# Transcribe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-hosted internal web app that transcribes Reels/TikToks/Shorts to text in their original language, deployed in a NEW isolated Coolify project on the existing VPS, with strict guarantees of non-interference with the running CRM.

**Architecture:** Single Python container behind Coolify's Traefik proxy. FastAPI serves a tiny HTMX UI and a `/transcribe` endpoint that pipelines `yt-dlp` (download) → `ffmpeg` (audio extraction) → Gemini 2.5 Flash (transcription via inline bytes, no File API). HTTP Basic Auth, 2-bucket rate limiting, anti-SSRF host validation. Container is constrained to 2GB RAM / 1 CPU and writes only to a tmpfs `/tmp/transcribe`.

**Tech Stack:** Python 3.13 · FastAPI 0.136.1 · uvicorn 0.46.0 · yt-dlp 2026.3.17 (pinned) · ffmpeg (apt) · google-genai 1.75.0 · Jinja2 3.1.6 · HTMX 2.0.9 (vendored) · slowapi 0.1.9 · pydantic-settings 2.7.0 · pytest 8.3.0 · uv lockfile · tini · multi-stage Dockerfile.

**Spec:** [`docs/specs/2026-05-06-transcribe-design.md`](../specs/2026-05-06-transcribe-design.md)

**Working dir for ALL commands:** `/Users/michael/Desktop/DESARROLLO/transcribe/` unless explicitly noted.

**SAFETY RULES (read before every Coolify call):**
- Project RSUnion uuid `d12s8a99e91bm5wy72plgfur` and its apps are READ-ONLY.
- Before any destructive Coolify call (deploy, env_vars set, restart_project_apps), verify target uuid is the NEW Transcribe project's uuid, never the CRM's.
- After every Coolify deploy, run `mcp__coolify__list_applications` and confirm `CRM Backend API`, `CRM Frontend`, `CRM Worker`, `sorteo-whatsapp` are all `running:healthy`.

---

## Phase 0 — Repo skeleton & tooling

### Task 0.1: Initialize Git repo and base files

**Files:**
- Create: `.gitignore`, `.dockerignore`, `.gitleaks.toml`, `.env.example`, `README.md`, `pyproject.toml`, `Makefile`

- [ ] **Step 1: Initialize Git** — `git init -b main` (in project dir).

- [ ] **Step 2: Write `.gitignore`** — patterns: `__pycache__/`, `*.py[cod]`, `.venv/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`, `.env`, `*.log`, `/tmp/`, `.DS_Store`, `*.egg-info/`, `.coolify-snapshots/`.

- [ ] **Step 3: Write `.dockerignore`** — exclude `.git`, `.venv`, `__pycache__`, `.pytest_cache`, `.env*`, `docs/`, `tests/`, `*.md`, `.gitleaks.toml`, `.gitignore`, `.dockerignore`, `Makefile`.

- [ ] **Step 4: Write `.env.example`** with placeholders for every key in `app/config.py` (real values go to Coolify only).

- [ ] **Step 5: Write `pyproject.toml`** with deps pinned per spec section 3, ruff + pytest config.

- [ ] **Step 6: Write `Makefile`** with targets `install`, `test`, `lint`, `run`, `docker-build`, `docker-run`, `guard-crm` (greps for CRM uuid and fails if found).

- [ ] **Step 7: Write skeleton `README.md`** (expanded later in Phase 11).

- [ ] **Step 8: Write `.gitleaks.toml`** with allowlist for placeholders in `.env.example`.

- [ ] **Step 9: Install deps and create lockfile** — `uv sync` (creates `uv.lock`, populates `.venv/`).

- [ ] **Step 10: Initial commit** — `git add . && git commit -m "chore: project skeleton"`.

### Task 0.2: Install pre-commit + CRM-uuid guard

**Files:** Create `.pre-commit-config.yaml`, `scripts/guard_crm_uuid.sh`.

- [ ] **Step 1: Write `scripts/guard_crm_uuid.sh`** that fails with non-zero exit if string `d12s8a99e91bm5wy72plgfur` appears anywhere under `Makefile`, `scripts/`, `.github/`, `Dockerfile`, or `app/` (search via `grep -RIn`). Make executable: `chmod +x scripts/guard_crm_uuid.sh`.

- [ ] **Step 2: Write `.pre-commit-config.yaml`:**
  ```yaml
  repos:
    - repo: https://github.com/gitleaks/gitleaks
      rev: v8.21.0
      hooks: [{id: gitleaks}]
    - repo: https://github.com/astral-sh/ruff-pre-commit
      rev: v0.7.0
      hooks:
        - {id: ruff}
        - {id: ruff-format}
    - repo: local
      hooks:
        - id: guard-crm-uuid
          name: Guard CRM uuid leak
          entry: scripts/guard_crm_uuid.sh
          language: script
          pass_filenames: false
  ```

