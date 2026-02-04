"""
Web scraping module for extracting artwork images from museum and reference websites.

This module provides async functionality to:
- Navigate to artwork pages using Playwright
- Handle cookie consent dialogs and captcha detection
- Extract the largest/best quality image from pages
- Download and convert images to JPEG format

The module implements a priority system for URL sources:
1. Wikipedia pages (most reliable for artwork images)
2. Known museum websites (trusted sources)
3. Other URLs as fallback

Warning
-------
This module automatically accepts cookie consent dialogs by clicking buttons
that match keywords like "accept", "allow", "consent", etc. This is done to
bypass popups that would block image extraction. Important notes:

- Cookies are accepted in an **isolated, temporary browser session**
- The browser session is closed after each page, so cookies are not persisted
- No cookies are stored on your system or affect your normal browsing
- If you need to avoid accepting certain terms, review COOKIE_CONSENT_KEYWORDS
  in config.py and remove keywords as needed

Functions:
    accept_cookies: Dismiss cookie consent dialogs
    download_image_from_url: Download image bytes from URL
    extract_best_image_from_url: Find highest resolution image from srcset
    convert_to_jpeg: Convert image formats to JPEG
    get_img: Find and download largest image on page
    extract_main_image_from_page: Full page processing pipeline
    process_a_painting: Process all URLs for a single painting
"""

import logging
import re
from urllib.parse import urljoin
import aiohttp
import mimetypes
import heapq
from io import BytesIO
from PIL import Image  # type: ignore[import-untyped]
from playwright.async_api import (  # type: ignore[import-untyped]
    Browser,
    ElementHandle,
    Page,
    TimeoutError as PlaywrightTimeout,
)

from plaques2gallery.config import (
    KNOWN_MUSEUMS,
    CAPTCHA_KEYWORDS,
    COOKIE_CONSENT_KEYWORDS,
    PAGE_LOAD_TIMEOUT_MS,
    IMAGE_WAIT_TIMEOUT_MS,
    DYNAMIC_CONTENT_WAIT_MS,
    IMAGE_DOWNLOAD_TIMEOUT_S,
    EXTRACTED_IMAGES_DIR,
)

logger = logging.getLogger(__name__)

# Type aliases for clarity
ImageData = tuple[bytes, str, str]
ImageResult = tuple[str, str]
BatchResult = tuple[str, str | list[str], str, str, str]


async def accept_cookies(page: Page) -> None:
    """
    Attempts to accept cookies on a webpage by clicking buttons with text related to consent.

    Searches for visible, non-disabled buttons matching consent keywords in multiple languages.
    Clicks the first matching button found.

    Warning
    -------
    This function automatically clicks consent buttons without user confirmation.
    It runs in an isolated browser session that is discarded after use, so no
    cookies persist. To customize which buttons are clicked, modify
    COOKIE_CONSENT_KEYWORDS in config.py.
    """
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(k) for k in COOKIE_CONSENT_KEYWORDS) + r")\b"
    )

    all_buttons = await page.query_selector_all(
        "button, input[type='button'], input[type='submit'], [role='button'], a[role='button']"
    )
    filtered_buttons: list[ElementHandle] = []

    for b in all_buttons:
        if await b.is_visible():
            disabled = await b.get_attribute("disabled")
            if not disabled:
                filtered_buttons.append(b)

    for button in filtered_buttons:
        try:
            html = await button.evaluate("el => el.outerHTML")
            if pattern.search(html.lower()):
                await button.click()
                logger.debug("Accepted cookie consent")
                return
        except Exception as e:
            logger.debug(f"Failed to click cookie button: {e}")
            continue


