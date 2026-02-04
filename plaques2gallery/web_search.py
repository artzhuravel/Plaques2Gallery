"""
Web search module using Google Custom Search API.

This module provides functionality to search for artwork images using
Google's Custom Search API. Due to API quota limitations (100 queries/day
on free tier), searches are typically performed in batches.

Functions:
    google_search_top3: Search for a painting and return top 3 URLs
"""

import logging

from googleapiclient.discovery import build  # type: ignore[import-untyped]

from plaques2gallery.config import SEARCH_RESULTS_COUNT

logger = logging.getLogger(__name__)


def google_search_top3(
    query: str,
    api_key: str,
    cse_id: str
) -> tuple[str, ...] | str:
    """
    Performs a Google Custom Search and returns the top result URLs.

    Parameters
    ----------
    query : str
        The search query string (typically "Painting Title by Artist").
    api_key : str
        API key for accessing the Google Custom Search service.
    cse_id : str
        Custom Search Engine ID (CX) associated with the search configuration.

    Returns
    -------
    tuple[str, ...] | str
        A tuple of up to 3 URLs returned by the search. If the query fails
        or no items are found, returns the string "Unsuccessful search".
    """
    logger.debug(f"Searching for: {query}")
    service = build("customsearch", "v1", developerKey=api_key)

    try:
        res = service.cse().list(
            q=str(query),
            cx=cse_id,
            num=SEARCH_RESULTS_COUNT
        ).execute()
        items = res.get("items", [])

        if items:
            urls = tuple(item["link"] for item in items)
            logger.info(f"Found {len(urls)} results for: {query[:30]}...")
            return urls
        else:
            logger.warning(f"No search results for: {query}")
            return "Unsuccessful search"
    except Exception as e:
        logger.error(f"Search failed for '{query}': {e}")
        return "Unsuccessful search"
