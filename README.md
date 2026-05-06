# Transcribe

App interna de RSUnion. Pega un Reel/TikTok/Short y devuelve la transcripción en el idioma original.

- **Stack**: Python 3.13 · FastAPI · yt-dlp · ffmpeg · Gemini 2.5 Flash · HTMX
- **Deploy**: Coolify (project `Transcribe`), https://transcribe.rsunion.com
- **Auth**: HTTP Basic
- **Costo mensual incremental**: $0

Ver [`docs/specs/2026-05-06-transcribe-design.md`](docs/specs/2026-05-06-transcribe-design.md) para diseño completo y [`docs/superpowers/plans/2026-05-06-transcribe-implementation.md`](docs/superpowers/plans/2026-05-06-transcribe-implementation.md) para el plan de implementación.

## Local

```bash
cp .env.example .env       # rellenar valores reales
make install
make test
make run                   # http://localhost:8000
```

## Deploy

Push a `main` → Coolify auto-redeploys (configurado en Coolify, no en GitHub Actions).

## Mantenimiento

- **Rotar `GEMINI_API_KEY`**: actualizar en Google AI Studio + Coolify env var (no requiere rebuild).
- **Rotar `BASIC_AUTH_PASS`**: `openssl rand -base64 24`, actualizar en Coolify env var.
- **yt-dlp upgrades**: Dependabot abre PR semanal; mergear si E2E test pasa.
