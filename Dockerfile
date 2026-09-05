# PraMaan backend — serves the API and the static frontend from one process.
# Build context is the repo root: `docker build -t pramaan .` from ~/pramaan.
FROM python:3.13-slim

# tesseract-ocr-hin/ben/guj/kan/mar/pan/tam/tel = the same Indic scripts installed
# via Homebrew in local dev (see README) — real OCR, not a stub, inside the image too.
RUN apt-get update && apt-get install -y --no-install-recommends \
      tesseract-ocr \
      tesseract-ocr-hin tesseract-ocr-ben tesseract-ocr-guj tesseract-ocr-kan \
      tesseract-ocr-mar tesseract-ocr-pan tesseract-ocr-tam tesseract-ocr-tel \
      libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/
COPY docs/ docs/

WORKDIR /app/backend
ENV UPLOAD_DIR=/app/backend/uploads
RUN mkdir -p "$UPLOAD_DIR"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
