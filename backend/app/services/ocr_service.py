"""
OCR Service using OCRmyPDF
Handles text recognition and PDF text layer creation
"""
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Callable
from loguru import logger

from ..config import settings
from ..models import ProcessingOptions, QualityPreset


class OCRService:
    """
    OCR processing service using OCRmyPDF.
    Provides comprehensive OCR with multiple configuration options.
    """

    def __init__(self):
        self.tesseract_available = self._check_tesseract()
        self.available_languages = self._get_available_languages()

    def _check_tesseract(self) -> bool:
        """Check if Tesseract is installed and available."""
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                logger.info(f"Tesseract available: {version}")
                return True
        except Exception as e:
            logger.error(f"Tesseract not available: {e}")
        return False

    def _get_available_languages(self) -> list[str]:
        """Get list of available Tesseract languages."""
        try:
            result = subprocess.run(
                ["tesseract", "--list-langs"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Parse output - first line is path, rest are languages
                lines = result.stdout.strip().split('\n')
                languages = [lang.strip() for lang in lines[1:] if lang.strip()]
                logger.info(f"Available languages: {len(languages)}")
                return languages
        except Exception as e:
            logger.warning(f"Could not get languages: {e}")
        return ["eng", "spa"]

    def process_pdf(
        self,
        input_path: Path,
        output_path: Path,
        options: ProcessingOptions,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> dict:
        """
        Process a PDF with OCR using OCRmyPDF.

        Args:
            input_path: Path to input PDF
            output_path: Path for output PDF
            options: Processing options
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with processing results and statistics
        """
        logger.info(f"Starting OCR processing: {input_path.name}")

        if progress_callback:
            progress_callback(10, "Preparing OCR engine...")

        # Build OCRmyPDF command
        cmd = self._build_command(input_path, output_path, options)

        logger.debug(f"OCRmyPDF command: {' '.join(cmd)}")

        if progress_callback:
            progress_callback(20, "Running OCR (this may take a while)...")

        # Run OCRmyPDF
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.OCR_TIMEOUT_PER_PAGE * settings.MAX_PAGES
            )

            if result.returncode == 0:
                logger.info("OCR processing completed successfully")
                if progress_callback:
                    progress_callback(90, "OCR completed successfully")

                return {
                    "success": True,
                    "message": "OCR processing completed",
                    "output_path": str(output_path),
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }

            # Handle specific return codes
            elif result.returncode == 6:
                # Already has text layer
                logger.warning("PDF already has text layer")
                if not options.force_ocr:
                    # Copy original to output
                    shutil.copy(input_path, output_path)
                    return {
                        "success": True,
                        "message": "PDF already has text layer (copied original)",
                        "output_path": str(output_path),
                        "already_has_text": True
                    }

            else:
                logger.error(f"OCR failed with code {result.returncode}: {result.stderr}")
                return {
                    "success": False,
                    "message": f"OCR processing failed: {result.stderr}",
                    "returncode": result.returncode,
                    "stderr": result.stderr
                }

        except subprocess.TimeoutExpired:
            logger.error("OCR processing timed out")
            return {
                "success": False,
                "message": "OCR processing timed out"
            }
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return {
                "success": False,
                "message": f"OCR error: {str(e)}"
            }

    def _build_command(
        self,
        input_path: Path,
        output_path: Path,
        options: ProcessingOptions
    ) -> list[str]:
        """Build the OCRmyPDF command with all options."""
        cmd = ["ocrmypdf"]

        # Language settings
        cmd.extend(["-l", options.language])

        # Deskew
        if options.deskew:
            cmd.append("--deskew")

        # Rotate pages to correct orientation
        if options.rotate_pages:
            cmd.append("--rotate-pages")

        # Force OCR if requested
        if options.force_ocr:
            cmd.append("--force-ocr")
        else:
            cmd.append("--skip-text")

        # Image processing options
        if options.denoise or options.enhance_contrast:
            cmd.append("--clean")

        # Remove background (creates binarized output)
        if options.remove_background:
            cmd.append("--clean-final")

        # Output DPI
        cmd.extend(["--output-type", "pdfa-2"])

        # Optimize based on quality preset
        optimize_level = self._get_optimize_level(options.quality_preset)
        cmd.extend(["--optimize", str(optimize_level)])

        # Additional quality options
        if options.quality_preset == QualityPreset.PREPRESS:
            cmd.append("--pdfa-image-compression")
            cmd.append("lossless")

        # Progress
        cmd.append("--verbose")
        cmd.append("1")

        # Input and output
        cmd.append(str(input_path))
        cmd.append(str(output_path))

        return cmd

    def _get_optimize_level(self, preset: QualityPreset) -> int:
        """Get OCRmyPDF optimization level based on quality preset."""
        levels = {
            QualityPreset.SCREEN: 3,    # Maximum compression
            QualityPreset.EBOOK: 2,     # Balanced
            QualityPreset.PRINTER: 1,   # Light optimization
            QualityPreset.PREPRESS: 0   # No optimization (max quality)
        }
        return levels.get(preset, 2)

    def get_pdf_info(self, pdf_path: Path) -> dict:
        """
        Get information about a PDF file.
        Uses pypdf for analysis.
        """
        try:
            from pypdf import PdfReader

            reader = PdfReader(pdf_path)
            info = {
                "pages": len(reader.pages),
                "has_text": False,
                "encrypted": reader.is_encrypted,
                "metadata": {}
            }

            # Check if has text
            for page in reader.pages[:3]:  # Check first 3 pages
                text = page.extract_text()
                if text and len(text.strip()) > 50:
                    info["has_text"] = True
                    break

            # Get metadata
            if reader.metadata:
                info["metadata"] = {
                    "title": reader.metadata.get("/Title", ""),
                    "author": reader.metadata.get("/Author", ""),
                    "creator": reader.metadata.get("/Creator", ""),
                    "producer": reader.metadata.get("/Producer", "")
                }

            return info

        except Exception as e:
            logger.error(f"Error reading PDF info: {e}")
            return {"error": str(e)}

    def validate_language(self, language: str) -> bool:
        """Check if the specified language is available."""
        # Handle multiple languages (spa+eng format)
        langs = language.split("+")
        for lang in langs:
            if lang not in self.available_languages:
                return False
        return True

    def get_supported_languages(self) -> list[dict]:
        """Get list of supported languages with names."""
        language_names = {
            "eng": ("English", "English"),
            "spa": ("Spanish", "Español"),
            "fra": ("French", "Français"),
            "deu": ("German", "Deutsch"),
            "ita": ("Italian", "Italiano"),
            "por": ("Portuguese", "Português"),
            "rus": ("Russian", "Русский"),
            "chi_sim": ("Chinese (Simplified)", "简体中文"),
            "chi_tra": ("Chinese (Traditional)", "繁體中文"),
            "jpn": ("Japanese", "日本語"),
            "kor": ("Korean", "한국어"),
            "ara": ("Arabic", "العربية"),
            "hin": ("Hindi", "हिन्दी"),
            "nld": ("Dutch", "Nederlands"),
            "pol": ("Polish", "Polski"),
            "tur": ("Turkish", "Türkçe"),
            "vie": ("Vietnamese", "Tiếng Việt"),
            "tha": ("Thai", "ไทย"),
            "swe": ("Swedish", "Svenska"),
            "dan": ("Danish", "Dansk"),
            "nor": ("Norwegian", "Norsk"),
            "fin": ("Finnish", "Suomi"),
            "ces": ("Czech", "Čeština"),
            "ell": ("Greek", "Ελληνικά"),
            "heb": ("Hebrew", "עברית"),
            "hun": ("Hungarian", "Magyar"),
            "ind": ("Indonesian", "Bahasa Indonesia"),
            "msa": ("Malay", "Bahasa Melayu"),
            "ron": ("Romanian", "Română"),
            "slk": ("Slovak", "Slovenčina"),
            "ukr": ("Ukrainian", "Українська"),
            "cat": ("Catalan", "Català"),
            "hrv": ("Croatian", "Hrvatski"),
            "bul": ("Bulgarian", "Български"),
            "lit": ("Lithuanian", "Lietuvių"),
            "lav": ("Latvian", "Latviešu"),
            "est": ("Estonian", "Eesti"),
            "slv": ("Slovenian", "Slovenščina"),
        }

        result = []
        for lang in self.available_languages:
            names = language_names.get(lang, (lang, lang))
            result.append({
                "code": lang,
                "name": names[0],
                "native_name": names[1]
            })

        return sorted(result, key=lambda x: x["name"])
