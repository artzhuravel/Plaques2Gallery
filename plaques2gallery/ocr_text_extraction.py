"""
OCR text extraction module for museum plaque images.

This module provides functions to preprocess images and extract text using
Tesseract OCR. It handles common challenges with plaque photographs such as:
- Incorrect orientation
- Inverted colors (light text on dark background)
- Noisy or low-contrast images

Functions:
    rotate: Auto-rotate image based on detected orientation
    invert: Invert image if background is darker than foreground
    custom_binarize: Find optimal binarization threshold for OCR
    remove_noise: Apply morphological operations to reduce noise
"""

from __future__ import annotations

import logging
import re

import cv2  # type: ignore[import-untyped]
import numpy as np
from numpy.typing import NDArray
import pytesseract  # type: ignore[import-untyped]

from plaques2gallery.config import BINARIZE_THRESHOLD_RANGE

logger = logging.getLogger(__name__)

# Type alias for image arrays (8-bit unsigned integers)
Image = NDArray[np.uint8]


def rotate(image: Image) -> Image:
    """
    Automatically rotates the input image based on its detected orientation.

    Uses Tesseract's orientation and script detection (OSD) to determine
    the rotation angle needed to make text upright.

    Parameters
    ----------
    image : Image
        Input grayscale or RGB image.

    Returns
    -------
    Image
        Rotated image in correct upright orientation.
    """
    try:
        osd = pytesseract.image_to_osd(image)
        match = re.search(r'Rotate: (\d+)', str(osd))
        if match is None:
            return image
        rotation = int(match.group(1))

        if rotation == 90:
            logger.debug("Rotating image 90 degrees clockwise")
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            logger.debug("Rotating image 180 degrees")
            return cv2.rotate(image, cv2.ROTATE_180)
        elif rotation == 270:
            logger.debug("Rotating image 90 degrees counter-clockwise")
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            return image
    except Exception as e:
        logger.warning(f"Failed to detect orientation: {e}")
        return image


def invert(image: Image) -> Image:
    """
    Inverts the input image if the background is darker than the foreground.

    This heuristic assumes that OCR performs better with dark text on light
    background. The function counts black vs. white pixels after binarization
    and inverts if dark regions dominate.

    Parameters
    ----------
    image : Image
        Input grayscale image.

    Returns
    -------
    Image
        Possibly inverted image (same dtype and shape as input).
    """
    _, binarized = cv2.threshold(image, 125, 255, cv2.THRESH_BINARY)
    num_black_px = int(np.sum(binarized == 0))
    num_white_px = int(np.sum(binarized == 255))

    if num_black_px > num_white_px:
        logger.debug("Inverting image (dark background detected)")
        return cv2.bitwise_not(image)
    else:
        return image


def custom_binarize(image: Image) -> tuple[int, Image | None]:
    """
    Applies threshold sweeping to find the binarization value that maximizes OCR confidence.

    Iterates over a range of thresholds and applies Tesseract OCR to each
    binarized version. The threshold yielding the highest average OCR
    confidence is selected.

    Parameters
    ----------
    image : Image
        Grayscale image to be binarized.

    Returns
    -------
    tuple[int, Image | None]
        (best_threshold, best_binary_image), where best_binary_image is the
        binarized version corresponding to the best OCR confidence.
        Returns (0, None) if no valid threshold is found.
    """
    best_conf: float = 0
    best_thresh_val: int = 0
    best_binary: Image | None = None

    start, stop, step = BINARIZE_THRESHOLD_RANGE
    for t in range(start, stop, step):
        _, binary = cv2.threshold(image, t, 255, cv2.THRESH_BINARY)
        data = pytesseract.image_to_data(binary, output_type=pytesseract.Output.DICT)
        confidences: list[int] = data['conf']
        avg_conf = sum(confidences) / len(confidences) if confidences else 0

        if avg_conf > best_conf:
            best_conf = avg_conf
            best_thresh_val = t
            best_binary = binary

    logger.debug(f"Best binarization threshold: {best_thresh_val} (confidence: {best_conf:.2f})")
    return best_thresh_val, best_binary


def remove_noise(image: Image) -> Image:
    """
    Reduces noise in a grayscale image using morphological operations and median filtering.

    Applies a combination of dilation, erosion, morphological closing,
    and median blurring to enhance the clarity of textual regions and
    suppress background artifacts.

    Parameters
    ----------
    image : Image
        Input grayscale image.

    Returns
    -------
    Image
        Denoised image suitable for OCR.
    """
    kernel = np.ones((2, 2), np.uint8)
    result = cv2.dilate(image, kernel, iterations=1)

    kernel = np.ones((1, 1), np.uint8)
    result = cv2.erode(result, kernel, iterations=10)
    result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel)
    result = cv2.medianBlur(result, 3)

    logger.debug("Applied noise removal filters")
    return result
