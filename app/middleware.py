"""Middleware: security headers + body size limit (header + stream)."""

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

CSP = (
    "default-src 'self'; script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'none'; "
    "base-uri 'self'; form-action 'self'"
)

PERMISSIONS_POLICY = "geolocation=(), camera=(), microphone=(), payment=()"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)
        resp.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Permissions-Policy"] = PERMISSIONS_POLICY
        return resp


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Enforces body size en 2 capas: Content-Length header + stream count."""

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        # Capa 1: Content-Length declarado
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self.max_bytes:
                    return Response(status_code=413, content="too large")
            except ValueError:
                return Response(status_code=400, content="bad content-length")

        # Capa 2: stream-level guard (envuelve receive para contar bytes)
        body_received = 0
        original_receive = request.receive
        too_large = False

        async def guarded_receive():
            nonlocal body_received, too_large
            msg = await original_receive()
            if msg["type"] == "http.request":
                body_received += len(msg.get("body") or b"")
                if body_received > self.max_bytes:
                    too_large = True
            return msg

        # Reemplazamos el receive del request scope
        request._receive = guarded_receive  # type: ignore[attr-defined]

        resp = await call_next(request)
        if too_large:
            return Response(status_code=413, content="too large")
        return resp


def install_security_middleware(app: FastAPI, *, max_body_bytes: int) -> None:
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=max_body_bytes)
    app.add_middleware(SecurityHeadersMiddleware)
