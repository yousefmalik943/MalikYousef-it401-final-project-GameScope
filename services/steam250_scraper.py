import json
import re
import time

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from services.external_errors import ExternalServiceError


class Steam250Scraper:
    """Scrape structured hidden-gem records from Steam 250's public ranking."""

    _cache = {}

    def __init__(
        self,
        source_url,
        timeout=10,
        cache_seconds=900,
        session=None,
        fallback_path=None,
        alternate_urls=None,
    ):
        self.source_url = source_url
        self.timeout = timeout
        self.cache_seconds = cache_seconds
        self.session = session or self._retrying_session()
        self.fallback_path = fallback_path
        self.alternate_urls = alternate_urls or []
        self.used_fallback = False
        self.used_mirror = False

    @staticmethod
    def _retrying_session():
        session = requests.Session()
        retries = Retry(
            total=2,
            connect=2,
            read=1,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))
        return session

    def get_hidden_gems(self, limit=50):
        self.used_fallback = False
        self.used_mirror = False
        cached = self._cache.get(self.source_url)
        if cached and time.time() - cached["saved_at"] < self.cache_seconds:
            self.used_fallback = cached.get("is_fallback", False)
            self.used_mirror = cached.get("is_mirror", False)
            return cached["games"][:limit]

        last_error = ExternalServiceError("Steam 250 could not be reached.")
        for index, url in enumerate([self.source_url, *self.alternate_urls]):
            try:
                games = self._fetch_games(url)
                self.used_mirror = index > 0
                self._cache[self.source_url] = {
                    "saved_at": time.time(),
                    "games": games,
                    "is_mirror": self.used_mirror,
                }
                return games[:limit]
            except ExternalServiceError as exc:
                last_error = exc

        return self._fallback_or_raise(last_error, limit)

    def _fetch_games(self, url):
        try:
            response = self.session.get(
                url,
                headers={
                    "User-Agent": "GameScope-A2/1.0 (student academic project; cached requests)"
                },
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise ExternalServiceError("Steam 250 took too long to respond.") from exc
        except requests.RequestException as exc:
            raise ExternalServiceError("Steam 250 could not be reached.") from exc

        if response.status_code == 429:
            raise ExternalServiceError(
                "Steam 250's request limit was reached.", status_code=429
            )
        if not response.ok:
            raise ExternalServiceError(
                f"Steam 250 returned an unsuccessful response ({response.status_code}).",
                status_code=response.status_code,
            )
        return self.parse_games(response.text)

    def _fallback_or_raise(self, error, limit, cause=None):
        if self.fallback_path:
            try:
                with open(self.fallback_path, encoding="utf-8") as fallback_file:
                    games = json.load(fallback_file)
                if isinstance(games, list) and games:
                    self.used_fallback = True
                    self._cache[self.source_url] = {
                        "saved_at": time.time(),
                        "games": games,
                        "is_fallback": True,
                    }
                    return games[:limit]
            except (OSError, ValueError, TypeError):
                pass
        if cause:
            raise error from cause
        raise error

    @staticmethod
    def parse_games(html):
        soup = BeautifulSoup(html, "html.parser")
        games = []

        for row in soup.select("section.applist > div[id]"):
            title_link = row.select_one(".title a[title]")
            store_link = row.select_one(".actions a.store")
            if not title_link or not store_link:
                continue

            app_match = re.search(r"/app/(\d+)", store_link.get("href", ""))
            if not app_match:
                continue

            def text_of(selector, default="Unknown"):
                element = row.select_one(selector)
                return element.get_text(" ", strip=True) if element else default

            rank_numbers = re.findall(r"\d+", text_of(".rank", ""))
            approval_match = re.search(r"(\d+)%", text_of(".reviews .rating", ""))
            image = row.select_one(".img img")
            image_url = image.get("data-src") or image.get("src") if image else None
            if image_url and image_url.startswith("//"):
                image_url = f"https:{image_url}"

            votes_text = text_of(".reviews .votes", "0").replace(",", "")
            try:
                review_count = int(votes_text)
            except ValueError:
                review_count = 0

            games.append(
                {
                    "rank": int(rank_numbers[-1]) if rank_numbers else len(games) + 1,
                    "title": title_link.get("title") or title_link.get_text(" ", strip=True),
                    "steam_app_id": app_match.group(1),
                    "tag": text_of(".title a.tag"),
                    "year": text_of(".title .date a"),
                    "score": text_of(".score span"),
                    "review_count": review_count,
                    "approval": int(approval_match.group(1)) if approval_match else None,
                    "price": text_of(".price"),
                    "image": image_url,
                    "steam_url": store_link.get("href", "").strip(),
                }
            )

        if not games:
            raise ExternalServiceError(
                "Steam 250's page format changed or contained no readable game records."
            )
        return games
