"""
Plaques2Gallery - Automated pipeline to match museum plaque photographs to artwork images.

This package provides tools for:
- OCR text extraction from museum plaque images
- AI-powered text cleaning using Google Gemini
- Web search for artwork images
- Automated image downloading and extraction
"""

from plaques2gallery.ocr_text_extraction import (
    rotate,
    invert,
    custom_binarize,
    remove_noise,
)
from plaques2gallery.clean_museum_plaques_text import clean_extracted_text
from plaques2gallery.web_search import google_search_top3
from plaques2gallery.web_scraping import (
    process_a_painting,
    extract_main_image_from_page,
)

__version__ = "1.0.0"
__all__ = [
    "rotate",
    "invert",
    "custom_binarize",
    "remove_noise",
    "clean_extracted_text",
    "google_search_top3",
    "process_a_painting",
    "extract_main_image_from_page",
]