- [ ] **Step 3: Install hook**:
  ```bash
  uv run --with pre-commit pre-commit install
  uv run --with pre-commit pre-commit run --all-files
  ```
  Expected: gitleaks PASS, ruff PASS, guard-crm-uuid PASS.

- [ ] **Step 4: Commit** — `git add .pre-commit-config.yaml scripts && git commit -m "chore: pre-commit with gitleaks + CRM-uuid guard"`.

---

## Phase 1 — Constants (zero-duplication foundation)

### Task 1.1: `app/constants/messages.py`

**Files:** Create `app/__init__.py`, `app/constants/__init__.py`, `app/constants/messages.py`, `tests/__init__.py`, `tests/test_constants_messages.py`.

- [ ] **Step 1: Write failing test** — `tests/test_constants_messages.py` asserting `ERROR_MESSAGES` contains all required keys (URL_NO_SOPORTADA, URL_PROHIBIDA, DESCARGA_FALLIDA, VIDEO_LARGO, TRANSCRIPCION_NO_DISPONIBLE, TIMEOUT_SUBPROCESO, TIMEOUT_TOTAL, RATE_LIMIT_EXCEDIDO, INTENTOS_AUTH_EXCEDIDOS, INPUT_DEMASIADO_GRANDE) and all values are non-empty strings.

- [ ] **Step 2: Run test, expect FAIL** — `uv run pytest tests/test_constants_messages.py -v`.

- [ ] **Step 3: Implement `app/constants/messages.py`** as a single `ERROR_MESSAGES: dict[str, str]` with Spanish messages from spec section 6.

- [ ] **Step 4: Run test, expect PASS.**

- [ ] **Step 5: Commit** — `git add app tests && git commit -m "feat(constants): error messages catalog"`.

### Task 1.2: `app/constants/platforms.py`

**Files:** Create `app/constants/platforms.py`, `tests/test_constants_platforms.py`.

- [ ] **Step 1: Write failing test** verifying `ALLOWED_HOSTS` is lowercase and contains all expected hosts (instagram.com, www.instagram.com, tiktok.com, www.tiktok.com, vm.tiktok.com, youtube.com, www.youtube.com, youtu.be, facebook.com, www.facebook.com, fb.watch, twitter.com, www.twitter.com, x.com, www.x.com), and `PLATFORM_PATH_RULES["instagram.com"]` rejects `/random/abc`.

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement `app/constants/platforms.py`** with:
  - `ALLOWED_HOSTS: frozenset[str]`
  - `PLATFORM_PATH_RULES: dict[str, Callable[[dict], bool]]` — rules: instagram only `/reel|reels|p/`, youtube only `/shorts/` (or `youtu.be` always), facebook only `/reel|watch`, others always.
  - `platform_for_host(host)` → canonical name for logging.

- [ ] **Step 4: PASS.**

- [ ] **Step 5: Commit** — `git add . && git commit -m "feat(constants): platform whitelist with host+path rules"`.

### Task 1.3: `app/constants/gemini.py` and `app/constants/logging.py`

- [ ] **Step 1: Write failing test** `tests/test_constants_gemini_logging.py`:
  - Asserts `GEMINI_PROMPT` contains "no translation" and "original language".
  - Asserts `DEFAULT_GEMINI_MODEL == "gemini-2.5-flash"`.
  - Asserts `url_hmac("a","b")` returns 8 hex chars, deterministic, and differs when secret differs.
  - Asserts `LOG_KEYS` contains `REQ_ID`, `URL_HMAC`, `PLATFORM`, `DURATION_MS`, `EVENT`.

- [ ] **Step 2: Run, expect FAIL** — `uv run pytest tests/test_constants_gemini_logging.py -v`.

- [ ] **Step 3: Implement `app/constants/gemini.py`** with `GEMINI_PROMPT` (per spec 3.1) and `DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"`.

- [ ] **Step 4: Implement `app/constants/logging.py`** with `LOG_KEYS` dict and `url_hmac(url, secret) -> str` returning HMAC-SHA256 truncated to 8 hex chars.

- [ ] **Step 5: Run, expect PASS.**

- [ ] **Step 6: Commit** — `git add . && git commit -m "feat(constants): gemini prompt + logging helpers"`.

---

## Phase 2 — Configuration

### Task 2.1: `app/config.py`

**Files:** Create `app/config.py`, `tests/conftest.py`, `tests/test_config.py`.

