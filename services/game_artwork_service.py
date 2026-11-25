"""Resolve current Steam artwork paths without changing saved recommendations."""
from collections import OrderedDict
import time
from urllib.parse import urlparse

import requests

_cache = OrderedDict()


def get_game_artwork(app_id, session=None):
    app_id = int(app_id)
    if not 0 < app_id < 2**32:
        return None
    now = time.monotonic()
    cached = _cache.get(app_id)
    if cached and cached[0] > now:
        return cached[1]
    image = None
    try:
        response = (session or requests).get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": str(app_id), "l": "english"}, timeout=6,
        )
        response.raise_for_status()
        result = response.json().get(str(app_id), {})
        candidate = (result.get("data") or {}).get("header_image") if result.get("success") else None
        if isinstance(candidate, str):
            parsed = urlparse(candidate)
            host = parsed.hostname or ""
            if parsed.scheme == "https" and (host.endswith(".steamstatic.com") or host == "steamcdn-a.akamaihd.net") and not parsed.username:
                image = candidate
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        pass
    _cache[app_id] = (now + (86400 if image else 300), image)
    _cache.move_to_end(app_id)
    while len(_cache) > 512:
        _cache.popitem(last=False)
    return image
