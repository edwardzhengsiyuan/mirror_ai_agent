FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# curl is used by HEALTHCHECK below.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Probe /health every 30s; fail container after 3 consecutive misses.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

# --threads=8 matches the local stress-test sweet spot and matters for SSE
# concurrency (one thread per long-running /v1/ask_stream request).
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "--threads=8", "--call", "web_server:create_app"]