async def download_image_from_url(
    url: str,
    base_url: str
) -> tuple[bytes | None, str | None, str | None]:
    """
    Downloads an image from a given relative or absolute URL, validating content type as an image.

    Parameters
    ----------
    url : str
        The image URL (can be relative or absolute).
    base_url : str
        Base URL for resolving relative paths.

    Returns
    -------
    tuple[bytes | None, str | None, str | None]
        (image_bytes, resolved_image_url, extension) or (None, None, None) on failure.
    """
    absolute_url = urljoin(base_url, url)
    headers = {
        "User-Agent": "Mozilla/5.0 ...",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": base_url,
    }

    try:
        timeout = aiohttp.ClientTimeout(total=IMAGE_DOWNLOAD_TIMEOUT_S)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                absolute_url,
                headers=headers,
            ) as response:
                if response.status == 200 and response.headers.get("Content-Type", "").startswith("image/"):
                    content_type = response.headers.get("Content-Type", "").split(";")[0]
                    extension = mimetypes.guess_extension(content_type) or ".jpg"
                    content = await response.read()
                    logger.debug(f"Downloaded image from {absolute_url}")
                    return content, absolute_url, extension
    except aiohttp.ClientError as e:
        logger.debug(f"Failed to download image from {absolute_url}: {e}")
        return None, None, None
    except TimeoutError:
        logger.debug(f"Timeout downloading image from {absolute_url}")
        return None, None, None

    return None, None, None


async def extract_best_image_from_url(
    img_block: ElementHandle,
    base_url: str
) -> tuple[bytes | None, str | None, str | None]:
    """
    Attempts to extract and download the highest-resolution image from a given <img> block.

    Uses `srcset`, `src`, or other attributes to find the best image source.

    Parameters
    ----------
    img_block : ElementHandle
        Playwright element handle for an <img> tag.
    base_url : str
        Base URL for resolving relative paths.

    Returns
    -------
    tuple[bytes | None, str | None, str | None]
        (image_bytes, resolved_image_url, extension) or (None, None, None) on failure.
    """
    srcset = await img_block.get_attribute("srcset")
    if srcset:
        srcset_tokens = [token.rstrip(",") for token in srcset.strip().split()]
        srcset_pairs: list[tuple[str, int]] = []
        i = 0
        while i < len(srcset_tokens) - 1:
            url = srcset_tokens[i]
            descriptor = srcset_tokens[i + 1]
            if descriptor[-1] in ("w", "x") and any(c.isdigit() for c in descriptor[:-1]):
                value = int(''.join(filter(str.isdigit, descriptor)))
                srcset_pairs.append((url, value))
                i += 2
            else:
                i += 1

        # Fallback if descriptor parsing failed
        if len(srcset_pairs) * 2 < len(srcset_tokens):
            for i in range(len(srcset_tokens) - 1, -1, -1):
                url = srcset_tokens[i]
                if "/" not in url:
                    continue
                img_bytes, img_url, img_extension = await download_image_from_url(url, base_url)
                if img_bytes:
                    return img_bytes, img_url, img_extension
        else:
            max_heap: list[tuple[int, str]] = [(-value, url) for url, value in srcset_pairs]
            heapq.heapify(max_heap)
            while max_heap:
                _, url = heapq.heappop(max_heap)
                img_bytes, img_url, img_extension = await download_image_from_url(url, base_url)
                if img_bytes:
                    return img_bytes, img_url, img_extension

    # Try src attribute
    src = await img_block.get_attribute("src")
    if src:
        img_bytes, img_url, img_extension = await download_image_from_url(src, base_url)
        if img_bytes:
            return img_bytes, img_url, img_extension

    # Fallback: try other attributes
    attrs: dict[str, str] = await img_block.evaluate(
        "img => Object.fromEntries(Array.from(img.attributes).map(a => [a.name, a.value]))"
    )
    for key, val in attrs.items():
        if key in ("src", "srcset"):
            continue
        if isinstance(val, str):
            img_bytes, img_url, img_extension = await download_image_from_url(val, base_url)
            if img_bytes:
                return img_bytes, img_url, img_extension

    return None, None, None


def convert_to_jpeg(img_bytes: bytes, img_extension: str) -> tuple[bytes, str]:
    """
    Converts an image to JPEG format if possible, preserving original data on failure.

    Parameters
    ----------
    img_bytes : bytes
        Raw image data.
    img_extension : str
        Original file extension.

    Returns
    -------
    tuple[bytes, str]
        (jpeg_image_bytes, '.jpg') or (original_bytes, original_extension) on failure.
    """
    try:
        img = Image.open(BytesIO(img_bytes))
        img.verify()

        img = Image.open(BytesIO(img_bytes))
        rgb_img = img.convert("RGB")

        buffer = BytesIO()
        rgb_img.save(buffer, format="JPEG")
        logger.debug("Converted image to JPEG format")
        return buffer.getvalue(), ".jpg"

    except (IOError, OSError, ValueError) as e:
        logger.debug(f"Failed to convert image to JPEG: {e}")
        return img_bytes, img_extension


