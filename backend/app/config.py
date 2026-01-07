"""
Configuration settings for PDF OCR Enhancement Tool
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # App Info
    APP_NAME: str = "PDF OCR Enhancement Tool"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", 8000))

    # CORS - Frontend URLs
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # Add your Netlify domain here
    ]

    # File Storage
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    TEMP_DIR: Path = BASE_DIR / "temp"

    # File Limits
    MAX_FILE_SIZE_MB: int = 200  # Maximum file size in MB
    MAX_PAGES: int = 500  # Maximum pages per PDF
    ALLOWED_EXTENSIONS: set[str] = {".pdf"}

    # Processing Defaults
    DEFAULT_LANGUAGE: str = "spa+eng"
    DEFAULT_DPI: int = 300
    MIN_DPI: int = 150
    MAX_DPI: int = 600

    # OCR Settings
    TESSERACT_PATH: Optional[str] = None
    OCR_TIMEOUT_PER_PAGE: int = 120  # seconds

    # Cleanup
    FILE_RETENTION_HOURS: int = 24
    CLEANUP_INTERVAL_MINUTES: int = 60

    # Ghostscript Quality Presets
    QUALITY_PRESETS: dict = {
        "screen": {"dpi": 72, "description": "Smallest size, web viewing"},
        "ebook": {"dpi": 150, "description": "Balanced quality/size"},
        "printer": {"dpi": 300, "description": "High quality printing"},
        "prepress": {"dpi": 300, "description": "Maximum quality"}
    }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Create directories if they don't exist
for directory in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
