FROM python:3.11-slim

# ffmpeg (export MP3/WMA) + outils de compilation (pyworld)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg build-essential rubberband-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt

COPY . .

# La plupart des hébergeurs fournissent $PORT. Timeout long : le traitement dure quelques minutes.
ENV PORT=8000
CMD gunicorn app:app --bind 0.0.0.0:${PORT} --timeout 600 --workers 1
