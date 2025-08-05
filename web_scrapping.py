import re
from urllib.parse import urljoin
import aiohttp
import mimetypes
import heapq
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright

async def accept_cookies(page):
    """
    Attempts to accept cookies on a webpage by clicking buttons with text related to consent.
    """
    keywords = ["accept", "allow", "akzeptieren", "consent", "zustimmen", "agree", "einwilligen", "accetta", "consenti", "acconsenti", "ho capito"]
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in keywords) + r")\b")

    all_buttons = await page.query_selector_all("button, input[type='button'], input[type='submit'], [role='button'], a[role='button']")
    filtered_buttons = []

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
                return
        except:
            continue


async def download_image_from_url(url, base_url):
    """
    Downloads an image from a given relative or absolute URL, validating content type as an image.

    Returns
    -------
    tuple
        (image_bytes, resolved_image_url, extension) or (None, None, None) on failure.
    """
    absolute_url = urljoin(base_url, url)
    headers = {
        "User-Agent": "Mozilla/5.0 ...",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": base_url,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(absolute_url, headers=headers, timeout=10) as response:
                if response.status == 200 and response.headers.get("Content-Type", "").startswith("image/"):
                    content_type = response.headers.get("Content-Type", "").split(";")[0]
                    extension = mimetypes.guess_extension(content_type) or ".jpg"
                    content = await response.read()
                    return content, absolute_url, extension
    except:
        return None, None, None

    return None, None, None


async def extract_best_image_from_url(img_block, base_url):
    """
    Attempts to extract and download the highest-resolution image from a given <img> block using `srcset`, `src`, or other attributes.

    Returns
    -------
    tuple
        (image_bytes, resolved_image_url, extension) or (None, None, None) on failure.
    """
    srcset = await img_block.get_attribute("srcset")
    if srcset:
        srcset_tokens = [token.rstrip(",") for token in srcset.strip().split()]
        srcset_pairs = []
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
                img_bytes, imr_url, img_extension = await download_image_from_url(url, base_url)
                if img_bytes: return img_bytes, imr_url, img_extension
        else:
            max_heap = [(-value, url) for url, value in srcset_pairs]
            heapq.heapify(max_heap)
            while max_heap:
                _, url = heapq.heappop(max_heap)
                img_bytes, imr_url, img_extension = await download_image_from_url(url, base_url)
                if img_bytes: return img_bytes, imr_url, img_extension

    # Try src attribute
    src = await img_block.get_attribute("src")
    if src:
        img_bytes, imr_url, img_extension = await download_image_from_url(src, base_url)
        if img_bytes: return img_bytes, imr_url, img_extension

    # Fallback: try other attributes
    attrs = await img_block.evaluate("img => Object.fromEntries(Array.from(img.attributes).map(a => [a.name, a.value]))")
    for key, val in attrs.items():
        if key in ("src", "srcset"): continue
        if isinstance(val, str):
            img_bytes, imr_url, img_extension = await download_image_from_url(val, base_url)
            if img_bytes: return img_bytes, imr_url, img_extension

    return None, None, None


def convert_to_jpeg(img_bytes, img_extension):
    """
    Converts an image to JPEG format if possible, preserving original data on failure.

    Returns
    -------
    tuple
        (jpeg_image_bytes, '.jpg') or (original_bytes, original_extension) on failure.
    """
    try:
        img = Image.open(BytesIO(img_bytes))
        img.verify()

        img = Image.open(BytesIO(img_bytes))
        rgb_img = img.convert("RGB")

        buffer = BytesIO()
        rgb_img.save(buffer, format="JPEG")
        return buffer.getvalue(), ".jpg"

    except:
        return img_bytes, img_extension


async def get_img(page, base_url, img_name):
    """
    Selects the largest visible <img> element on the page and downloads it.

    Returns
    -------
    tuple
        (image_file_path, resolved_image_url) or (None, None) if unsuccessful.
    """
    img_blocks = await page.query_selector_all("img")
    heap = []

    for i, img_block in enumerate(img_blocks):
        box = await img_block.bounding_box()
        if not box: continue
        width = box["width"]
        height = box["height"]
        area = width * height
        if area == 0: continue
        heapq.heappush(heap, (-area, i, img_block))  # max heap

    img_to_download = heap[0][2]
    img_bytes, img_url, img_extension = await extract_best_image_from_url(img_to_download, base_url)

    if img_bytes:
        img_bytes, img_extension = convert_to_jpeg(img_bytes, img_extension)
        img_path = f"final_results/extracted_images/{img_name}{img_extension}"
        with open(img_path, "wb") as f:
            f.write(img_bytes)
        return img_path, img_url
    else:
        return None, None


async def extract_main_image_from_page(painting_name, url, browser):
    """
    Opens a given URL, handles captchas and cookies, and tries to extract the main image from the page.

    Returns
    -------
    tuple
        (image_file_path, resolved_image_url) or (None, None) if unsuccessful.
    """
    try:
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_load_state("domcontentloaded", timeout=10000)

        # Handle potential captchas
        content = await page.inner_text("body")
        skip_words = [
            "captcha", "not a robot", "cloudflare", "verify you are human",
            "checking your browser", "sicherheitsüberprüfung", 
            "bestätigen sie, dass sie ein mensch sind", "verifica di sicurezza", 
            "verifica che tu sia un essere umano", "verifica browser", 
            "non sono ein robot"
        ]
        if any(keyword in content.lower() for keyword in skip_words):
            await page.close()
            return None, None

        await page.wait_for_selector("img", timeout=10000, state="attached")
        await page.wait_for_timeout(2000)
        await accept_cookies(page)
        img_path, img_url = await get_img(page, base_url=page.url, img_name=painting_name)
        await page.close()
        return img_path, img_url
    except:
        try:
            await page.close()
        except:
            pass
        return None, None


async def process_a_painting(painting_name, urls, browser, cur_batch_names_to_imgs, cur_batch_results):
    """
    Attempts to download the best image corresponding to a painting by visiting its associated URLs.

    Updates cur_batch_results with the download path, source URL, and inferred museum location.

    Parameters
    ----------
    painting_name : str
        Name of the painting.
    urls : list of str
        List of candidate page URLs containing the image.
    browser : playwright.async_api.Browser
        Playwright browser instance.
    cur_batch_names_to_imgs : dict
        Mapping of painting names to text content from plaques.
    cur_batch_results : dict
        Mutable dictionary to store output (image path, url, location, etc.) for this batch.
    """
    painting_location = "Unknown location"
    invalid_urls = set()

    if not urls:
        img_path = "No image was downloaded (no urls were found)."
        img_url = "No url to download the image was located."
        cur_batch_results[painting_name] = (
            cur_batch_names_to_imgs[painting_name], [], img_path, painting_location, img_url
        )
        return

    visited_museums = {
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
        'si': 'Smithsonian Museums'
    }

    # Detect museum based on URL domain
    found = False
    for url in urls:
        if found: break
        for museum_domain in visited_museums:
            if museum_domain in url:
                painting_location = visited_museums[museum_domain]
                found = True
                break

    # 1. Try Wikipedia URLs first
    for url in urls:
        if "wikipedia" in url:
            img_path, img_url = await extract_main_image_from_page(painting_name, url, browser=browser)
            if img_path:
                cur_batch_results[painting_name] = (
                    cur_batch_names_to_imgs[painting_name], img_path, url, painting_location, img_url
                )
                return
            else:
                invalid_urls.add(url)

    # 2. Try trusted museum URLs
    for url in urls:
        for museum_domain in visited_museums:
            if museum_domain in url:
                painting_location = visited_museums[museum_domain]
                img_path, img_url = await extract_main_image_from_page(painting_name, url, browser=browser)
                if img_path:
                    cur_batch_results[painting_name] = (
                        cur_batch_names_to_imgs[painting_name], img_path, url, painting_location, img_url
                    )
                    return
                else:
                    invalid_urls.add(url)

    # 3. Try other remaining URLs
    for url in urls:
        if url in invalid_urls: continue
        img_path, img_url = await extract_main_image_from_page(painting_name, url, browser=browser)
        if img_path:
            cur_batch_results[painting_name] = (
                cur_batch_names_to_imgs[painting_name], img_path, url, painting_location, img_url
            )
            return

    # 4. No valid image found
    img_path = "No image was downloaded even though some urls were found."
    img_url = ""
    cur_batch_results[painting_name] = (
        cur_batch_names_to_imgs[painting_name], [], img_path, painting_location, img_url
    )
    return