- [ ] **Step 1: Write failing test** — `Settings()` loads with all required env vars present; raises `ValidationError` if any required (GEMINI_API_KEY, BASIC_AUTH_USER, BASIC_AUTH_PASS, HMAC_LOG_SECRET) is missing or password < 24 chars.

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement `app/config.py`** as `class Settings(BaseSettings)` with:
  - Required: `GEMINI_API_KEY` (min 10), `BASIC_AUTH_USER` (min 1), `BASIC_AUTH_PASS` (min 24), `HMAC_LOG_SECRET` (min 32).
  - Defaults from spec section 6.1 and 5.5: `MAX_VIDEO_DURATION_SEC=600`, `MAX_DOWNLOAD_SIZE_MB=100`, `YT_DLP_SOCKET_TIMEOUT_SEC=30`, `FFMPEG_TIMEOUT_SEC=30`, `GEMINI_TIMEOUT_SEC=45`, `TOTAL_REQUEST_TIMEOUT_SEC=90`, `MAX_BODY_BYTES=4096`, `RATE_LIMIT_PER_MIN=10`, `RATE_LIMIT_PER_DAY=100`, `RATE_LIMIT_FAILED_AUTH_PER_HOUR=5`, `MAX_INLINE_AUDIO_BYTES=20_000_000`, `MAX_CONCURRENT_REQUESTS=2`, `TMPFS_BASE_DIR="/tmp/transcribe"`, `GEMINI_MODEL="gemini-2.5-flash"`.
  - `get_settings()` factory.

- [ ] **Step 4: Write `tests/conftest.py`** auto-fixture setting minimal valid env (24-char password, 64-char HMAC secret, dummy Gemini key).

- [ ] **Step 5: PASS.**

- [ ] **Step 6: Commit** — `git add . && git commit -m "feat(config): Pydantic Settings"`.

---

## Phase 3 — Services (TDD with mocked I/O)

### Task 3.1: `app/services/url_validator.py`

**Files:** `app/services/__init__.py`, `app/services/url_validator.py`, `tests/test_url_validator.py`.

- [ ] **Step 1: Write failing tests:**
  - Parametrized: accepts valid URLs from each platform (mock `_resolve_is_public` → True).
  - Parametrized: rejects http (not https), bypass-style `evil.com/?x=instagram.com/...`, unlisted hosts, wrong paths, non-URLs.
  - Rejects when `_resolve_is_public` returns False (private IP).

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement `app/services/url_validator.py`:**
  - `class UrlValidationError(ValueError)`.
  - `@dataclass(frozen=True) class ValidatedUrl(raw, host, path, platform)`.
  - `_resolve_is_public(host)` uses `socket.getaddrinfo` + `ipaddress` to reject private/loopback/link-local IPv4 and IPv6 ranges.
  - `validate_url(raw)` parses with `urllib.parse.urlparse`, checks scheme=https, netloc in `ALLOWED_HOSTS`, runs `PLATFORM_PATH_RULES[host]`, then `_resolve_is_public`. Returns `ValidatedUrl`.

- [ ] **Step 4: PASS.**

- [ ] **Step 5: Commit** — `git add . && git commit -m "feat(services): url_validator with anti-SSRF + host whitelist"`.

### Task 3.2: `app/services/cleanup.py`

**Files:** `app/services/cleanup.py`, `tests/test_cleanup.py`.

- [ ] **Step 1: Write failing test** for `make_request_dir`, idempotent `drop_request_dir`, `sweep_orphans` (creates two dirs, backdates one with `os.utime`, asserts old removed and new kept).

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement** `make_request_dir(base, uuid) -> Path`, `drop_request_dir(d) -> None` (uses `shutil.rmtree` with `ignore_errors=True`), `sweep_orphans(base, max_age_seconds) -> int` (iterates children, removes if `mtime` older than threshold).

- [ ] **Step 4: PASS.**

- [ ] **Step 5: Commit** — `git add . && git commit -m "feat(services): cleanup with orphan sweep"`.

### Task 3.3: `app/services/concurrency.py`

**Files:** `app/services/concurrency.py`, `tests/test_concurrency.py`.

- [ ] **Step 1: Write failing test** — async test launches 3 tasks against `Gate(max_concurrent=2)`, verifies only 2 hold the gate at once.

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement** `class Gate(max_concurrent)` wrapping `asyncio.Semaphore`, exposing async context manager `acquire()`.

- [ ] **Step 4: Add module-level factory** `get_gate() -> Gate` in `concurrency.py` that lazily constructs a singleton `Gate(get_settings().MAX_CONCURRENT_REQUESTS)` and returns it. Used by routes via `Depends(get_gate)`.

- [ ] **Step 5: Add test** for the factory: two calls return the same instance.

- [ ] **Step 6: PASS.**

- [ ] **Step 7: Commit** — `git add . && git commit -m "feat(services): concurrency gate + singleton factory"`.

### Task 3.4: `app/services/downloader.py` (yt-dlp)

**Files:** `app/services/downloader.py`, `tests/test_downloader.py`.

