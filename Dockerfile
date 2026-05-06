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

# Copy venv from builder
COPY --from=builder --chown=app:app /build/.venv /home/app/.venv
ENV PATH="/home/app/.venv/bin:$PATH"

# Copy app code
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

# Healthcheck sin curl: usa python stdlib
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health',timeout=3).getcode()==200 else 1)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--timeout-graceful-shutdown", "30"]
