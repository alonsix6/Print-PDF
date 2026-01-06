"""
Image Preprocessing Service
Advanced image enhancement for optimal OCR accuracy
"""
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Tuple
from loguru import logger


class ImagePreprocessor:
    """
    Comprehensive image preprocessing pipeline for OCR enhancement.
    Applies multiple techniques to improve text recognition accuracy.
    """

    def __init__(self, target_dpi: int = 300):
        self.target_dpi = target_dpi
        self.min_dpi_for_ocr = 300

    def process_image(
        self,
        image: np.ndarray,
        deskew: bool = True,
        denoise: bool = True,
        enhance_contrast: bool = True,
        remove_background: bool = False,
        current_dpi: int = 72
    ) -> np.ndarray:
        """
        Apply full preprocessing pipeline to an image.

        Args:
            image: Input image as numpy array (BGR format from OpenCV)
            deskew: Correct rotation/skew
            denoise: Remove noise artifacts
            enhance_contrast: Apply contrast enhancement
            remove_background: Remove background for cleaner output
            current_dpi: Current DPI of the image

        Returns:
            Preprocessed image as numpy array
        """
        logger.debug(f"Starting preprocessing pipeline - Shape: {image.shape}")

        # Convert to grayscale for processing if color
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 1. Upscale if needed (must be done first)
        if current_dpi < self.min_dpi_for_ocr:
            scale_factor = self.target_dpi / current_dpi
            gray = self._upscale_image(gray, scale_factor)
            logger.debug(f"Upscaled image by {scale_factor:.2f}x")

        # 2. Deskew (correct rotation)
        if deskew:
            gray = self._deskew(gray)
            logger.debug("Applied deskew correction")

        # 3. Denoise
        if denoise:
            gray = self._denoise(gray)
            logger.debug("Applied denoising")

        # 4. Enhance contrast
        if enhance_contrast:
            gray = self._enhance_contrast(gray)
            logger.debug("Applied contrast enhancement")

        # 5. Remove background (optional, can affect quality)
        if remove_background:
            gray = self._remove_background(gray)
            logger.debug("Applied background removal")

        # 6. Final sharpening
        gray = self._sharpen(gray)
        logger.debug("Applied final sharpening")

        return gray

    def _upscale_image(self, image: np.ndarray, scale_factor: float) -> np.ndarray:
        """
        Upscale image using high-quality interpolation.
        Uses LANCZOS (cv2.INTER_LANCZOS4) for best quality.
        """
        if scale_factor <= 1.0:
            return image

        # Limit scale factor to avoid memory issues
        scale_factor = min(scale_factor, 4.0)

        new_width = int(image.shape[1] * scale_factor)
        new_height = int(image.shape[0] * scale_factor)

        # Use INTER_LANCZOS4 for high-quality upscaling
        upscaled = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=cv2.INTER_LANCZOS4
        )

        return upscaled

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Detect and correct skew in the image.
        Uses projection profile analysis for accurate angle detection.
        """
        # Binary threshold for angle detection
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find all non-zero points
        coords = np.column_stack(np.where(binary > 0))

        if len(coords) < 100:
            return image

        # Get the minimum area rectangle
        try:
            angle = cv2.minAreaRect(coords)[-1]

            # Adjust angle
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            # Only correct if angle is significant but not too extreme
            if abs(angle) > 0.5 and abs(angle) < 15:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)

                # Get rotation matrix
                rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

                # Apply rotation with white background
                rotated = cv2.warpAffine(
                    image,
                    rotation_matrix,
                    (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
                return rotated
        except Exception as e:
            logger.warning(f"Deskew failed: {e}")

        return image

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """
        Remove noise while preserving text edges.
        Uses Non-Local Means Denoising for best results.
        """
        # Apply Non-Local Means Denoising
        # Parameters tuned for document images
        denoised = cv2.fastNlMeansDenoising(
            image,
            h=10,  # Filter strength
            templateWindowSize=7,  # Size of template patch
            searchWindowSize=21  # Size of area to search
        )

        # Apply mild bilateral filter to smooth while keeping edges
        denoised = cv2.bilateralFilter(denoised, 5, 75, 75)

        return denoised

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
        This works better than global histogram equalization for documents.
        """
        # Create CLAHE object with tuned parameters
        clahe = cv2.createCLAHE(
            clipLimit=2.0,  # Contrast limiting
            tileGridSize=(8, 8)  # Grid size for adaptive processing
        )

        enhanced = clahe.apply(image)

        return enhanced

    def _remove_background(self, image: np.ndarray) -> np.ndarray:
        """
        Remove background using adaptive thresholding.
        Creates a clean black text on white background.
        """
        # Use adaptive thresholding (Gaussian)
        # This handles varying illumination across the document
        binary = cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15,  # Size of neighborhood
            C=10  # Constant subtracted from mean
        )

        return binary

    def _sharpen(self, image: np.ndarray) -> np.ndarray:
        """
        Apply mild sharpening to enhance text edges.
        Uses unsharp masking technique.
        """
        # Create gaussian blur
        blurred = cv2.GaussianBlur(image, (0, 0), 3)

        # Unsharp mask: original + (original - blurred) * amount
        sharpened = cv2.addWeighted(
            image, 1.5,  # Original weight
            blurred, -0.5,  # Blurred weight (negative for sharpening)
            0
        )

        return sharpened

    def auto_rotate(self, image: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        Detect and correct page orientation (0, 90, 180, 270 degrees).
        Returns the rotated image and the rotation angle applied.
        """
        # This is a simplified version - OCRmyPDF handles this better
        # We'll rely on OCRmyPDF's --rotate-pages feature
        return image, 0

    def detect_dpi(self, image_path: Path) -> int:
        """
        Detect the DPI of an image from its metadata.
        Returns 72 as default if not found.
        """
        try:
            with Image.open(image_path) as img:
                dpi = img.info.get('dpi', (72, 72))
                if isinstance(dpi, tuple):
                    return int(dpi[0])
                return int(dpi)
        except Exception:
            return 72

    def process_pil_image(
        self,
        pil_image: Image.Image,
        deskew: bool = True,
        denoise: bool = True,
        enhance_contrast: bool = True,
        remove_background: bool = False,
        current_dpi: int = 72
    ) -> Image.Image:
        """
        Process a PIL Image and return a PIL Image.
        Convenience method for integration with pdf2image.
        """
        # Convert PIL to OpenCV format
        if pil_image.mode == 'RGB':
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        elif pil_image.mode == 'RGBA':
            cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGBA2BGR)
        elif pil_image.mode == 'L':
            cv_image = np.array(pil_image)
        else:
            cv_image = np.array(pil_image.convert('RGB'))
            cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)

        # Process
        processed = self.process_image(
            cv_image,
            deskew=deskew,
            denoise=denoise,
            enhance_contrast=enhance_contrast,
            remove_background=remove_background,
            current_dpi=current_dpi
        )

        # Convert back to PIL
        if len(processed.shape) == 2:
            return Image.fromarray(processed, mode='L')
        else:
            return Image.fromarray(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB))

    def analyze_image_quality(self, image: np.ndarray) -> dict:
        """
        Analyze image quality metrics.
        Useful for determining which preprocessing steps are needed.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Calculate metrics
        metrics = {
            "resolution": f"{image.shape[1]}x{image.shape[0]}",
            "mean_brightness": float(np.mean(gray)),
            "contrast": float(np.std(gray)),
            "is_low_contrast": float(np.std(gray)) < 50,
            "estimated_noise": self._estimate_noise(gray),
            "sharpness": self._estimate_sharpness(gray)
        }

        return metrics

    def _estimate_noise(self, image: np.ndarray) -> float:
        """Estimate noise level in the image using Laplacian variance."""
        laplacian = cv2.Laplacian(image, cv2.CV_64F)
        return float(laplacian.var())

    def _estimate_sharpness(self, image: np.ndarray) -> float:
        """Estimate sharpness using gradient magnitude."""
        gx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        return float(np.sqrt(gx**2 + gy**2).mean())
