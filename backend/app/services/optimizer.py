"""
PDF Optimization Service using Ghostscript
Handles compression and final quality optimization
"""
import subprocess
import os
from pathlib import Path
from typing import Optional
from loguru import logger

from ..models import QualityPreset


class PDFOptimizer:
    """
    PDF optimization service using Ghostscript.
    Provides compression and quality optimization for output PDFs.
    """

    def __init__(self):
        self.ghostscript_available = self._check_ghostscript()
        self.gs_command = self._get_gs_command()

    def _check_ghostscript(self) -> bool:
        """Check if Ghostscript is installed."""
        for cmd in ["gs", "gswin64c", "gswin32c"]:
            try:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info(f"Ghostscript available: {cmd} v{result.stdout.strip()}")
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        logger.warning("Ghostscript not available")
        return False

    def _get_gs_command(self) -> str:
        """Get the correct Ghostscript command for the platform."""
        for cmd in ["gs", "gswin64c", "gswin32c"]:
            try:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return cmd
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return "gs"

    def optimize_pdf(
        self,
        input_path: Path,
        output_path: Path,
        quality_preset: QualityPreset = QualityPreset.EBOOK,
        custom_dpi: Optional[int] = None
    ) -> dict:
        """
        Optimize a PDF file using Ghostscript.

        Args:
            input_path: Path to input PDF
            output_path: Path for optimized output
            quality_preset: Quality preset (screen, ebook, printer, prepress)
            custom_dpi: Optional custom DPI override

        Returns:
            Dictionary with optimization results
        """
        if not self.ghostscript_available:
            logger.warning("Ghostscript not available, skipping optimization")
            # Just copy the file
            import shutil
            shutil.copy(input_path, output_path)
            return {
                "success": True,
                "message": "Optimization skipped (Ghostscript not available)",
                "optimized": False
            }

        logger.info(f"Optimizing PDF with preset: {quality_preset.value}")

        # Build command
        cmd = self._build_command(input_path, output_path, quality_preset, custom_dpi)

        logger.debug(f"Ghostscript command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode == 0:
                # Calculate compression ratio
                original_size = input_path.stat().st_size
                output_size = output_path.stat().st_size
                compression_ratio = (1 - output_size / original_size) * 100

                logger.info(f"Optimization complete. Compression: {compression_ratio:.1f}%")

                return {
                    "success": True,
                    "message": "PDF optimized successfully",
                    "optimized": True,
                    "original_size": original_size,
                    "output_size": output_size,
                    "compression_ratio": compression_ratio
                }
            else:
                logger.error(f"Ghostscript error: {result.stderr}")
                return {
                    "success": False,
                    "message": f"Optimization failed: {result.stderr}",
                    "optimized": False
                }

        except subprocess.TimeoutExpired:
            logger.error("Ghostscript optimization timed out")
            return {
                "success": False,
                "message": "Optimization timed out",
                "optimized": False
            }
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            return {
                "success": False,
                "message": f"Optimization error: {str(e)}",
                "optimized": False
            }

    def _build_command(
        self,
        input_path: Path,
        output_path: Path,
        preset: QualityPreset,
        custom_dpi: Optional[int] = None
    ) -> list[str]:
        """Build the Ghostscript command."""
        # Map presets to Ghostscript settings
        preset_settings = {
            QualityPreset.SCREEN: "/screen",
            QualityPreset.EBOOK: "/ebook",
            QualityPreset.PRINTER: "/printer",
            QualityPreset.PREPRESS: "/prepress"
        }

        gs_preset = preset_settings.get(preset, "/ebook")

        cmd = [
            self.gs_command,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={gs_preset}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-dSAFER",
            # Prevent Ghostscript from adding its own metadata
            "-dDetectDuplicateImages=true",
            "-dCompressFonts=true",
            "-dSubsetFonts=true",
        ]

        # Add custom DPI if specified
        if custom_dpi:
            cmd.extend([
                f"-dColorImageResolution={custom_dpi}",
                f"-dGrayImageResolution={custom_dpi}",
                f"-dMonoImageResolution={custom_dpi}",
            ])

        # Higher quality settings for printer/prepress
        if preset in [QualityPreset.PRINTER, QualityPreset.PREPRESS]:
            cmd.extend([
                "-dColorImageDownsampleType=/Bicubic",
                "-dGrayImageDownsampleType=/Bicubic",
                "-dMonoImageDownsampleType=/Bicubic",
                "-dAutoRotatePages=/None",
            ])

        # Output and input
        cmd.extend([
            f"-sOutputFile={output_path}",
            str(input_path)
        ])

        return cmd

    def get_pdf_size_estimate(self, input_path: Path, preset: QualityPreset) -> dict:
        """
        Estimate output size based on preset.
        These are rough estimates based on typical compression ratios.
        """
        input_size = input_path.stat().st_size

        # Typical compression ratios
        ratios = {
            QualityPreset.SCREEN: 0.3,    # 70% reduction
            QualityPreset.EBOOK: 0.5,     # 50% reduction
            QualityPreset.PRINTER: 0.7,   # 30% reduction
            QualityPreset.PREPRESS: 0.9   # 10% reduction
        }

        ratio = ratios.get(preset, 0.5)
        estimated_size = int(input_size * ratio)

        return {
            "input_size_bytes": input_size,
            "input_size_mb": round(input_size / (1024 * 1024), 2),
            "estimated_output_bytes": estimated_size,
            "estimated_output_mb": round(estimated_size / (1024 * 1024), 2),
            "estimated_reduction_percent": round((1 - ratio) * 100)
        }

    def repair_pdf(self, input_path: Path, output_path: Path) -> dict:
        """
        Attempt to repair a corrupted PDF using Ghostscript.
        """
        if not self.ghostscript_available:
            return {
                "success": False,
                "message": "Ghostscript not available"
            }

        cmd = [
            self.gs_command,
            "-o", str(output_path),
            "-sDEVICE=pdfwrite",
            "-dPDFSETTINGS=/prepress",
            str(input_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "PDF repaired successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"Repair failed: {result.stderr}"
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"Repair error: {str(e)}"
            }
