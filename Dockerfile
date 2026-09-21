FROM python:3.13-slim

# System dependencies: tesseract-ocr for the OCR pipeline, libmagic1 for
# python-magic's file-type detection. tesseract-ocr on Debian pulls in
# English language data automatically.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching -- only reinstalls if
# requirements.txt actually changes, not on every code edit)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and frontend as siblings, matching the relative-path
# assumptions baked into main.py ("../frontend/...") which expects to be
# run from inside backend/
COPY backend/ ./backend/
COPY frontend/ ./frontend/

WORKDIR /app/backend

# Render injects $PORT at runtime -- shell form (not exec/JSON array) is
# required here so the $PORT variable actually gets substituted.
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT