import cv2
import numpy as np
import pytesseract
import re

def rotate(image):
    """
    Automatically rotates the input image based on its detected orientation.

    Uses Tesseract's orientation script detection (OSD) to determine
    the correct upright orientation of the text and applies the appropriate
    rotation to align the text horizontally.

    Parameters
    ----------
    image : numpy.ndarray
        Input grayscale or RGB image.

    Returns
    -------
    numpy.ndarray
        Rotated image in correct upright orientation.
    """
    osd = pytesseract.image_to_osd(image)
    rotation = int(re.search(r'Rotate: (\d+)', osd).group(1))

    if rotation == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif rotation == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        return image

def invert(image):
    """
    Inverts the input image if the background is darker than the foreground.

    This heuristic assumes that OCR performs better with dark text on light background.
    The function counts black vs. white pixels after binarization and inverts
    if dark regions dominate.

    Parameters
    ----------
    image : numpy.ndarray
        Input grayscale image.

    Returns
    -------
    numpy.ndarray
        Possibly inverted image (same dtype and shape as input).
    """
    _, binarized = cv2.threshold(image, 125, 255, cv2.THRESH_BINARY)
    num_black_px = np.sum(binarized == 0)
    num_white_px = np.sum(binarized == 255)

    if num_black_px > num_white_px:
        return cv2.bitwise_not(image)
    else:
        return image

def custom_binarize(image):
    """
    Applies threshold sweeping to find the binarization value that maximizes OCR confidence.

    Iterates over a range of thresholds and applies Tesseract OCR to each binarized version.
    The threshold yielding the highest average OCR confidence is selected.

    Parameters
    ----------
    image : numpy.ndarray
        Grayscale image to be binarized.

    Returns
    -------
    tuple
        (best_threshold, best_binary_image), where best_binary_image is the
        binarized version corresponding to the best OCR confidence.
    """
    best_conf = 0
    best_thresh_val = 0
    best_binary = None

    for t in range(0, 240, 10):
        _, binary = cv2.threshold(image, t, 255, cv2.THRESH_BINARY)
        data = pytesseract.image_to_data(binary, output_type=pytesseract.Output.DICT)
        confidences = data['conf']
        avg_conf = sum(confidences) / len(confidences) if confidences else 0

        if avg_conf > best_conf:
            best_conf = avg_conf
            best_thresh_val = t
            best_binary = binary

    return best_thresh_val, best_binary

def remove_noise(image):
    """
    Reduces noise in a grayscale image using morphological operations and median filtering.

    Applies a combination of dilation, erosion, morphological closing,
    and median blurring to enhance the clarity of textual regions and suppress
    background artifacts.

    Parameters
    ----------
    image : numpy.ndarray
        Input grayscale image.

    Returns
    -------
    numpy.ndarray
        Denoised image suitable for OCR.
    """
    kernel = np.ones((2, 2), np.uint8)
    image = cv2.dilate(image, kernel, iterations=1)

    kernel = np.ones((1, 1), np.uint8)
    image = cv2.erode(image, kernel, iterations=10)

    image = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
    image = cv2.medianBlur(image, 3)

    return image