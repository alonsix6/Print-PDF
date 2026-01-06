"""
File handling utilities for PDF processing
"""
import os
import magic
import aiofiles
import asyncio
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger

from ..config import settings


class FileHandler:
    """
    Handles file operations including upload, validation, and cleanup.
    """

    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "application/x-pdf",
    }

    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.output_dir = settings.OUTPUT_DIR
        self.temp_dir = settings.TEMP_DIR

    async def save_upload(
        self,
        file_content: bytes,
        filename: str,
        task_id: str
    ) -> Path:
        """
        Save uploaded file to disk.

        Args:
            file_content: File bytes
            filename: Original filename
            task_id: Task ID for organizing files

        Returns:
            Path to saved file
        """
        # Create task directory
        task_dir = self.upload_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        file_path = task_dir / safe_filename

        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        logger.info(f"Saved upload: {file_path}")
        return file_path

    def validate_file(self, file_content: bytes, filename: str) -> dict:
        """
        Validate uploaded file.

        Args:
            file_content: File bytes
            filename: Original filename

        Returns:
            Dictionary with validation results
        """
        errors = []

        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            errors.append(
                f"File too large: {file_size_mb:.1f}MB (max: {settings.MAX_FILE_SIZE_MB}MB)"
            )

        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            errors.append(f"Invalid file extension: {ext}")

        # Check MIME type using magic bytes
        try:
            mime_type = magic.from_buffer(file_content, mime=True)
            if mime_type not in self.ALLOWED_MIME_TYPES:
                errors.append(f"Invalid file type: {mime_type}")
        except Exception as e:
            logger.warning(f"Could not detect MIME type: {e}")

        # Check if PDF is not empty/corrupted
        if len(file_content) < 100:
            errors.append("File appears to be empty or corrupted")

        # Basic PDF header check
        if not file_content[:5] == b"%PDF-":
            errors.append("File does not appear to be a valid PDF")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "file_size_mb": round(file_size_mb, 2),
            "mime_type": mime_type if 'mime_type' in dir() else "unknown"
        }

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and other issues."""
        # Remove path components
        filename = Path(filename).name

        # Replace problematic characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, "_")

        # Limit length
        if len(filename) > 200:
            ext = Path(filename).suffix
            filename = filename[:200 - len(ext)] + ext

        return filename

    def get_output_path(self, task_id: str, original_filename: str) -> Path:
        """Get the output path for a processed file."""
        task_dir = self.output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # Add _enhanced suffix
        name = Path(original_filename).stem
        ext = Path(original_filename).suffix or ".pdf"

        return task_dir / f"{name}_enhanced{ext}"

    def get_temp_path(self, task_id: str, suffix: str = "") -> Path:
        """Get a temporary file path."""
        task_dir = self.temp_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        return task_dir / f"temp_{suffix}"

    async def cleanup_task_files(self, task_id: str) -> None:
        """Remove all files associated with a task."""
        for directory in [self.upload_dir, self.output_dir, self.temp_dir]:
            task_dir = directory / task_id
            if task_dir.exists():
                try:
                    import shutil
                    await asyncio.to_thread(shutil.rmtree, task_dir)
                    logger.info(f"Cleaned up: {task_dir}")
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")

    async def cleanup_old_files(self, hours: int = None) -> dict:
        """
        Remove files older than specified hours.

        Args:
            hours: Maximum file age in hours (defaults to config setting)

        Returns:
            Dictionary with cleanup statistics
        """
        if hours is None:
            hours = settings.FILE_RETENTION_HOURS

        cutoff_time = datetime.now() - timedelta(hours=hours)
        stats = {"directories_removed": 0, "errors": 0}

        for directory in [self.upload_dir, self.output_dir, self.temp_dir]:
            if not directory.exists():
                continue

            for task_dir in directory.iterdir():
                if not task_dir.is_dir():
                    continue

                try:
                    # Check directory modification time
                    mtime = datetime.fromtimestamp(task_dir.stat().st_mtime)
                    if mtime < cutoff_time:
                        import shutil
                        await asyncio.to_thread(shutil.rmtree, task_dir)
                        stats["directories_removed"] += 1
                        logger.debug(f"Removed old directory: {task_dir}")
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"Cleanup error for {task_dir}: {e}")

        logger.info(f"Cleanup complete: {stats}")
        return stats

    def get_disk_usage(self) -> dict:
        """Get disk usage statistics for storage directories."""
        total_size = 0
        file_count = 0

        for directory in [self.upload_dir, self.output_dir, self.temp_dir]:
            if directory.exists():
                for path in directory.rglob("*"):
                    if path.is_file():
                        total_size += path.stat().st_size
                        file_count += 1

        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count
        }

    def file_exists(self, path: Path) -> bool:
        """Check if a file exists."""
        return path.exists() and path.is_file()

    def get_file_size(self, path: Path) -> int:
        """Get file size in bytes."""
        if path.exists():
            return path.stat().st_size
        return 0
