"""
Configuration constants for the Plaques2Gallery pipeline.

This module centralizes all configurable parameters used throughout the pipeline,
making it easy to adjust behavior without modifying core logic.
"""

# =============================================================================
# OCR Settings
# =============================================================================

#: Languages to use for Tesseract OCR (supports multi-language plaques)
OCR_LANGUAGES = "eng+deu+ita+kor+chi_sim+jpn"

#: Threshold range for custom binarization (start, stop, step)
BINARIZE_THRESHOLD_RANGE = (0, 240, 10)


# =============================================================================
# API Settings
# =============================================================================

#: Number of search results to retrieve per query
SEARCH_RESULTS_COUNT = 3

#: Batch size for processing (limited by Google Custom Search API daily quota)
BATCH_SIZE = 70


# =============================================================================
# Web Scraping Settings
# =============================================================================

#: Timeout for page load operations (milliseconds)
PAGE_LOAD_TIMEOUT_MS = 10000

#: Timeout for waiting for images to appear (milliseconds)
IMAGE_WAIT_TIMEOUT_MS = 10000

#: Additional wait time after page load for dynamic content (milliseconds)
DYNAMIC_CONTENT_WAIT_MS = 2000

#: Timeout for image download requests (seconds)
IMAGE_DOWNLOAD_TIMEOUT_S = 10

#: Number of paintings to process concurrently in each async group
ASYNC_GROUP_SIZE = 3

#: Whether to run browser in headless mode
BROWSER_HEADLESS = True


# =============================================================================
# Known Museums
# =============================================================================

#: Mapping of URL domain keywords to full museum names
#: Used to identify the source museum from search result URLs
KNOWN_MUSEUMS: dict[str, str] = {
    'mfa': 'Museum of Fine Arts Boston',
    'artic': 'The Art Institute of Chicago',
    'belvedere': 'Austrian Gallery Belvedere',
    'metmuseum': 'The Metropolitan Museum of Art',
    'nga': 'The National Gallery of Art',
    'sfmoma': 'San Francisco Museum of Modern Art (SFMOMA)',
    'guggenheim': 'The Guggenheim Museum',
    'philamuseum': 'The Philadelphia Museum of Art',
    'albertina': 'Albertina Museum Wien',
    'harvardartmuseums': 'The Harvard Art Museums',
    'leopoldmuseum': 'The Leopold Museum',
    'museodelnovecento': 'The Museo del Novecento',
    'moma': 'Museum of Modern Art (MoMA)',
    'galleriaborghese': 'The Galleria Borghese',
    'doriapamphilj': 'Galleria Doria Pamphilji',
    'famsf': 'The Fine Arts Museums of San Francisco',
    'noma': 'The New Orleans Museum of Art (NOMA)',
    'sjmusart': 'The San José Museum of Art',
    'bampfa': 'Berkeley Art Museum and Pacific Film Archive (BAMPFA)',
    'si': 'Smithsonian Museums',
}


# =============================================================================
# Captcha Detection
# =============================================================================

#: Keywords that indicate a captcha or bot detection page
CAPTCHA_KEYWORDS = [
    "captcha",
    "not a robot",
    "cloudflare",
    "verify you are human",
    "checking your browser",
    "sicherheitsüberprüfung",
    "bestätigen sie, dass sie ein mensch sind",
    "verifica di sicurezza",
    "verifica che tu sia un essere umano",
    "verifica browser",
    "non sono ein robot",
]


# =============================================================================
# Cookie Consent
# =============================================================================

#: Keywords to identify cookie consent buttons (multi-language)
COOKIE_CONSENT_KEYWORDS = [
    "accept",
    "allow",
    "akzeptieren",
    "consent",
    "zustimmen",
    "agree",
    "einwilligen",
    "accetta",
    "consenti",
    "acconsenti",
    "ho capito",
]


# =============================================================================
# File Paths
# =============================================================================

#: Directory for intermediate pipeline results
INTERMEDIATE_RESULTS_DIR = "intermediate_results"

#: Directory for downloaded artwork images
EXTRACTED_IMAGES_DIR = "extracted_images"

#: Directory for input plaque images
MUSEUM_PLAQUES_DIR = "museum_plaques"
