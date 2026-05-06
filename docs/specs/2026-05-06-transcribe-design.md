# Spec — Transcribe (transcripción de Reels/TikTok)

**Fecha**: 2026-05-06
**Autor**: Michael + Claude
**Estado**: DRAFT v2 — incorporando review

---

## 1. Objetivo

Aplicación web interna para el equipo de RSUnion que recibe la URL de un video corto (Instagram Reel, TikTok, YouTube Short, Facebook Reel, X/Twitter video) y devuelve la **transcripción del audio en su idioma original**, sin traducir.

### 1.1 Casos de uso
- Equipo de marketing/contenido analiza guiones de competencia.
- Documentar diálogos de Reels para citas o subtítulos.
- Búsqueda de keywords en contenido visual.

### 1.2 Fuera de alcance (explícito)
- NO traduce a otro idioma.
- NO genera subtítulos con timestamps (solo texto plano por ahora).
- NO procesa videos largos (>10 min) — límite duro de duración.
- NO almacena historial de transcripciones (stateless).
- NO multi-tenant ni cuentas individuales — auth compartido del equipo.
- NO soporta playlists (un solo video por petición).

---

## 2. Arquitectura

### 2.1 Diagrama

```
┌─────────────────┐
│   Navegador     │
│ (equipo RSUnion)│
└────────┬────────┘
         │ HTTPS Basic Auth
         ▼
┌─────────────────────────────────────────────┐
│  https://transcribe.rsunion.com             │
│  Cloudflare DNS → 187.124.151.37 (DNS only) │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Traefik (Coolify managed)                  │
│  - SSL Let's Encrypt                        │
│  - Routing por FQDN                         │
│  - Body size limit middleware (4 KB)        │
└────────┬────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│  Container: transcribe-app                  │
│  Project: Transcribe (NUEVO en Coolify)     │
│  Limits: 2 GB RAM, 1 CPU                    │
│  PID 1: tini (zombie reaper)                │
│  ┌───────────────────────────────────────┐  │
│  │ Python 3.13 + FastAPI 0.136           │  │
│  │  ├── GET  /         → HTML+HTMX form  │  │
│  │  ├── POST /transcribe → JSON con texto│  │
│  │  └── GET  /health   → {"status":"ok"} │  │
│  │                                       │  │
│  │ Concurrency gate: asyncio.Semaphore=2 │  │
│  │ yt-dlp (pinned)     → descarga video  │  │
│  │ ffmpeg (apt)        → audio MP3 64kbps│  │
│  │ google-genai 1.75   → Gemini 2.5 Flash│  │
│  │   (Part.from_bytes inline, no File API)│  │
│  └───────────────────────────────────────┘  │
└─────────────────┬───────────────────────────┘
                  │ HTTPS
                  ▼
        ┌─────────────────────┐
        │  Gemini 2.5 Flash   │
        │  (Google AI Studio) │
        │  Free tier 2026     │
        └─────────────────────┘
```

### 2.2 Flujo de una petición exitosa

```
1. Usuario pega URL en HTML form → submit (HTMX POST /transcribe)
2. FastAPI valida URL (regex whitelist de plataformas) + body size ≤ 4 KB
3. Concurrency gate: semaphore.acquire() (max 2 en simultaneo)
4. yt-dlp (Python API, NO subprocess) descarga video a /tmp/{uuid}/v.mp4
   con: noplaylist=True, max_filesize=100MB, socket_timeout=30s,
        outtmpl="/tmp/{uuid}/v.%(ext)s" (sin %(title)s para evitar path injection)
   → timeout asyncio.wait_for(60s)
5. ffprobe valida duracion ≤ 600s; abort si excede
6. ffmpeg extrae audio → /tmp/{uuid}/a.mp3 (mono, 16kHz, 64kbps)
   → ~5MB max para 10min audio → cabe en inline Gemini (20MB límite)
   → timeout asyncio.wait_for(30s)
7. SDK Gemini: types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp3")
   con prompt: "Transcribe the audio in its original language. Output ONLY
   the transcribed text, no preamble, no translation, no formatting commentary."
   → timeout asyncio.wait_for(45s)
   → No usa File API, no requiere cleanup remoto
8. FastAPI devuelve {"texto", "idioma_detectado", "duracion_seg", "modelo"}
9. HTMX swappea el resultado en la página
10. Cleanup garantizado en finally: shutil.rmtree(/tmp/{uuid}) + semaphore.release()

Timeout total HTTP: 90s (asyncio.wait_for global).
```

