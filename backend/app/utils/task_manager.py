"""
Task Manager for tracking PDF processing jobs
"""
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger

from ..models import ProcessingStatus, TaskStatus, ProcessingOptions
from ..services.preprocessor import ImagePreprocessor
from ..services.ocr_service import OCRService
from ..services.optimizer import PDFOptimizer
from .file_handler import FileHandler


class TaskManager:
    """
    Manages PDF processing tasks including creation, tracking, and execution.
    Uses in-memory storage (suitable for single-instance deployment).
    """

    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.file_handler = FileHandler()
        self.preprocessor = ImagePreprocessor()
        self.ocr_service = OCRService()
        self.optimizer = PDFOptimizer()

    def create_task(
        self,
        original_filename: str,
        file_size: int,
        options: ProcessingOptions
    ) -> str:
        """
        Create a new processing task.

        Args:
            original_filename: Original uploaded filename
            file_size: Size of uploaded file in bytes
            options: Processing options

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()

        self.tasks[task_id] = {
            "task_id": task_id,
            "status": ProcessingStatus.PENDING,
            "progress": 0,
            "current_step": "Waiting to process",
            "message": "Task created",
            "pages_processed": 0,
            "total_pages": 0,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "original_filename": original_filename,
            "file_size_original": file_size,
            "file_size_output": 0,
            "processing_time_seconds": 0,
            "error_details": None,
            "options": options,
            "input_path": None,
            "output_path": None,
            "download_url": None
        }

        logger.info(f"Created task: {task_id} for {original_filename}")
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskStatus]:
        """Get task status by ID."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return TaskStatus(
            task_id=task["task_id"],
            status=task["status"],
            progress=task["progress"],
            current_step=task["current_step"],
            message=task["message"],
            pages_processed=task["pages_processed"],
            total_pages=task["total_pages"],
            created_at=task["created_at"],
            updated_at=task["updated_at"],
            completed_at=task["completed_at"],
            download_url=task["download_url"],
            original_filename=task["original_filename"],
            file_size_original=task["file_size_original"],
            file_size_output=task["file_size_output"],
            processing_time_seconds=task["processing_time_seconds"],
            error_details=task["error_details"]
        )

    def update_task(
        self,
        task_id: str,
        status: Optional[ProcessingStatus] = None,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs
    ) -> None:
        """Update task properties."""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task["updated_at"] = datetime.now()

        if status is not None:
            task["status"] = status
        if progress is not None:
            task["progress"] = min(max(progress, 0), 100)
        if current_step is not None:
            task["current_step"] = current_step
        if message is not None:
            task["message"] = message

        for key, value in kwargs.items():
            if key in task:
                task[key] = value

        logger.debug(f"Updated task {task_id}: status={task['status']}, progress={task['progress']}")

    async def process_task(self, task_id: str, input_path: Path) -> None:
        """
        Execute the full PDF processing pipeline.

        Args:
            task_id: Task ID
            input_path: Path to uploaded PDF
        """
        start_time = datetime.now()
        task = self.tasks.get(task_id)

        if not task:
            logger.error(f"Task not found: {task_id}")
            return

        task["input_path"] = input_path
        options: ProcessingOptions = task["options"]

        try:
            # Update status
            self.update_task(
                task_id,
                status=ProcessingStatus.PROCESSING,
                progress=5,
                current_step="Analyzing PDF",
                message="Starting processing..."
            )

            # Get PDF info
            pdf_info = self.ocr_service.get_pdf_info(input_path)
            if "error" in pdf_info:
                raise Exception(f"Could not read PDF: {pdf_info['error']}")

            total_pages = pdf_info.get("pages", 0)
            task["total_pages"] = total_pages

            self.update_task(
                task_id,
                progress=10,
                current_step=f"Found {total_pages} pages",
                total_pages=total_pages
            )

            # Get output path
            output_path = self.file_handler.get_output_path(
                task_id,
                task["original_filename"]
            )
            task["output_path"] = output_path

            # Progress callback
            def progress_callback(progress: int, step: str):
                self.update_task(
                    task_id,
                    progress=progress,
                    current_step=step
                )

            # Step 1: OCR Processing (includes preprocessing via OCRmyPDF)
            self.update_task(
                task_id,
                status=ProcessingStatus.OCR_PROCESSING,
                progress=20,
                current_step="Running OCR engine",
                message="Recognizing text..."
            )

            ocr_result = self.ocr_service.process_pdf(
                input_path=input_path,
                output_path=output_path,
                options=options,
                progress_callback=progress_callback
            )

            if not ocr_result["success"]:
                raise Exception(ocr_result.get("message", "OCR processing failed"))

            self.update_task(
                task_id,
                progress=80,
                current_step="OCR complete",
                message="Text layer added successfully"
            )

            # Step 2: Optimization (if enabled)
            if options.optimize_size:
                self.update_task(
                    task_id,
                    status=ProcessingStatus.OPTIMIZING,
                    progress=85,
                    current_step="Optimizing PDF",
                    message="Compressing output..."
                )

                # Create temp path for optimized output
                optimized_path = self.file_handler.get_temp_path(
                    task_id,
                    "optimized.pdf"
                )

                opt_result = self.optimizer.optimize_pdf(
                    input_path=output_path,
                    output_path=optimized_path,
                    quality_preset=options.quality_preset
                )

                if opt_result["success"] and opt_result.get("optimized"):
                    # Replace output with optimized version
                    import shutil
                    shutil.move(str(optimized_path), str(output_path))
                    logger.info(f"Optimization: {opt_result.get('compression_ratio', 0):.1f}% reduction")

            # Calculate final file size
            output_size = self.file_handler.get_file_size(output_path)
            processing_time = (datetime.now() - start_time).total_seconds()

            # Mark as completed
            self.update_task(
                task_id,
                status=ProcessingStatus.COMPLETED,
                progress=100,
                current_step="Processing complete",
                message="PDF enhanced successfully!",
                completed_at=datetime.now(),
                file_size_output=output_size,
                processing_time_seconds=round(processing_time, 2),
                download_url=f"/api/download/{task_id}",
                pages_processed=total_pages
            )

            logger.info(
                f"Task {task_id} completed in {processing_time:.1f}s. "
                f"Size: {task['file_size_original']} -> {output_size} bytes"
            )

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            self.update_task(
                task_id,
                status=ProcessingStatus.FAILED,
                progress=0,
                current_step="Processing failed",
                message=str(e),
                error_details=str(e),
                completed_at=datetime.now(),
                processing_time_seconds=(datetime.now() - start_time).total_seconds()
            )

    def get_output_path(self, task_id: str) -> Optional[Path]:
        """Get the output file path for a completed task."""
        task = self.tasks.get(task_id)
        if task and task.get("output_path"):
            path = Path(task["output_path"])
            if path.exists():
                return path
        return None

    def get_all_tasks(self, limit: int = 100) -> list[TaskStatus]:
        """Get all tasks, most recent first."""
        tasks = sorted(
            self.tasks.values(),
            key=lambda t: t["created_at"],
            reverse=True
        )[:limit]

        return [
            TaskStatus(
                task_id=t["task_id"],
                status=t["status"],
                progress=t["progress"],
                current_step=t["current_step"],
                message=t["message"],
                pages_processed=t["pages_processed"],
                total_pages=t["total_pages"],
                created_at=t["created_at"],
                updated_at=t["updated_at"],
                completed_at=t["completed_at"],
                download_url=t["download_url"],
                original_filename=t["original_filename"],
                file_size_original=t["file_size_original"],
                file_size_output=t["file_size_output"],
                processing_time_seconds=t["processing_time_seconds"],
                error_details=t["error_details"]
            )
            for t in tasks
        ]

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task and its associated files."""
        if task_id not in self.tasks:
            return False

        # Clean up files
        await self.file_handler.cleanup_task_files(task_id)

        # Remove from memory
        del self.tasks[task_id]
        logger.info(f"Deleted task: {task_id}")

        return True

    def get_statistics(self) -> dict:
        """Get processing statistics."""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t["status"] == ProcessingStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t["status"] == ProcessingStatus.FAILED)
        processing = sum(1 for t in self.tasks.values() if t["status"] in [
            ProcessingStatus.PROCESSING,
            ProcessingStatus.PREPROCESSING,
            ProcessingStatus.OCR_PROCESSING,
            ProcessingStatus.OPTIMIZING
        ])

        total_pages = sum(t["pages_processed"] for t in self.tasks.values())
        total_input_size = sum(t["file_size_original"] for t in self.tasks.values())
        total_output_size = sum(t["file_size_output"] for t in self.tasks.values())

        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "processing": processing,
            "pending": total - completed - failed - processing,
            "total_pages_processed": total_pages,
            "total_input_size_mb": round(total_input_size / (1024 * 1024), 2),
            "total_output_size_mb": round(total_output_size / (1024 * 1024), 2),
            "average_compression_percent": round(
                (1 - total_output_size / total_input_size) * 100, 1
            ) if total_input_size > 0 else 0
        }


# Global task manager instance
task_manager = TaskManager()
