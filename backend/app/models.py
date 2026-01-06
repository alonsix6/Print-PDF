"""
Pydantic models for request/response validation
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Status of PDF processing task"""
    PENDING = "pending"
    PROCESSING = "processing"
    PREPROCESSING = "preprocessing"
    OCR_PROCESSING = "ocr_processing"
    OPTIMIZING = "optimizing"
    COMPLETED = "completed"
    FAILED = "failed"


class QualityPreset(str, Enum):
    """Output quality presets"""
    SCREEN = "screen"      # 72 DPI - smallest
    EBOOK = "ebook"        # 150 DPI - balanced
    PRINTER = "printer"    # 300 DPI - high quality
    PREPRESS = "prepress"  # 300 DPI - maximum


class ProcessingOptions(BaseModel):
    """Options for PDF processing"""

    # OCR Settings
    language: str = Field(
        default="spa+eng",
        description="OCR language(s), e.g., 'eng', 'spa', 'spa+eng'"
    )

    # Image Enhancement
    deskew: bool = Field(
        default=True,
        description="Automatically straighten rotated pages"
    )
    denoise: bool = Field(
        default=True,
        description="Remove noise and artifacts"
    )
    enhance_contrast: bool = Field(
        default=True,
        description="Improve text visibility with contrast enhancement"
    )
    remove_background: bool = Field(
        default=False,
        description="Remove background for cleaner output"
    )

    # Resolution
    target_dpi: int = Field(
        default=300,
        ge=150,
        le=600,
        description="Target DPI for output (150-600)"
    )
    upscale_images: bool = Field(
        default=True,
        description="Upscale low-resolution images"
    )

    # Output
    quality_preset: QualityPreset = Field(
        default=QualityPreset.EBOOK,
        description="Output quality preset"
    )
    optimize_size: bool = Field(
        default=True,
        description="Optimize final PDF size"
    )

    # Advanced
    force_ocr: bool = Field(
        default=False,
        description="Force OCR even if text layer exists"
    )
    rotate_pages: bool = Field(
        default=True,
        description="Auto-rotate pages to correct orientation"
    )


class TaskCreate(BaseModel):
    """Response when creating a new task"""
    task_id: str
    status: ProcessingStatus
    message: str
    created_at: datetime


class TaskStatus(BaseModel):
    """Current status of a processing task"""
    task_id: str
    status: ProcessingStatus
    progress: int = Field(ge=0, le=100)
    current_step: str
    message: str
    pages_processed: int = 0
    total_pages: int = 0
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None
    original_filename: str
    file_size_original: int = 0
    file_size_output: int = 0
    processing_time_seconds: float = 0
    error_details: Optional[str] = None


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    tesseract_available: bool
    ghostscript_available: bool
    poppler_available: bool
    disk_space_gb: float
    uptime_seconds: float


class SupportedLanguage(BaseModel):
    """Supported OCR language"""
    code: str
    name: str
    native_name: str


class APIInfo(BaseModel):
    """API information response"""
    name: str
    version: str
    description: str
    supported_languages: list[SupportedLanguage]
    max_file_size_mb: int
    max_pages: int
    quality_presets: dict