### 2.3 Componentes y responsabilidades

| Módulo | Archivo | Responsabilidad única |
|---|---|---|
| Entrypoint | `app/main.py` | Configurar FastAPI, lifespan (startup/shutdown), montar templates |
| Config | `app/config.py` | Pydantic Settings, valida env vars al boot |
| Auth | `app/auth.py` | HTTP Basic dependency, `secrets.compare_digest`, failed-auth tracker |
| Constantes mensajes | `app/constants/messages.py` | `ERROR_MESSAGES` dict |
| Constantes plataformas | `app/constants/platforms.py` | `SUPPORTED_URL_PATTERNS` regex compilados |
| Constantes Gemini | `app/constants/gemini.py` | `GEMINI_PROMPT`, `GEMINI_MODEL`, `MAX_INLINE_AUDIO_BYTES` |
| Constantes logging | `app/constants/logging.py` | `LOG_KEYS` mapping, HMAC helper |
| Endpoint health | `app/routes/health.py` | `/health` mínimo `{"status":"ok"}`, sin auth |
| Endpoint index | `app/routes/index.py` | `/` HTML form (auth requerido) |
| Endpoint core | `app/routes/transcribe.py` | `/transcribe` orquesta pipeline (auth + rate limit) |
| Servicio descarga | `app/services/downloader.py` | yt-dlp Python API, args seguros |
| Servicio audio | `app/services/audio.py` | ffmpeg/ffprobe via asyncio subprocess |
| Servicio Gemini | `app/services/gemini.py` | Cliente google-genai, inline bytes |
| Servicio validador | `app/services/url_validator.py` | Validar URL + resolver host final + check no-SSRF |
| Servicio cleanup | `app/services/cleanup.py` | Crea/borra tmpdir; tarea async de huérfanos al boot |
| Servicio concurrencia | `app/services/concurrency.py` | Semáforo global, contexto async |
| UI | `app/templates/index.html` | HTML + HTMX (vendored) |
| Static | `app/static/htmx.min.js` | HTMX 2.0.9 vendored localmente (no CDN) |
| Static | `app/static/style.css` | Estilos minimal |

Cada módulo testeable independiente. Dependencias inyectadas por FastAPI Depends.

### 2.4 Centralización (zero duplicación)

| Concepto | Archivo único | Regla |
|---|---|---|
| Mensajes de error UI | `app/constants/messages.py` | TODOS los strings de error vienen de aquí |
| Regex plataformas | `app/constants/platforms.py` | Cero regex inline en endpoints |
| Prompt Gemini | `app/constants/gemini.py` | Un solo prompt, modificable en 1 lugar |
| Límites/timeouts | `app/config.py` (Pydantic Settings) | Cero hardcoding de números mágicos |
| Logging keys | `app/constants/logging.py` | Keys consistentes en logs estructurados |
| Acceso a env | `app/config.py` único punto | Cero `os.environ` directo |

**Anti-duplicación enforced via test**: `tests/test_no_duplication.py` falla si:
- Detecta strings de error duplicados fuera de `constants/messages.py`.
- Detecta regex de URL fuera de `constants/platforms.py`.
- Detecta `os.environ` fuera de `config.py`.
- Detecta llamadas a `requests.post` o `httpx` directas a Gemini fuera de `services/gemini.py`.

---

## 3. Stack técnico (versiones verificadas 2026-05-06)

