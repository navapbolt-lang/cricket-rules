# Stage 1: Build
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Copy packages to appuser's home directory
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV HOME=/home/appuser

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/frontend/widget && chown -R appuser:appuser /app/frontend

EXPOSE 8000

# Set HuggingFace cache to writable temp directory
ENV HF_HOME=/tmp/hf_cache
ENV SENTENCE_TRANSFORMERS_HOME=/tmp/hf_cache
ENV TRANSFORMERS_CACHE=/tmp/hf_cache

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/api/v1/health')" || exit 1

USER appuser

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
