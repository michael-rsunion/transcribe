"""HTTP Basic Auth + bucket de failed-auth (anti-brute-force)."""

import secrets
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import Settings, get_settings
from app.constants.messages import ERROR_MESSAGES

_security = HTTPBasic(realm="transcribe", auto_error=True)

# {ip: [(timestamp, count_in_window)]}
_failed_attempts: dict[str, list[float]] = defaultdict(list)
_WINDOW_SEC = 3600  # 1 hora


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _record_failure(ip: str) -> int:
    now = time.time()
    bucket = _failed_attempts[ip]
    # Limpiar entradas mas viejas que la ventana
    _failed_attempts[ip] = [t for t in bucket if now - t < _WINDOW_SEC]
    _failed_attempts[ip].append(now)
    return len(_failed_attempts[ip])


def _is_locked(ip: str, max_per_hour: int) -> bool:
    now = time.time()
    bucket = _failed_attempts.get(ip, [])
    bucket = [t for t in bucket if now - t < _WINDOW_SEC]
    _failed_attempts[ip] = bucket
    return len(bucket) >= max_per_hour


def reset_failed_auth_for_tests() -> None:
    """Helper SOLO para tests."""
    _failed_attempts.clear()


def require_basic_auth(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(_security),
    settings: Settings = Depends(get_settings),
) -> None:
    ip = _client_ip(request)

    if _is_locked(ip, settings.RATE_LIMIT_FAILED_AUTH_PER_HOUR):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ERROR_MESSAGES["INTENTOS_AUTH_EXCEDIDOS"],
        )

    user_ok = secrets.compare_digest(credentials.username, settings.BASIC_AUTH_USER)
    pass_ok = secrets.compare_digest(credentials.password, settings.BASIC_AUTH_PASS)

    if not (user_ok and pass_ok):
        _record_failure(ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="transcribe"'},
        )