| Componente | Versión pinned | Por qué |
|---|---|---|
| Python | `3.13` | Wheels nativas garantizadas; eol 2029 |
| FastAPI | `==0.136.1` | ASGI moderno, OpenAPI auto |
| Uvicorn[standard] | `==0.46.0` | Servidor ASGI |
| yt-dlp | `==2026.3.17` (pinned) | **Pinned**, bump explícito vía Dependabot semanal |
| ffmpeg | `apt` debian-bookworm | Binario sistema |
| google-genai | `==1.75.0` | SDK 2026 oficial (NO `google-generativeai` deprecated) |
| Jinja2 | `==3.1.6` | Templates server |
| HTMX | `2.0.9` (vendored local) | NO desde CDN |
| python-multipart | `==0.0.20` | Form data |
| pydantic-settings | `==2.7.0` | Config typed |
| slowapi | `==0.1.9` | Rate limiting con dos buckets |
| tini | `apt` | PID 1 zombie reaper |
| pytest + httpx | `==8.3.0` + `==0.28.0` | Tests |
| uv | `0.5+` | Lockfile reproducible (`uv.lock`) |

### 3.1 Modelo Gemini

- **`gemini-2.5-flash`** (GA, no preview).
- Free tier según pricing 2026 — **verificar antes de deploy** que la quota actual cubre uso esperado del equipo.
- Audio inline (Part.from_bytes) hasta 20 MB → 10 min de audio mp3 mono 64kbps = ~5 MB ≪ límite.
- **No usamos Gemini File API** → cero cleanup remoto, cero leak 48h.
- Prompt centralizado en `app/constants/gemini.py`:
  ```python
  GEMINI_PROMPT = (
      "Transcribe the audio in its original language. "
      "Output ONLY the transcribed text, no preamble, "
      "no translation, no formatting commentary."
  )
  ```

### 3.2 Reproducibilidad y supply chain

- `uv.lock` commiteado, hash-pinned.
- Build Docker usa `uv sync --frozen` (falla si lock no coincide).
- Dependabot weekly para `yt-dlp` y `google-genai` (los más activos).
- CI test E2E con un Reel público antes de aceptar el bump.

---

## 4. Aislamiento — garantías para no afectar el CRM

### 4.1 Recursos NUEVOS (creo yo)
- **Project Coolify**: `Transcribe` (nuevo, separado de `RSUnion`)
- **Application Coolify**: `transcribe-app` dentro del project nuevo
- **Container Docker**: 1 nuevo container, network propia
- **Volúmenes**: ninguno persistente. `/tmp/transcribe/` declarado como **tmpfs explícito** en Coolify (`tmpfs: ["/tmp/transcribe:size=500m"]`) → vive en RAM, nunca toca disco del host, wiped en cada restart. La app escribe siempre en `/tmp/transcribe/{uuid}/`, nunca en `/tmp` raíz
- **Repo Git**: nuevo, separado de `rsunion-crm`
- **Subdominio**: `transcribe.rsunion.com` (DNS A record ya creado, apunta a 187.124.151.37)

### 4.2 Recursos del CRM que NO se tocan (lista exhaustiva)

| Recurso | UUID / Nombre | Acción permitida |
|---|---|---|
| Project RSUnion | `d12s8a99e91bm5wy72plgfur` | **Solo lectura** para verificar que sigue healthy |
| App "CRM Backend API" | https://api.crmrsunion.com | **NO TOCAR** |
| App "CRM Frontend" | https://crmrsunion.com | **NO TOCAR** |
| App "CRM Worker" | (sslip.io interno) | **NO TOCAR** |
| App "sorteo-whatsapp" | (interno) | **NO TOCAR** |
| Volumen `pgdata` | postgres CRM | **NO TOCAR** |
| Volumen `redisdata` | redis CRM | **NO TOCAR** |
| Volumen `uploads-data` | media chat CRM | **NO TOCAR** |
| Servidor `VPS RSUnion` | `q6zzyixsxp4hjbq6xn7arjeg` | Solo lectura |

### 4.3 Reglas para llamadas MCP a Coolify

**Comandos PROHIBIDOS sin verificación previa de target**:
- `mcp__coolify__stop_all_apps` — NUNCA en este proyecto
- `mcp__coolify__restart_project_apps` con `project_uuid=d12s8a99e91bm5wy72plgfur`
- `mcp__coolify__redeploy_project` con `project_uuid=d12s8a99e91bm5wy72plgfur`
- `mcp__coolify__bulk_env_update` sobre apps del CRM

**Patrón seguro de cada llamada destructiva**:
1. Antes de llamar tool destructiva, leer `application.uuid` o `project.uuid` target.
2. Verificar que el UUID NO esté en la blocklist (UUIDs del CRM).
3. Solo entonces ejecutar.

**Lint de scripts de deploy**: el `Makefile` y cualquier script bash NO debe contener literal `d12s8a99e91bm5wy72plgfur` ni los UUIDs/dominios del CRM. Hay un check `grep -n` en pre-commit que falla si aparecen.

### 4.4 Límites de recursos del container

```
limits_memory: 2G            # 2GB para acomodar 2 requests concurrentes
                             # ffmpeg + buffer 100MB + Python ≈ 700MB/req peak
limits_cpus: 1               # 1 core max (VPS tiene 2)
healthcheck_enabled: true
healthcheck_path: /health
healthcheck_interval: 30s
```

**Concurrencia controlada en aplicación**: `asyncio.Semaphore(2)` en `services/concurrency.py`. Si 3+ usuarios mandan a la vez, el 3º espera (no falla, no OOM).

**Peor caso garantizado**: el container puede usar como máximo 2 GB RAM y 1 CPU. El CRM mantiene 1 CPU + ≥5 GB RAM intactos.

---

## 5. Seguridad

### 5.1 Autenticación
- **HTTP Basic Auth** vía FastAPI dependency.
- Variables de entorno (configuradas SOLO en Coolify, NUNCA en este spec):
  - `BASIC_AUTH_USER` = `<set-in-coolify>` (ej. `equipo`)
  - `BASIC_AUTH_PASS` = `<set-in-coolify>` — generar con `openssl rand -base64 24` (≥24 chars random, no diccionario+año)
- Comparación con `secrets.compare_digest` (timing-safe).
- Aplica a **todas las rutas excepto `/health`**.

### 5.2 Validación de input
- URL validada en dos pasos en `services/url_validator.py`:
  1. **Parse con `urllib.parse.urlparse`** → verificar `scheme in {"https"}` y `netloc` no vacío.
  2. **Whitelist de host (NO regex sobre URL completa para evitar bypass tipo `evil.com/?x=instagram.com/reel/`)**:
     - host (`netloc.lower()`) debe matchear exacto:
       - `www.instagram.com`, `instagram.com` (con path `/(reel|p|reels)/...`)
       - `www.tiktok.com`, `tiktok.com`, `vm.tiktok.com`
       - `www.youtube.com`, `youtube.com` (path `/shorts/`), `youtu.be`
       - `www.facebook.com`, `facebook.com` (path `/reel/`), `fb.watch`
       - `twitter.com`, `x.com`, `www.twitter.com`, `www.x.com`
- Rechazo HTTP 400 si no matchea.
- **Resolver IP del host** (`socket.getaddrinfo`) y verificar que NO sea IP privada/loopback/link-local (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 169.254.0.0/16, ::1, fc00::/7) — anti-SSRF.
- **Nota sobre redirects internos de yt-dlp**: el SDK puede seguir redirects una vez que arranca. Mitigación parcial aceptada (limite por `max_filesize` y `socket_timeout`); riesgo residual documentado.
- Body size limit middleware (4 KB) en FastAPI + Traefik label `traefik.http.middlewares.limit.buffering.maxRequestBodyBytes=4096`.
- yt-dlp args seguros (Python API, no shell). Todos los números vienen de `config.py`, NUNCA hardcoded:
  ```python
  ydl_opts = {
      "outtmpl": f"/tmp/{request_uuid}/v.%(ext)s",  # UUID-only, NO %(title)s
      "noplaylist": True,
      "max_filesize": settings.MAX_DOWNLOAD_SIZE_MB * 1024 * 1024,
      "socket_timeout": settings.YT_DLP_SOCKET_TIMEOUT_SEC,
      "cookiefile": None,
      "no_warnings": True,
      "quiet": True,
  }
  # Nota: NO incluimos `extractor_args.generic.impersonate` — la sintaxis
  # correcta varía por extractor y está fuera de necesidad para nuestro caso.
  # Si se requiere bypass anti-bot, evaluar `curl_cffi` en follow-up.
  ```
