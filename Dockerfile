FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MINGSHU_BROWSER_BIN=/usr/bin/chromium
ENV MINGSHU_FONT_SANS=/app/assets/fonts/NotoSansSC-Regular.ttf
ENV MINGSHU_FONT_SERIF=/app/assets/fonts/NotoSerifSC-Regular.ttf

WORKDIR /app

# Chromium renders the print-ready HTML spreads.  The bundled fonts are used
# by the book itself; fonts-noto-cjk also gives Chromium safe system fallbacks.
RUN apt-get update && apt-get install -y --no-install-recommends \
      chromium \
      curl \
      fonts-noto-cjk \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Probe /health every 30s; fail container after 3 consecutive misses.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1

# The shell form expands Zeabur's injected PORT.  Four request threads are
# sufficient because report work runs in its own single-worker queue.
CMD ["sh", "-c", "exec waitress-serve --host=0.0.0.0 --port=${PORT:-8000} --threads=4 --call web_server:create_app"]