- [ ] **Step 1: Write failing test** mocking `YoutubeDL`:
  - Captures the opts dict; asserts `noplaylist=True`, `max_filesize=100*1024*1024`, `socket_timeout=30`, `cookiefile=None`, `outtmpl` ends with `v.%(ext)s` and contains no `%(title)s`.
  - On `download()` raising, function raises `DownloadError`.

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement** `download_video(url, target_dir, *, max_size_mb, socket_timeout) -> Path`:
  - Build `opts` dict per spec section 5.2.
  - Use `with YoutubeDL(opts) as ydl: ydl.download([url])`.
  - Wrap in try/except → raise `DownloadError`.
  - Return `next(target_dir.glob("v.*"))` or raise if none.

- [ ] **Step 4: PASS.**

- [ ] **Step 5: Commit** — `git add . && git commit -m "feat(services): yt-dlp downloader with safe opts"`.

### Task 3.5: `app/services/audio.py` (ffmpeg/ffprobe)

**Files:** `app/services/audio.py`, `tests/test_audio.py`.

- [ ] **Step 1: Write failing async test** mocking `asyncio.create_subprocess_exec`:
  - `extract_audio_mp3` called with `-ac 1 -ar 16000`, returns `target_dir / "a.mp3"`.
  - `probe_duration_sec` parses stdout `"42.5\n"` → returns `42.5`.

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement:**
  - `class AudioError(RuntimeError)`.
  - `_run(args, timeout)` helper using `asyncio.create_subprocess_exec` (passing args list, no shell), `asyncio.wait_for(proc.communicate(), timeout)`, on timeout `proc.kill()` + raise.
  - `extract_audio_mp3(src, target_dir, *, timeout)` runs ffmpeg with `-y -i SRC -vn -ac 1 -ar 16000 -c:a libmp3lame -b:a 64k OUT`.
  - `probe_duration_sec(src, *, timeout)` runs ffprobe `-show_entries format=duration -of default=noprint_wrappers=1:nokey=1`.

- [ ] **Step 4: PASS.**

- [ ] **Step 5: Commit** — `git add . && git commit -m "feat(services): audio extract + duration probe"`.

### Task 3.6: `app/services/gemini.py`

**Files:** `app/services/gemini.py`, `tests/test_gemini.py`.

- [ ] **Step 1: Write failing async test** mocking `genai.Client`:
  - `transcribe_audio` reads file bytes, calls `client.aio.models.generate_content` with the prompt + `Part.from_bytes`, returns response text.
  - Raises `GeminiError` if file > `max_inline_bytes` (test with 30MB dummy file).

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement** `transcribe_audio(audio_path, *, api_key, model, timeout, max_inline_bytes=20_000_000) -> str`:
  - Read bytes, validate size ≤ `max_inline_bytes`.
  - `client = genai.Client(api_key=api_key)`.
  - `audio_part = types.Part.from_bytes(data=data, mime_type="audio/mp3")`.
  - `resp = await asyncio.wait_for(client.aio.models.generate_content(model=model, contents=[GEMINI_PROMPT, audio_part]), timeout=timeout)`.
  - Catch `asyncio.TimeoutError` and other exceptions → raise `GeminiError`.
  - Return `resp.text.strip()` (raise if empty).

- [ ] **Step 4: PASS.**

- [ ] **Step 5: Commit** — `git add . && git commit -m "feat(services): gemini inline-bytes transcription"`.

---

## Phase 4 — Auth + middleware

### Task 4.1: `app/auth.py`

**Files:** `app/auth.py`, `tests/test_auth.py`.

- [ ] **Step 1: Write failing test** building a tiny FastAPI app with `Depends(require_basic_auth)`:
  - 401 with `WWW-Authenticate` header when no auth.
  - 200 with correct basic credentials.
  - 401 with wrong password.

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement `app/auth.py`:**
  - `_security = HTTPBasic(realm="transcribe")`.
  - `require_basic_auth(request, credentials = Depends(_security), settings = Depends(get_settings))`:
    - Use `secrets.compare_digest` for both username and password.
    - On failure: increment a per-IP failed-auth counter (slowapi limiter via `request.app.state.limiter.hit("failed_auth", get_remote_address(request))` OR a small in-memory `defaultdict[ip → (count, window_start)]` reset hourly). If count > `settings.RATE_LIMIT_FAILED_AUTH_PER_HOUR`, raise `HTTPException(429, ERROR_MESSAGES["INTENTOS_AUTH_EXCEDIDOS"])`. Otherwise raise `HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": ...})`.
    - On success: do NOT reset the counter (still penalize correct logins from same IP after recent failures, until window expires).

- [ ] **Step 4: Add tests** for failed-auth bucket: 5 wrong attempts → 401; 6th wrong attempt from same IP → 429.

- [ ] **Step 5: PASS.**

