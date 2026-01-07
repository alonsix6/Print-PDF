# PDF OCR Enhancement Tool - Docker Image
# Optimized for Railway deployment with ALL OCRmyPDF dependencies

FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    DEBIAN_FRONTEND=noninteractive \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Set working directory
WORKDIR /app

# Install system dependencies including ALL OCRmyPDF optional deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Tesseract OCR and language packs
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-ita \
    tesseract-ocr-por \
    tesseract-ocr-chi-sim \
    tesseract-ocr-jpn \
    tesseract-ocr-kor \
    tesseract-ocr-ara \
    tesseract-ocr-rus \
    # Poppler for PDF rendering
    poppler-utils \
    # Ghostscript for PDF optimization
    ghostscript \
    # OCRmyPDF optional dependencies
    unpaper \
    pngquant \
    # Build tools for jbig2enc
    git \
    build-essential \
    autotools-dev \
    automake \
    libtool \
    libleptonica-dev \
    pkg-config \
    zlib1g-dev \
    # Required for python-magic
    libmagic1 \
    # OpenCV dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Build and install jbig2enc from source (for better PDF compression)
RUN git clone https://github.com/agl/jbig2enc.git /tmp/jbig2enc \
    && cd /tmp/jbig2enc \
    && ./autogen.sh \
    && ./configure \
    && make \
    && make install \
    && ldconfig \
    && rm -rf /tmp/jbig2enc

# Clean up build dependencies to reduce image size
RUN apt-get purge -y --auto-remove \
    git \
    build-essential \
    autotools-dev \
    automake \
    libtool \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy requirements first for better caching
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/app ./app

# Create necessary directories
RUN mkdir -p uploads outputs temp logs && \
    chmod -R 755 uploads outputs temp logs

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port (Railway will override with $PORT)
EXPOSE 8000

# Run the application with shell to expand $PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