async def get_img(
    page: Page,
    base_url: str,
    img_name: str
) -> tuple[str | None, str | None]:
    """
    Selects the largest visible <img> element on the page and downloads it.

    Parameters
    ----------
    page : Page
        Playwright page object.
    base_url : str
        Base URL for resolving relative image paths.
    img_name : str
        Name to use when saving the image file.

    Returns
    -------
    tuple[str | None, str | None]
        (image_file_path, resolved_image_url) or (None, None) if unsuccessful.
    """
    img_blocks = await page.query_selector_all("img")
    heap: list[tuple[float, int, ElementHandle]] = []

    for i, img_block in enumerate(img_blocks):
        box = await img_block.bounding_box()
        if not box:
            continue
        width = box["width"]
        height = box["height"]
        area = width * height
        if area == 0:
            continue
        heapq.heappush(heap, (-area, i, img_block))  # max heap

    if not heap:
        logger.warning(f"No valid images found on page for {img_name}")
        return None, None

    img_to_download = heap[0][2]
    img_bytes, img_url, img_extension = await extract_best_image_from_url(img_to_download, base_url)

    if img_bytes and img_url and img_extension:
        img_bytes, img_extension = convert_to_jpeg(img_bytes, img_extension)
        img_path = f"{EXTRACTED_IMAGES_DIR}/{img_name}{img_extension}"
        with open(img_path, "wb") as f:
            f.write(img_bytes)
        logger.info(f"Saved image for {img_name} to {img_path}")
        return img_path, img_url
    else:
        return None, None


def _is_captcha_page(content: str) -> bool:
    """Check if page content indicates a captcha or bot detection."""
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in CAPTCHA_KEYWORDS)


def _detect_museum_from_urls(urls: list[str]) -> str:
    """
    Detect museum location from URL domains.

    Parameters
    ----------
    urls : list[str]
        List of URLs to check.

    Returns
    -------
    str
        Museum name if found, otherwise "Unknown location".
    """
    for url in urls:
        for museum_domain, museum_name in KNOWN_MUSEUMS.items():
            if museum_domain in url:
                return museum_name
    return "Unknown location"


async def _try_wikipedia_urls(
    painting_name: str,
    urls: list[str],
    browser: Browser
) -> tuple[str | None, str | None, set[str]]:
    """
    Try to extract image from Wikipedia URLs first.

    Returns
    -------
    tuple[str | None, str | None, set[str]]
        (image_path, source_url, invalid_urls) - invalid_urls tracks failed attempts.
    """
    invalid_urls: set[str] = set()
    for url in urls:
        if "wikipedia" in url:
            img_path, img_url = await extract_main_image_from_page(painting_name, url, browser)
            if img_path:
                return img_path, img_url, invalid_urls
            invalid_urls.add(url)
    return None, None, invalid_urls


async def _try_museum_urls(
    painting_name: str,
    urls: list[str],
    browser: Browser,
    invalid_urls: set[str]
) -> tuple[str | None, str | None, str]:
    """
    Try to extract image from known museum URLs.

    Returns
    -------
    tuple[str | None, str | None, str]
        (image_path, source_url, museum_location).
    """
    for url in urls:
        if url in invalid_urls:
            continue
        for museum_domain, museum_name in KNOWN_MUSEUMS.items():
            if museum_domain in url:
                img_path, img_url = await extract_main_image_from_page(painting_name, url, browser)
                if img_path:
                    return img_path, img_url, museum_name
                invalid_urls.add(url)
                break
    return None, None, "Unknown location"


async def _try_remaining_urls(
    painting_name: str,
    urls: list[str],
    browser: Browser,
    invalid_urls: set[str]
) -> tuple[str | None, str | None]:
    """Try to extract image from any remaining URLs not yet attempted."""
    for url in urls:
        if url in invalid_urls:
            continue
        img_path, img_url = await extract_main_image_from_page(painting_name, url, browser)
        if img_path:
            return img_path, img_url
    return None, None