- [ ] **Step 6: Commit** — `git add . && git commit -m "feat(auth): HTTP Basic + failed-auth bucket (5/h)"`.

### Task 4.2: Security headers + body size middleware

**Files:** `app/middleware.py`, `tests/test_security_headers.py`.

- [ ] **Step 1: Write failing test:**
  - HSTS, CSP, X-Content-Type-Options, Referrer-Policy, Permissions-Policy headers present.
  - CSP includes `frame-ancestors 'none'`.
  - POST body > limit returns 413.

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement `app/middleware.py`** with two `BaseHTTPMiddleware` classes:
  - `SecurityHeadersMiddleware`: appends headers per spec 5.3 to every response.
  - `BodySizeLimitMiddleware`: enforces in TWO layers:
    1. **Header check**: if `Content-Length` present and > limit → 413 immediately.
    2. **Stream check** (handles missing/lying CL and chunked transfer): wrap `request.receive` so when total bytes received exceeds limit, raises and returns 413. (Use `starlette.requests.ClientDisconnect`-safe pattern.)
  - `install_security_middleware(app, *, max_body_bytes)` registers both.

- [ ] **Step 4: Add stream-test** sending chunked POST with no Content-Length but body > limit → expect 413.

- [ ] **Step 5: PASS.**

- [ ] **Step 6: Commit** — `git add . && git commit -m "feat(middleware): security headers + 2-layer body size limit"`.

---

## Phase 5 — Routes

### Task 5.1: `/health`

**Files:** `app/routes/__init__.py`, `app/routes/health.py`, `tests/test_health.py`.

- [ ] **Step 1: Write test** — `GET /health` returns 200 with exact `{"status":"ok"}`, no auth required.
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** simple `APIRouter` with one GET returning the dict.
- [ ] **Step 4: PASS, commit** — `git add . && git commit -m "feat(routes): /health"`.

### Task 5.2: `/` HTML index

**Files:** `app/templates/index.html`, `app/static/htmx.min.js`, `app/static/style.css`, `app/routes/index.py`, `tests/test_index.py`.

- [ ] **Step 1: Vendor HTMX:**
  ```bash
  mkdir -p app/static
  curl -fsSL -o app/static/htmx.min.js https://unpkg.com/htmx.org@2.0.9/dist/htmx.min.js
  shasum -a 256 app/static/htmx.min.js   # registrar checksum en commit message
  ```

- [ ] **Step 2: Write `app/static/style.css`** — minimal styles for body, form, button, .result, .error, .meta, .htmx-request spinner.

- [ ] **Step 3: Write `app/templates/index.html`** — Spanish UI, single form posting to `/transcribe` via HTMX (`hx-post`, `hx-target="#result"`, `hx-disabled-elt="button"`).

- [ ] **Step 4: Write failing test:**
  - `GET /` without auth → 401.
  - `GET /` with valid Basic Auth → 200, response body contains `<form` and `/transcribe`.

- [ ] **Step 5: Run, expect FAIL.**

- [ ] **Step 6: Implement `app/routes/index.py`** with `Jinja2Templates(directory=...)`, GET `/` with `dependencies=[Depends(require_basic_auth)]` returning `_templates.TemplateResponse("index.html", {})`.

- [ ] **Step 7: PASS, commit** — `git add . && git commit -m "feat(routes): / HTML + HTMX vendored (sha256 in commit)"`.

### Task 5.3: `/transcribe` orchestration

**Files:** `app/routes/transcribe.py`, `tests/test_transcribe.py`.

- [ ] **Step 1: Write failing tests** with all I/O patched:
  - **Happy path**: `download_video` returns a fake video path, `probe_duration_sec` returns 12.0, `extract_audio_mp3` returns audio path, `transcribe_audio` returns "hola mundo" → endpoint returns 200 with that text.
  - **Bad URL**: `https://evil.com/` → 400 with `URL_NO_SOPORTADA` message.
  - **Long video**: `probe_duration_sec` returns 999.0 → 413 with `VIDEO_LARGO`.

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement `app/routes/transcribe.py`:**
  - `POST /transcribe` with `dependencies=[Depends(require_basic_auth)]`, `url: str = Form(..., max_length=2048)`, `settings = Depends(get_settings)`, `gate = Depends(_get_gate)`.
  - Validate URL → 400 on `UrlValidationError`.
  - Generate `request_uuid`, `make_request_dir(settings.TMPFS_BASE_DIR, uuid)`.
  - Inside `try/finally`:
    - Acquire gate.
    - `asyncio.wait_for(_pipeline(), timeout=TOTAL_REQUEST_TIMEOUT_SEC)`:
      - `await asyncio.to_thread(download_video, ...)` (yt-dlp is sync).
      - `await probe_duration_sec(...)` → 413 if > limit.
      - `await extract_audio_mp3(...)`.
      - `await transcribe_audio(...)`.
      - Return `{"texto", "duracion_seg", "modelo", "platform"}`.
    - Map errors: `DownloadError`→422, `AudioError`→504, `GeminiError`→502, `TimeoutError`→504.
  - `finally: drop_request_dir(workdir)`.