- ffprobe valida `duracion_seg ≤ settings.MAX_VIDEO_DURATION_SEC` post-download; abort+cleanup si excede. **Todos los límites se leen de `config.py`** (Pydantic Settings), nunca inline.

### 5.3 Headers de seguridad
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()`
- (NO se usa `X-Frame-Options` legacy — `frame-ancestors 'none'` lo cubre)
- HTMX vendored localmente → cero dependencia CDN.

### 5.4 Secrets management
- `.env.example` commiteado con placeholders.
- `.env` en `.gitignore`.
- Valores reales SOLO en Coolify env vars del app.
- `GEMINI_API_KEY`:
  - Restringida en Google Cloud Console → API restrictions: solo `Generative Language API`.
  - **Budget alert** en Google Cloud a $5/mes para detectar uso anómalo.
  - Rotación documentada en README.
- `.mcp.json` referencia `${COOLIFY_TOKEN}` vía env, NUNCA literal.
- Pre-commit hook `gitleaks` para detectar secrets accidentales.

### 5.5 Rate limiting (dos buckets)

`slowapi` configurado con dos límites distintos:

| Bucket | Límite | Aplica a |
|---|---|---|
| Per-IP general | 10/minuto, 100/día | Todas las rutas autenticadas |
| Per-IP failed-auth | 5/hora | Solo respuestas 401 (anti-brute-force) |

Si la app está expuesta a internet sin Cloudflare WAF, esto es defensa en profundidad.

---

## 6. Manejo de errores

| Caso | HTTP code | Mensaje (de `ERROR_MESSAGES`) |
|---|---|---|
| URL no soportada | 400 | `URL_NO_SOPORTADA` |
| URL resuelve a IP privada | 400 | `URL_PROHIBIDA` |
| yt-dlp falla (privado/inválido/geo) | 422 | `DESCARGA_FALLIDA` |
| Video > 10 min | 413 | `VIDEO_LARGO` |
| Gemini API error/quota | 502 | `TRANSCRIPCION_NO_DISPONIBLE` |
| Timeout subprocess | 504 | `TIMEOUT_SUBPROCESO` |
| Timeout total | 504 | `TIMEOUT_TOTAL` |
| Auth incorrecto | 401 | (browser muestra prompt nativo) |
| Rate limit general | 429 | `RATE_LIMIT_EXCEDIDO` |
| Rate limit failed-auth | 429 | `INTENTOS_AUTH_EXCEDIDOS` |
| Body > 4 KB | 413 | `INPUT_DEMASIADO_GRANDE` |

### 6.1 Timeouts explícitos (config.py)

```python
DOWNLOAD_TIMEOUT_SEC = 60
FFMPEG_TIMEOUT_SEC = 30
GEMINI_TIMEOUT_SEC = 45
TOTAL_REQUEST_TIMEOUT_SEC = 90
```

Cada operación envuelta en `asyncio.wait_for(...)`. Subprocess de ffmpeg con `proc.kill()` en timeout.

### 6.2 Logging estructurado

JSON logs vía `structlog` o `logging.JSONFormatter`:
```json
{"ts":"...","level":"info","event":"transcribe.start","request_uuid":"...","url_hmac":"<hex8>","platform":"tiktok"}
```

- **NO loguear URL completa** — solo `platform` + `url_hmac` (HMAC-SHA256 con secret per-deployment, primeros 8 chars). Reversible solo con el secret.
- `LOG_KEYS` centralizadas en `constants/logging.py`.

### 6.3 Cleanup garantizado

```python
async def transcribe(url: str):
    request_uuid = uuid4().hex
    tmpdir = Path(f"/tmp/{request_uuid}")
    async with concurrency.gate():  # semaphore
        try:
            tmpdir.mkdir(parents=True)
            # download → ffmpeg → gemini ...
            return result
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
```

---

## 7. Testing

### 7.1 Tests unitarios
- `test_config.py` — Pydantic carga env vars, falla si falta `GEMINI_API_KEY`/`BASIC_AUTH_*`.
- `test_auth.py` — Basic Auth: credenciales OK/KO, exime `/health`, failed-auth rate limit.
- `test_url_validator.py` — Cada plataforma de la whitelist + URLs malas + IPs privadas (mock DNS).
- `test_downloader.py` — Mock de `YoutubeDL`, verifica `outtmpl`, `noplaylist`, `max_filesize`.
- `test_audio.py` — Mock `asyncio.create_subprocess_exec`, verifica args y timeout.
- `test_gemini.py` — Mock `genai.Client`, verifica prompt y `Part.from_bytes`.
- `test_cleanup.py` — Crea/borra tmpdir, verifica orphans cleanup al boot.
- `test_concurrency.py` — Semáforo permite 2 simultáneos, bloquea el 3º.
- `test_no_duplication.py` — AST scan con allowlist explícita: `os.environ` permitido SOLO en `app/config.py`; regex de plataforma SOLO en `app/constants/platforms.py`; strings de error SOLO en `app/constants/messages.py`. Tests y `conftest.py` exentos. La allowlist vive en el propio test como constante.

### 7.2 Tests de integración
- `test_health.py` — `/health` retorna 200 sin auth, payload `{"status":"ok"}` exacto.
- `test_index.py` — `/` retorna HTML con form (auth requerido).
- `test_security_headers.py` — HSTS, CSP, X-Content-Type-Options presentes.
- `test_body_size_limit.py` — Body > 4 KB rechazado 413.

### 7.3 E2E (manual / CI on demand)
- `test_transcribe_e2e.py` (`@pytest.mark.slow`) — Reel público real, smoke test.

### 7.4 Cobertura objetivo
- ≥ 85% en `app/services/`
- ≥ 70% global

---

## 8. Estructura de archivos

```
transcribe/
├── .mcp.json                    # Coolify MCP (token via ${COOLIFY_TOKEN} env)
├── .gitignore
├── .gitleaks.toml
├── .env.example
├── .dockerignore
├── Dockerfile                   # multi-stage
├── pyproject.toml
├── uv.lock                      # frozen
├── Makefile
├── README.md
├── docs/
│   └── specs/
│       └── 2026-05-06-transcribe-design.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── constants/
│   │   ├── __init__.py
│   │   ├── messages.py
│   │   ├── platforms.py
│   │   ├── gemini.py
│   │   └── logging.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── index.py
│   │   └── transcribe.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── url_validator.py
│   │   ├── downloader.py
│   │   ├── audio.py
│   │   ├── gemini.py
│   │   ├── concurrency.py
│   │   └── cleanup.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── htmx.min.js          # vendored 2.0.9
│       └── style.css
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_config.py
    ├── test_auth.py
    ├── test_url_validator.py
    ├── test_downloader.py
    ├── test_audio.py
    ├── test_gemini.py
    ├── test_cleanup.py
    ├── test_concurrency.py
    ├── test_health.py
    ├── test_index.py
    ├── test_security_headers.py
    ├── test_body_size_limit.py
    ├── test_no_duplication.py
    └── test_transcribe_e2e.py
