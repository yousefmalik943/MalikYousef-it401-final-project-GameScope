import requests

from services.external_errors import ExternalServiceError


class SteamReviewService:
    """Retrieve public written reviews through Steam's documented endpoint."""

    def __init__(self, base_url, timeout=10, session=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def get_reviews(self, app_id, limit=3):
        app_id = str(app_id or "").strip()
        if not app_id.isdigit():
            raise ExternalServiceError("The selected game has an invalid Steam App ID.")

        try:
            response = self.session.get(
                f"{self.base_url}/{app_id}",
                params={
                    "json": 1,
                    "filter": "all",
                    "language": "english",
                    "day_range": 365,
                    "review_type": "all",
                    "purchase_type": "all",
                    "num_per_page": max(1, min(int(limit), 20)),
                    "filter_offtopic_activity": 1,
                },
                headers={"User-Agent": "GameScope-A2/1.0 (student academic project)"},
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise ExternalServiceError(
                "Steam reviews took too long to respond. Please try again."
            ) from exc
        except requests.RequestException as exc:
            raise ExternalServiceError(
                "Steam reviews could not be reached. Check your connection and try again."
            ) from exc

        if response.status_code == 429:
            raise ExternalServiceError(
                "Steam's request limit was reached. Please wait and try again.",
                status_code=429,
            )
        if not response.ok:
            raise ExternalServiceError(
                f"Steam returned an unsuccessful response ({response.status_code}).",
                status_code=response.status_code,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalServiceError("Steam returned data that could not be read.") from exc

        if payload.get("success") != 1:
            raise ExternalServiceError("Steam did not return reviews for this game.")

        summary = payload.get("query_summary") or {}
        reviews = []
        for item in payload.get("reviews") or []:
            text = " ".join((item.get("review") or "").split())
            if not text:
                continue
            author = item.get("author") or {}
            reviews.append(
                {
                    "text": text,
                    "recommended": bool(item.get("voted_up")),
                    "helpful_votes": item.get("votes_up", 0),
                    "comment_count": item.get("comment_count", 0),
                    "playtime_hours": round(author.get("playtime_at_review", 0) / 60, 1),
                    "developer_response": item.get("developer_response"),
                }
            )

        return {
            "score_description": summary.get("review_score_desc") or "No rating",
            "total_positive": summary.get("total_positive", 0),
            "total_negative": summary.get("total_negative", 0),
            "total_reviews": summary.get("total_reviews", 0),
            "reviews": reviews,
            "source_url": f"https://store.steampowered.com/app/{app_id}/#app_reviews_hash",
        }
