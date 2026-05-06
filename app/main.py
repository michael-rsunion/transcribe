"""App factory: lifespan + middleware + routes + rate limit."""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.middleware import install_security_middleware
from app.routes import health, index, transcribe
from app.services.cleanup import sweep_orphans

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    base = Path(settings.TMPFS_BASE_DIR)
    base.mkdir(parents=True, exist_ok=True)
    sweep_orphans(base, max_age_seconds=3600)
    yield
    # Final cleanup en shutdown: borrar todo lo que quede
    sweep_orphans(base, max_age_seconds=0)


_settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="transcribe", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

install_security_middleware(app, max_body_bytes=_settings.MAX_BODY_BYTES)

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

app.include_router(health.router)
app.include_router(index.router)
app.include_router(transcribe.router)

# Aplicar rate limit al endpoint de transcribe
limiter.limit(
    f"{_settings.RATE_LIMIT_PER_MIN}/minute;{_settings.RATE_LIMIT_PER_DAY}/day"
)(transcribe.transcribe)
