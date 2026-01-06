"""
PDF OCR Enhancement Tool - Main Application
A powerful tool to enhance scanned PDFs with OCR
"""
import time
import shutil
import subprocess
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from loguru import logger

from .config import settings
from .routers import pdf_router
from .models import HealthCheck


# Configure logging
logger.add(
    "logs/app.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


# Application startup/shutdown
start_time = datetime.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("=" * 50)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("=" * 50)

    # Check dependencies
    check_dependencies()

    # Create directories
    for directory in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory ready: {directory}")

    # Start cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())

    logger.info("Application started successfully!")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Application shutdown complete")


def check_dependencies():
    """Check if required system dependencies are available."""
    deps = {
        "tesseract": ["tesseract", "--version"],
        "ghostscript": ["gs", "--version"],
        "poppler": ["pdftoppm", "-v"]
    }

    for name, cmd in deps.items():
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"✓ {name} is available")
            else:
                logger.warning(f"✗ {name} check returned non-zero")
        except FileNotFoundError:
            logger.error(f"✗ {name} is NOT installed")
        except Exception as e:
            logger.warning(f"? {name} check failed: {e}")


async def periodic_cleanup():
    """Periodically clean up old files."""
    while True:
        try:
            await asyncio.sleep(settings.CLEANUP_INTERVAL_MINUTES * 60)
            from .utils.file_handler import FileHandler
            handler = FileHandler()
            result = await handler.cleanup_old_files()
            logger.info(f"Periodic cleanup: {result}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## PDF OCR Enhancement Tool

A powerful tool to enhance scanned PDF documents with OCR (Optical Character Recognition).

### Features
- **Text Recognition**: Add searchable text layer to scanned PDFs
- **Image Enhancement**: Deskew, denoise, and enhance contrast
- **Multiple Languages**: Support for 100+ languages
- **Quality Presets**: Choose between file size and quality
- **Automatic Optimization**: Compress output without losing quality

### How to Use
1. Upload your PDF file
2. Configure processing options
3. Wait for processing to complete
4. Download your enhanced PDF

### API Endpoints
- `POST /api/upload` - Upload PDF for processing
- `GET /api/status/{task_id}` - Check processing status
- `GET /api/download/{task_id}` - Download enhanced PDF
    """,
    contact={
        "name": "PDF OCR Enhancement Tool",
    },
    license_info={
        "name": "MIT",
    },
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    process_time = time.time() - start
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    return response


# Include routers
app.include_router(pdf_router)


# Health check endpoint
@app.get("/health", response_model=HealthCheck, tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    """
    # Check Tesseract
    tesseract_ok = False
    try:
        result = subprocess.run(["tesseract", "--version"], capture_output=True, timeout=5)
        tesseract_ok = result.returncode == 0
    except Exception:
        pass

    # Check Ghostscript
    gs_ok = False
    try:
        result = subprocess.run(["gs", "--version"], capture_output=True, timeout=5)
        gs_ok = result.returncode == 0
    except Exception:
        pass

    # Check Poppler
    poppler_ok = False
    try:
        result = subprocess.run(["pdftoppm", "-v"], capture_output=True, timeout=5)
        poppler_ok = True  # pdftoppm returns non-zero but works
    except Exception:
        pass

    # Get disk space
    try:
        disk = shutil.disk_usage("/")
        disk_space_gb = round(disk.free / (1024**3), 2)
    except Exception:
        disk_space_gb = -1

    # Calculate uptime
    uptime = (datetime.now() - start_time).total_seconds()

    return HealthCheck(
        status="healthy" if tesseract_ok else "degraded",
        version=settings.APP_VERSION,
        tesseract_available=tesseract_ok,
        ghostscript_available=gs_ok,
        poppler_available=poppler_ok,
        disk_space_gb=disk_space_gb,
        uptime_seconds=round(uptime, 2)
    )


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint - returns API information.
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "documentation": "/docs",
        "health": "/health"
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "message": "An internal error occurred",
            "detail": str(exc) if settings.DEBUG else "Please try again later"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
