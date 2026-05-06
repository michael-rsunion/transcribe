"""Keys y helpers de logging estructurado. Cero strings de log inline."""

import hashlib
import hmac

LOG_KEYS: dict[str, str] = {
    "REQ_ID": "request_uuid",
    "URL_HMAC": "url_hmac",
    "PLATFORM": "platform",
    "DURATION_MS": "duration_ms",
    "EVENT": "event",
}


def url_hmac(url: str, secret: str) -> str:
    """HMAC-SHA256 de la URL truncado a 8 hex chars (no-reversible sin secret)."""
    return hmac.new(secret.encode(), url.encode(), hashlib.sha256).hexdigest()[:8]
