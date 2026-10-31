
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY require.txt .
RUN pip install --no-cache-dir -r require.txt

COPY app.py .
COPY templates ./templates

EXPOSE 8000

CMD ["sh", "-c", "gunicorn --workers 2 --threads 2 --timeout 180 --bind 0.0.0.0:${PORT:-8000} app:app"]