```

---

## 9. Dockerfile (multi-stage, sin curl, con tini)

```dockerfile
# ----- Builder -----
FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.5.0

WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ----- Runtime -----
FROM python:3.13-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tini \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 app
WORKDIR /home/app

# Copy deps from builder
COPY --from=builder --chown=app:app /build/.venv /home/app/.venv
ENV PATH="/home/app/.venv/bin:$PATH"

# Copy app code
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

# Healthcheck sin curl: usa python stdlib
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
        sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health',timeout=3).getcode()==200 else 1)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--timeout-graceful-shutdown", "30"]
# Nota: NO usamos --limit-max-requests porque en single-worker container
# el recycling produce cortes momentáneos. Coolify reinicia por healthcheck
# si hay leak. Para defensa contra mem leaks, dependemos de limits_memory.
```

### 9.1 Graceful shutdown

- `tini` como PID 1 → propaga SIGTERM, reapa zombies.
- FastAPI `lifespan`: en shutdown cancela tasks activas, espera semaphore drain (max 30s), limpia `/tmp`.
- Uvicorn `--timeout-graceful-shutdown 30`.

### 9.2 CORS

**Explícito**: CORS NO se habilita. Misma origen únicamente. Si en el futuro se necesita, se agrega vía `CORSMiddleware` con whitelist explícita.

---

## 10. Plan de deploy

### Fase 0 — Local
1. Crear repo Git en `/Users/michael/Desktop/DESARROLLO/transcribe/`.
2. Implementar siguiendo TDD (test → fail → impl → pass).
3. `uv sync` + `pytest` + `docker build` + smoke test local.

### Fase 1 — GitHub
1. Crear repo `michael-rsunion/transcribe` privado.
2. Push initial commit.
3. Configurar Dependabot weekly para `yt-dlp` y `google-genai`.

### Fase 2 — Coolify (acciones aisladas, una por una con verificación)

**Paso 2.1** — Crear nuevo Project en Coolify:
```
mcp__coolify__projects (action=create, name=Transcribe,
  description="Transcripción de Reels/TikToks - app interna")