- [ ] **Step 4: Add structured logging in `/transcribe`**:
  - At pipeline start: `logger.info("transcribe.start", **{LOG_KEYS["REQ_ID"]: request_uuid, LOG_KEYS["URL_HMAC"]: url_hmac(v.raw, settings.HMAC_LOG_SECRET), LOG_KEYS["PLATFORM"]: v.platform})`.
  - At pipeline success: `logger.info("transcribe.success", request_uuid=..., duration_ms=...)`.
  - At each error path: `logger.warning("transcribe.error", request_uuid=..., reason=type(e).__name__)`.
  - **Never log the raw URL.**

- [ ] **Step 5: Add log-assertion test** using `structlog.testing.capture_logs()`:
  - Happy-path test asserts emitted events include `transcribe.start` and `transcribe.success` with required keys, and `URL_HMAC` is 8 hex chars (not raw URL).

- [ ] **Step 6: PASS.**

- [ ] **Step 7: Commit** — `git add . && git commit -m "feat(routes): /transcribe orchestration with gate + cleanup + structured logs"`.

---

## Phase 6 — Main app + rate limiting

### Task 6.1: `app/main.py`

- [ ] **Step 1: Implement `app/main.py`:**
  - Configure `structlog` for JSON output.
  - `lifespan` async context: on startup `sweep_orphans(settings.TMPFS_BASE_DIR, 3600)`; on shutdown sweep with age=0.
  - `Limiter(key_func=get_remote_address)` from slowapi.
  - `app = FastAPI(title="transcribe", lifespan=lifespan)`.
  - `app.state.limiter = limiter`; `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)`.
  - `install_security_middleware(app, max_body_bytes=settings.MAX_BODY_BYTES)`.
  - `app.mount("/static", StaticFiles(directory=...))`.
  - Include routers: `health.router`, `index.router`, `transcribe.router`.
  - Apply rate limit to `/transcribe`: `limiter.limit(f"{RATE_LIMIT_PER_MIN}/minute;{RATE_LIMIT_PER_DAY}/day")(transcribe.transcribe)`.

- [ ] **Step 2: Local smoke** — `cp .env.example .env`, fill real values, `make run` → `curl localhost:8000/health` → `{"status":"ok"}`. Stop server.

- [ ] **Step 3: Commit** — `git add . && git commit -m "feat(main): app factory + lifespan + rate limit"`.

---

## Phase 7 — Anti-duplication test

### Task 7.1: `tests/test_no_duplication.py`

- [ ] **Step 1: Write the test** scanning `app/**.py`:
  - `os.environ` substring forbidden outside `app/config.py`.
  - `generativelanguage.googleapis` forbidden outside `app/services/gemini.py`.
  - Spanish error string fragments ("Plataforma no soportada", "No se pudo descargar", "demasiado largo") forbidden outside `app/constants/messages.py`.
  - Tests and `conftest.py` are exempt by skipping any file under `tests/`.

- [ ] **Step 2: Run, expect PASS** (fix any violation by moving content into the canonical file).

- [ ] **Step 3: Commit** — `git add . && git commit -m "test: anti-duplication AST-style guard"`.

---

## Phase 8 — Dockerfile

### Task 8.1: Multi-stage Dockerfile

- [ ] **Step 1: Write `Dockerfile`** matching spec section 9 exactly:
  - **Stage 1 (builder)**: `python:3.13-slim` + `build-essential` + `uv 0.5.0` + `uv sync --frozen --no-dev --no-install-project`.
  - **Stage 2 (runtime)**: `python:3.13-slim` + `ffmpeg` + `tini` (apt). Non-root user `app`. Copy `.venv` from builder. Copy `app/` source. `EXPOSE 8000`. Healthcheck via `python -c "import urllib.request; ..."` (no curl). `ENTRYPOINT ["/usr/bin/tini","--"]`. `CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--timeout-graceful-shutdown","30"]`.

- [ ] **Step 2: Local build** — `make docker-build`. Expected: success, image ~250-350 MB.

- [ ] **Step 3: Local run with .env** — `make docker-run` (in background), `sleep 5`, `curl -fsS localhost:8000/health` → `{"status":"ok"}`. Stop container.

- [ ] **Step 4: Commit** — `git add Dockerfile && git commit -m "feat: multi-stage Dockerfile with tini + healthcheck"`.

---

## Phase 9 — GitHub repo

### Task 9.1: Push to GitHub

