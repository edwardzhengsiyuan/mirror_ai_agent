FROM python:3.12-alpine3.23@sha256:33a47b0a92c0766bdd77cd82bbaa4c320ce48db01a2bfe1782920ca7a16e3744

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Use the supported Alpine runtime without Debian's unused mount/login/systemd
# packages; retain its package inventory so vulnerability scans remain complete.
RUN apk upgrade --no-cache

COPY requirements-bootstrap.lock requirements.lock ./
# The base image's installer has separate advisories from application packages.
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-bootstrap.lock \
 && python -m pip install --no-cache-dir --require-hashes -r requirements.lock \
 && python -m pip check \
 && python -m pip uninstall --yes pip \
 && python -c "import ensurepip, pathlib, shutil; shutil.rmtree(pathlib.Path(ensurepip.__file__).parent)"
# Dependencies are immutable at runtime. Remove the actual installer/vendor code
# and ensurepip's old wheel, not package metadata or vulnerability scan findings.

COPY . .

EXPOSE 8000

# Probe /health every 30s; fail container after 3 consecutive misses.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).read()"]

# --threads=8 matches the local stress-test sweet spot and matters for SSE
# concurrency (one thread per long-running /v1/ask_stream request).
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8000", "--threads=8", "--call", "web_server:create_app"]
