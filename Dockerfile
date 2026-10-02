FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Apply distribution security updates; the health probe needs no extra OS client.
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY . .

EXPOSE 8000

# Probe /health every 30s; fail container after 3 consecutive misses.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).read()"]

# --threads=8 matches the local stress-test sweet spot and matters for SSE
# concurrency (one thread per long-running /v1/ask_stream request).
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "--threads=8", "--call", "web_server:create_app"]