async def extract_main_image_from_page(
    painting_name: str,
    url: str,
    browser: Browser
) -> tuple[str | None, str | None]:
    """
    Opens a given URL, handles captchas and cookies, and tries to extract the main image from the page.

    Parameters
    ----------
    painting_name : str
        Name of the painting (used for logging and file naming).
    url : str
        URL of the page to scrape.
    browser : Browser
        Playwright browser instance.

    Returns
    -------
    tuple[str | None, str | None]
        (image_file_path, resolved_image_url) or (None, None) if unsuccessful.
    """
    page: Page | None = None
    try:
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)

        # Handle potential captchas
        content = await page.inner_text("body")
        if _is_captcha_page(content):
            logger.info(f"Captcha detected for {painting_name} at {url}")
            await page.close()
            return None, None

        await page.wait_for_selector("img", timeout=IMAGE_WAIT_TIMEOUT_MS, state="attached")
        await page.wait_for_timeout(DYNAMIC_CONTENT_WAIT_MS)
        await accept_cookies(page)
        img_path, img_url = await get_img(page, base_url=page.url, img_name=painting_name)
        await page.close()
        return img_path, img_url
    except PlaywrightTimeout as e:
        logger.warning(f"Timeout loading page for {painting_name} at {url}: {e}")
    except Exception as e:
        logger.error(f"Error extracting image for {painting_name} from {url}: {e}")
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass
    return None, None


async def process_a_painting(
    painting_name: str,
    urls: list[str] | str,
    browser: Browser,
    cur_batch_names_to_imgs: dict[str, str],
    cur_batch_results: dict[str, BatchResult]
) -> None:
    """
    Attempts to download the best image corresponding to a painting by visiting its associated URLs.

    Updates cur_batch_results with the download path, source URL, and inferred museum location.
    Uses a priority system: Wikipedia first, then known museums, then other URLs.

    Parameters
    ----------
    painting_name : str
        Name of the painting.
    urls : list[str] | str
        List of candidate page URLs containing the image, or error string.
    browser : Browser
        Playwright browser instance.
    cur_batch_names_to_imgs : dict[str, str]
        Mapping of painting names to text content from plaques.
    cur_batch_results : dict[str, BatchResult]
        Mutable dictionary to store output (image path, url, location, etc.) for this batch.
    """
    # Handle case where urls is an error string or empty
    if not urls or isinstance(urls, str):
        logger.warning(f"No valid URLs for {painting_name}")
        cur_batch_results[painting_name] = (
            cur_batch_names_to_imgs[painting_name],
            [],
            "No image was downloaded (no urls were found).",
            "Unknown location",
            "No url to download the image was located."
        )
        return

    # Detect museum location from URLs
    painting_location = _detect_museum_from_urls(urls)

    # 1. Try Wikipedia URLs first (most reliable for artwork images)
    img_path, img_url, invalid_urls = await _try_wikipedia_urls(painting_name, urls, browser)
    if img_path:
        logger.info(f"Found image for {painting_name} from Wikipedia")
        cur_batch_results[painting_name] = (
            cur_batch_names_to_imgs[painting_name], img_path, urls[0], painting_location, img_url or ""
        )
        return

    # 2. Try known museum URLs
    img_path, img_url, museum_location = await _try_museum_urls(
        painting_name, urls, browser, invalid_urls
    )
    if img_path:
        logger.info(f"Found image for {painting_name} from museum website")
        cur_batch_results[painting_name] = (
            cur_batch_names_to_imgs[painting_name], img_path, urls[0], museum_location, img_url or ""
        )
        return

    # 3. Try remaining URLs
    img_path, img_url = await _try_remaining_urls(painting_name, urls, browser, invalid_urls)
    if img_path:
        logger.info(f"Found image for {painting_name} from other source")
        cur_batch_results[painting_name] = (
            cur_batch_names_to_imgs[painting_name], img_path, urls[0], painting_location, img_url or ""
        )
        return

    # 4. No valid image found
    logger.warning(f"Could not find valid image for {painting_name}")
    cur_batch_results[painting_name] = (
        cur_batch_names_to_imgs[painting_name],
        [],
        "No image was downloaded even though some urls were found.",
        painting_location,
        ""
    )