- [ ] **Step 1: Verify gh CLI auth** — `gh auth status`. If not logged in, ask user to run `gh auth login` interactively.

- [ ] **Step 2: Create private repo**:
  ```bash
  gh repo create michael-rsunion/transcribe --private --source=. \
    --description "Transcripción interna Reels/TikToks vía Gemini"
  ```

- [ ] **Step 3: Push** — `git branch -M main && git push -u origin main`.

- [ ] **Step 4: Verify** — `gh repo view michael-rsunion/transcribe`.

- [ ] **Step 5: Add Dependabot config** at `.github/dependabot.yml` covering weekly `yt-dlp` and `google-genai` bumps for the `uv` ecosystem.

- [ ] **Step 6: Commit + push** — `git add .github && git commit -m "chore: dependabot weekly for yt-dlp + google-genai" && git push`.

---

## Phase 10 — Coolify deploy (most sensitive)

> **Before EVERY step in this phase:** state explicitly which uuid you are about to operate on, and confirm it is NOT `d12s8a99e91bm5wy72plgfur`. Take a snapshot of CRM apps before and after the deploy.

### Task 10.0: Define CRM blocklist constants (programmatic safeguard)

- [ ] **Step 1: Create `scripts/coolify_constants.sh`** with:
  ```bash
  CRM_PROJECT_UUID="d12s8a99e91bm5wy72plgfur"
  PROTECTED_APP_NAMES=("CRM Backend API" "CRM Frontend" "CRM Worker" "sorteo-whatsapp")
  ```

- [ ] **Step 2: Create `scripts/assert_not_crm.sh`** that takes a uuid arg and exits non-zero if it equals `$CRM_PROJECT_UUID`. The agent must run this before any destructive `mcp__coolify__*` call.
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  source "$(dirname "$0")/coolify_constants.sh"
  if [[ "$1" == "$CRM_PROJECT_UUID" ]]; then
    echo "REFUSING: target uuid is the CRM project. Aborting." >&2
    exit 1
  fi
  ```
  `chmod +x scripts/assert_not_crm.sh`.

- [ ] **Step 3: Commit** — `git add scripts && git commit -m "chore: CRM uuid blocklist scripts"`.

### Task 10.1: Snapshot CRM apps (baseline + persisted)

- [ ] **Step 1: List apps** — `mcp__coolify__list_applications`. Save UUIDs + statuses of `CRM Backend API`, `CRM Frontend`, `CRM Worker`, `sorteo-whatsapp` (all should be `running:healthy`).

- [ ] **Step 2: Persist baseline snapshot** to `.coolify-snapshots/baseline-$(date +%Y%m%d-%H%M).json` (gitignored): capture per-app `{uuid, name, status}` for the four protected apps. This file is the comparison reference for Step 10.5.5.

- [ ] **Step 3: If ANY CRM app is not healthy, STOP and notify user.** Do not proceed with deploy.

### Task 10.2: Create Project "Transcribe"

- [ ] **Step 1: Create project** — `mcp__coolify__projects` (action=create, name="Transcribe", description="Transcripción interna Reels/TikToks. NO confundir con RSUnion CRM.").

- [ ] **Step 2: Capture `<NEW_PROJECT_UUID>`.** Verify it is NOT `d12s8a99e91bm5wy72plgfur`.

- [ ] **Step 3: List projects to confirm** — both `RSUnion` and `Transcribe` appear.

### Task 10.3: Create application

- [ ] **Step 1: Create app** — `mcp__coolify__application` (action=create, project_uuid=`<NEW_PROJECT_UUID>`, server_uuid=`q6zzyixsxp4hjbq6xn7arjeg`, environment_name="production", name="transcribe-app", git_repository="https://github.com/michael-rsunion/transcribe", git_branch="main", build_pack="dockerfile", ports_exposes="8000", fqdn="https://transcribe.rsunion.com", instant_deploy=false).

- [ ] **Step 2: Capture `<APP_UUID>`.**

- [ ] **Step 3: Run blocklist guard** before update — `bash scripts/assert_not_crm.sh "<NEW_PROJECT_UUID>"` must exit 0.

- [ ] **Step 4: Update with limits + healthcheck + tmpfs + traefik label**:
  - First, query current Coolify MCP capabilities — `mcp__coolify__search_docs` (query="tmpfs custom labels") to confirm whether `mcp__coolify__application` supports `custom_labels` and `tmpfs` flags directly. If the MCP exposes them, use them:
    ```
    mcp__coolify__application (action=update, application_uuid=<APP_UUID>,
      limits_memory="2G",
      limits_cpus="1",
      health_check_enabled=true,
      health_check_path="/health",
      custom_labels="traefik.http.middlewares.transcribe-bodysize.buffering.maxRequestBodyBytes=4096\ntraefik.http.routers.transcribe-app.middlewares=transcribe-bodysize",
      custom_docker_run_options="--tmpfs /tmp/transcribe:size=500m,mode=1777")
    ```
  - If the MCP does NOT support these fields, fall back: set them in the Coolify UI manually (Application → General → Custom Container Run Command + Custom Labels). The agent must surface this to the user with the exact strings to paste.

- [ ] **Step 5: Verify** — `mcp__coolify__get_application` (application_uuid=`<APP_UUID>`) and confirm the labels and limits are present in the response.

### Task 10.4: Set environment variables

- [ ] **Step 1: Generate secrets** locally:
  ```bash
  openssl rand -base64 24    # for BASIC_AUTH_PASS
  openssl rand -hex 32       # for HMAC_LOG_SECRET
  ```
  Save both for the user.

- [ ] **Step 2: Set vars** — `mcp__coolify__env_vars` (action=set, application_uuid=`<APP_UUID>`, vars={GEMINI_API_KEY, GEMINI_MODEL, BASIC_AUTH_USER="equipo", BASIC_AUTH_PASS=`<gen>`, HMAC_LOG_SECRET=`<gen>`, all numeric/string defaults from `app/config.py`}).

- [ ] **Step 3: Return generated password to user in chat.** Do NOT write it to docs.

### Task 10.5: First deploy

- [ ] **Step 0: Run blocklist guard** — `bash scripts/assert_not_crm.sh "<APP_UUID>"` must exit 0. Also verify `<APP_UUID>` is NOT in the snapshot of CRM app UUIDs from Task 10.1.

- [ ] **Step 1: Trigger deploy** — `mcp__coolify__deploy` (application_uuid=`<APP_UUID>`, force=false).

- [ ] **Step 2: Poll deployments every 15s (max 5 min)** — `mcp__coolify__list_deployments` (application_uuid=`<APP_UUID>`). Wait until `status=finished`.

- [ ] **Step 3: Read logs** — `mcp__coolify__application_logs` (application_uuid=`<APP_UUID>`, lines=200). Look for `Application startup complete`.

- [ ] **Step 4: External health check** — `curl -fsS https://transcribe.rsunion.com/health` → `{"status":"ok"}`.

