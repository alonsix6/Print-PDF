"""
PDF Processing API Routes
"""
import asyncio
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional
from loguru import logger

from ..models import (
    ProcessingOptions,
    ProcessingStatus,
    TaskCreate,
    TaskStatus,
    QualityPreset
)
from ..utils.task_manager import task_manager
from ..utils.file_handler import FileHandler
from ..config import settings

router = APIRouter(prefix="/api", tags=["PDF Processing"])
file_handler = FileHandler()


@router.post("/upload", response_model=TaskCreate)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to process"),
    language: str = Query(default="spa+eng", description="OCR language(s)"),
    deskew: bool = Query(default=True, description="Auto-straighten pages"),
    denoise: bool = Query(default=True, description="Remove noise"),
    enhance_contrast: bool = Query(default=True, description="Enhance contrast"),
    remove_background: bool = Query(default=False, description="Remove background"),
    target_dpi: int = Query(default=300, ge=150, le=600, description="Target DPI"),
    upscale_images: bool = Query(default=True, description="Upscale low-res images"),
    quality_preset: QualityPreset = Query(default=QualityPreset.EBOOK, description="Quality preset"),
    optimize_size: bool = Query(default=True, description="Optimize output size"),
    force_ocr: bool = Query(default=False, description="Force OCR even if text exists"),
    rotate_pages: bool = Query(default=True, description="Auto-rotate pages")
):
    """
    Upload a PDF file for OCR enhancement.

    Returns a task ID that can be used to check processing status
    and download the enhanced PDF.
    """
    logger.info(f"Upload request: {file.filename}, size: {file.size}")

    # Read file content
    content = await file.read()

    # Validate file
    validation = file_handler.validate_file(content, file.filename)
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid file",
                "errors": validation["errors"]
            }
        )

    # Create processing options
    options = ProcessingOptions(
        language=language,
        deskew=deskew,
        denoise=denoise,
        enhance_contrast=enhance_contrast,
        remove_background=remove_background,
        target_dpi=target_dpi,
        upscale_images=upscale_images,
        quality_preset=quality_preset,
        optimize_size=optimize_size,
        force_ocr=force_ocr,
        rotate_pages=rotate_pages
    )

    # Create task
    task_id = task_manager.create_task(
        original_filename=file.filename,
        file_size=len(content),
        options=options
    )

    # Save uploaded file
    input_path = await file_handler.save_upload(content, file.filename, task_id)

    # Start background processing
    background_tasks.add_task(
        task_manager.process_task,
        task_id,
        input_path
    )

    logger.info(f"Task created: {task_id}")

    return TaskCreate(
        task_id=task_id,
        status=ProcessingStatus.PENDING,
        message="File uploaded successfully. Processing started.",
        created_at=task_manager.tasks[task_id]["created_at"]
    )


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_status(task_id: str):
    """
    Get the current status of a processing task.

    Returns detailed information about progress, errors, and download URL when complete.
    """
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Task not found: {task_id}"}
        )

    return task


@router.get("/download/{task_id}")
async def download_pdf(task_id: str):
    """
    Download the enhanced PDF file.

    Only available after processing is complete.
    """
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Task not found: {task_id}"}
        )

    if task.status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "File not ready for download",
                "status": task.status.value
            }
        )

    output_path = task_manager.get_output_path(task_id)

    if not output_path or not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail={"message": "Output file not found"}
        )

    # Create download filename
    original_name = task.original_filename
    download_name = original_name.rsplit('.', 1)[0] + "_enhanced.pdf"

    return FileResponse(
        path=output_path,
        filename=download_name,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"'
        }
    )


@router.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """
    Delete a task and its associated files.
    """
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Task not found: {task_id}"}
        )

    success = await task_manager.delete_task(task_id)

    if success:
        return {"message": "Task deleted successfully", "task_id": task_id}
    else:
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to delete task"}
        )


@router.get("/tasks")
async def list_tasks(limit: int = Query(default=50, le=100)):
    """
    List all processing tasks.
    """
    tasks = task_manager.get_all_tasks(limit=limit)
    return {"tasks": tasks, "total": len(tasks)}


@router.get("/statistics")
async def get_statistics():
    """
    Get processing statistics.
    """
    stats = task_manager.get_statistics()
    disk_usage = file_handler.get_disk_usage()

    return {
        "processing": stats,
        "storage": disk_usage
    }


@router.post("/cleanup")
async def cleanup_old_files(hours: int = Query(default=24, ge=1, le=168)):
    """
    Clean up files older than specified hours.
    Admin endpoint for maintenance.
    """
    result = await file_handler.cleanup_old_files(hours)
    return {
        "message": "Cleanup completed",
        "result": result
    }


@router.get("/languages")
async def get_supported_languages():
    """
    Get list of supported OCR languages.
    """
    languages = task_manager.ocr_service.get_supported_languages()
    return {
        "languages": languages,
        "default": "spa+eng"
    }


@router.get("/presets")
async def get_quality_presets():
    """
    Get available quality presets with descriptions.
    """
    return {
        "presets": [
            {
                "value": "screen",
                "name": "Screen",
                "description": "Smallest file size, 72 DPI. Best for web viewing.",
                "dpi": 72
            },
            {
                "value": "ebook",
                "name": "E-Book",
                "description": "Balanced quality and size, 150 DPI. Recommended for most uses.",
                "dpi": 150
            },
            {
                "value": "printer",
                "name": "Printer",
                "description": "High quality, 300 DPI. For printing documents.",
                "dpi": 300
            },
            {
                "value": "prepress",
                "name": "Prepress",
                "description": "Maximum quality, 300 DPI. For professional printing.",
                "dpi": 300
            }
        ],
        "default": "ebook"
    }
