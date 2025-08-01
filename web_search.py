from googleapiclient.discovery import build

def google_search_top3(query, api_key, cse_id):
    """
    Performs a Google Custom Search and returns the top 3 result URLs.

    Parameters
    ----------
    query : str
        The search query string.
    api_key : str
        API key for accessing the Google Custom Search service.
    cse_id : str
        Custom Search Engine ID (CX) associated with the search configuration.

    Returns
    -------
    tuple of str or str
        A tuple of up to 3 URLs (strings) returned by the search. If the query fails
        or no items are found, returns the string "Unsuccessful search".
    """
    service = build("customsearch", "v1", developerKey=api_key)

    try:
        res = service.cse().list(q=str(query), cx=cse_id, num=3).execute()
        items = res.get("items", [])
        return tuple(item["link"] for item in items) if items else "Unsuccessful search"
    except Exception:
        return "Unsuccessful search"