```
→ obtener nuevo `project_uuid` (≠ `d12s8a99e91bm5wy72plgfur`).

**Paso 2.2** — Crear application:
```
mcp__coolify__application (action=create,
  project_uuid=<NUEVO>,
  server_uuid=q6zzyixsxp4hjbq6xn7arjeg,
  name=transcribe-app,
  git_repository=https://github.com/michael-rsunion/transcribe,
  git_branch=main,
  build_pack=dockerfile,
  ports_exposes=8000,
  fqdn=https://transcribe.rsunion.com,
  limits_memory=2G,
  limits_cpus=1)
```

**Paso 2.3** — Setear env vars (valores REALES solo en este paso, NUNCA en docs):
```
mcp__coolify__env_vars (application_uuid=<nuevo>, action=set, vars={
  GEMINI_API_KEY=<set-here>,
  BASIC_AUTH_USER=equipo,
  BASIC_AUTH_PASS=<openssl rand -base64 24>,
  GEMINI_MODEL=gemini-2.5-flash,
  MAX_VIDEO_DURATION_SEC=600,
  MAX_DOWNLOAD_SIZE_MB=100,
  HMAC_LOG_SECRET=<openssl rand -hex 32>,
  RATE_LIMIT_PER_MIN=10,
  RATE_LIMIT_PER_DAY=100,
  RATE_LIMIT_FAILED_AUTH_PER_HOUR=5
})
```

**Paso 2.4** — Disparar deploy:
```
mcp__coolify__deploy (application_uuid=<nuevo>, force=false)
```

**Paso 2.5** — Verificar:
```
mcp__coolify__application_logs (application_uuid=<nuevo>, lines=100)
curl -fsS https://transcribe.rsunion.com/health    # debe retornar 200
mcp__coolify__list_applications  # confirmar CRM apps siguen healthy
```

### Fase 3 — Validación funcional
- Login Basic Auth desde browser.
- Pegar Reel público de prueba.
- Verificar transcripción correcta.
- Verificar headers de seguridad con `curl -I`.

---

## 11. Costos

| Concepto | Costo mensual incremental |
|---|---|
| VPS (ya pagado) | $0 |
| Coolify (self-hosted) | $0 |
| Gemini API free tier | $0 |
| Dominio `rsunion.com` | $0 |
| **Total incremental** | **$0 USD/mes** |

Si excede free tier (Gemini paga ~$0.075/1M tokens audio, ≈ $0.0001/min audio), 1000 transcripciones de 1 min = $0.10. Budget alert configurado en $5/mes.

---

## 12. Decisiones tomadas y descartadas

| Decisión | Tomada | Alternativa descartada | Razón |
|---|---|---|---|
| Hosting | Coolify VPS propio | Render Free / Railway | $0 incremental, sin cold starts |
| Transcripción | Gemini 2.5 Flash inline bytes | Whisper local / Gemini File API | Free tier suficiente, sin leak 48h |
| Stack | Python + FastAPI | Node.js | yt-dlp y google-genai nativos |
| Frontend | HTMX vendored + Jinja2 | React/Next.js o HTMX desde CDN | Sin build step ni dep CDN |
| Auth | HTTP Basic + 2 buckets rate limit | OAuth/JWT | Setup rápido, defensa en profundidad |
| Aislamiento | Project Coolify nuevo | App dentro de RSUnion | Garantía visual+lógica |
| Python | 3.13 | 3.14 | Wheels nativas garantizadas |
| Lockfile | uv.lock | requirements.txt | Reproducibilidad estricta |
| PID 1 | tini | Uvicorn directo | Graceful shutdown + reaper |
| yt-dlp version | pinned + Dependabot | `*` rolling | Reproducibilidad + supply chain |

---

## 13. Riesgos y mitigaciones

| Riesgo | Prob | Impact | Mitigación |
|---|---|---|---|
| TikTok/IG cambia API → yt-dlp roto | Alta | Medio | Dependabot weekly + test E2E pre-merge |
| Bad release de yt-dlp en CI | Media | Alto | uv.lock + CI verifica E2E antes de bump |
| Gemini quota excedida | Baja | Medio | Logging contador + budget alert |
| Container OOM por concurrencia | Baja | Bajo | Semáforo=2 + 2GB RAM + tini |
| Token Gemini filtrado | Baja | Alto | API restrictions + budget + rotación |
| Token Coolify filtrado (existente en docs CRM) | Existente | Alto | **Follow-up**: rotar token CRM |
| Subdominio público bot abuse | Media | Bajo | Basic Auth fuerte + 2 buckets rate limit |
| Brute-force credenciales | Baja | Alto | failed-auth rate limit 5/h/IP + pass 24chars |
| SSRF via URL maliciosa | Baja | Alto | Resolver host + bloquear IPs privadas |
| Path injection en outtmpl | Baja | Alto | UUID-only path, no `%(title)s` |
| Playlist explotada | Baja | Medio | `noplaylist=True` |
| Logs con URL identificables | Media | Medio | HMAC con secret per-deployment |
| ToS de Instagram/TikTok/etc | Media | Bajo | Uso interno + acknowledged en README |
| Container afecta CRM (CPU/RAM) | Muy baja | Alto | `limits_memory=2G`, `limits_cpus=1`, project separado |
| Llamada MCP por error a app del CRM | Baja | Alto | UUID blocklist + grep pre-commit |

---

## 14. Criterios de aceptación

1. ✅ `https://transcribe.rsunion.com/health` retorna 200 con SSL válido y payload `{"status":"ok"}` exacto.
2. ✅ Browser pide Basic Auth al entrar a `/`.
3. ✅ Reel público en español → transcripción correcta en español.
4. ✅ TikTok en inglés → transcripción en inglés (no traduce).
5. ✅ URL inválida → mensaje claro de `ERROR_MESSAGES`.
6. ✅ URL que resuelve a IP privada → 400 (anti-SSRF).
7. ✅ Container respeta `limits_memory=2G`, `limits_cpus=1`.
8. ✅ Apps del project RSUnion (CRM Frontend, Backend, Worker, sorteo) siguen `running:healthy` durante y después del deploy (verificado vía `mcp__coolify__list_applications`).
9. ✅ `pytest` pasa todos los tests, incluyendo `test_no_duplication.py`.
10. ✅ Headers de seguridad (HSTS, CSP, etc.) presentes en respuestas (verificado con `curl -I`).
11. ✅ `gitleaks` y pre-commit hooks pasan sin warnings.
12. ✅ `README.md` documenta uso y mantenimiento (incluye runbook de rotación de keys).

---

## 15. Follow-ups (post-launch)

- Rotar token Coolify (está en plain text en `rsunion-crm/docs/PLAN_DEPLOY_RESTRUCTURE.md`).
- Agregar timestamps en transcripción (subtítulos SRT).
- Caché por URL hash (evitar duplicados).
- Login del CRM (SSO) si crece el uso.
- Métricas (Prometheus exporter): count transcripciones/día, latencia p95.
- WAF Cloudflare (proxy mode) si crece uso público.
