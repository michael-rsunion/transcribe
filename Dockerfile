FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tini \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /usr/local/bin/uv

RUN useradd -m -u 1000 app
WORKDIR /home/app

# Install deps (creates /home/app/.venv with correct shebangs in place)
COPY --chown=app:app pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project \
    && chown -R app:app /home/app/.venv

# Copy app code
COPY --chown=app:app app ./app

USER app
ENV PATH="/home/app/.venv/bin:$PATH"

EXPOSE 8000

# Healthcheck via python stdlib (no curl/wget needed in container path)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/home/app/.venv/bin/python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--timeout-graceful-shutdown", "30"]
