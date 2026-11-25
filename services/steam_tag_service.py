"""Read popular user-defined tags from the exact Steam App ID's store page."""
import re

import requests
from bs4 import BeautifulSoup

from services.external_errors import ExternalServiceError


class SteamTagService:
    def __init__(self, timeout=6, session=None):
        self.timeout = timeout
        self.session = session or requests

    @staticmethod
    def parse_tags(html, app_id):
        soup = BeautifulSoup(html, "html.parser")
        canonical = soup.select_one('meta[property="og:url"]')
        if canonical:
            match = re.search(r"/app/(\d+)", canonical.get("content", ""))
            if match and match.group(1) != str(app_id):
                raise ExternalServiceError("Steam returned tags for a different game.")
        return list(dict.fromkeys(
            element.get_text(" ", strip=True)[:120]
            for element in soup.select(".glance_tags a.app_tag")
            if element.get_text(" ", strip=True) not in {"", "+"}
        ))[:30]

    def get_tags(self, app_id):
        if not str(app_id).isdigit():
            raise ExternalServiceError("Invalid Steam App ID for category lookup.")
        try:
            response = self.session.get(
                f"https://store.steampowered.com/app/{app_id}/", params={"l": "english"},
                headers={"User-Agent": "GameScope-A6/1.0 (student project; cached category lookups)"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self.parse_tags(response.text, app_id)
        except requests.RequestException as exc:
            raise ExternalServiceError("Steam category tags are temporarily unavailable.") from exc