- [ ] **Step 5: Verify CRM apps still healthy (programmatic compare against baseline)** ← critical:
  - `mcp__coolify__list_applications` → save to `.coolify-snapshots/post-deploy-$(date +%Y%m%d-%H%M).json`.
  - Diff baseline (Task 10.1 Step 2) vs post-deploy: for each protected app name, verify status is still `running:healthy`. If any flipped or disappeared, STOP, dump both snapshots to chat, and notify user. Do NOT continue.

### Task 10.6: Functional smoke test

- [ ] **Step 1: Tell user the credentials** (`equipo` / generated password) in chat.
- [ ] **Step 2: User opens** `https://transcribe.rsunion.com` in browser, logs in, pastes a public Reel URL, verifies transcription returns.
- [ ] **Step 3: Final CRM health check** — `mcp__coolify__list_applications`. All four CRM apps still `running:healthy`. ✅

---

## Phase 11 — Wrap-up

### Task 11.1: Expand README

- [ ] Add to `README.md`:
  - Env var table (name → purpose → where to set).
  - Deploy runbook (link to plan section 10).
  - **Rotation runbook**: how to rotate `GEMINI_API_KEY`, `BASIC_AUTH_PASS`, `HMAC_LOG_SECRET` via Coolify env vars (no redeploy needed).
  - Troubleshooting: yt-dlp updates (Dependabot), Gemini quota (budget alert), tmpfs full.
  - Pointer to spec.

- [ ] Commit + push.

### Task 11.2: Acceptance checklist

Verify ALL acceptance criteria from spec section 14:

1. [ ] `https://transcribe.rsunion.com/health` → 200, payload exact `{"status":"ok"}`, SSL valid.
2. [ ] Browser prompts Basic Auth on `/`.
3. [ ] Reel español → Spanish transcription.
4. [ ] TikTok inglés → English transcription (no translation).
5. [ ] Invalid URL → clear message from `ERROR_MESSAGES`.
6. [ ] URL resolving to private IP → 400.
7. [ ] Container respects `limits_memory=2G`, `limits_cpus=1`.
8. [ ] CRM apps `running:healthy` throughout.
9. [ ] `pytest` all green (incl. `test_no_duplication.py`).
10. [ ] Security headers present (verify with `curl -I`).
11. [ ] `gitleaks` + pre-commit pass.
12. [ ] README documents usage + rotation runbook.

---

## End state

- `https://transcribe.rsunion.com` live, password-protected, transcribing.
- Coolify project `Transcribe` separate from `RSUnion`.
- CRM untouched and verified healthy throughout.
- Repo `michael-rsunion/transcribe` private.
- Cost: $0/month incremental.
