import requests

from services.external_errors import ExternalServiceError, MissingApiKeyError


class RawgService:
    """Retrieve and normalize PC game metadata from the RAWG API."""

    PC_PLATFORM_ID = 4

    def __init__(self, base_url, api_key, timeout=10, session=None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = session or requests.Session()

    def search_game(self, query):
        query = (query or "").strip()
        if not query:
            raise ExternalServiceError("Enter a game title before searching RAWG.")
        if not self.api_key:
            raise MissingApiKeyError(
                "RAWG is not configured. Add RAWG_API_KEY to your local .env file."
            )

        try:
            response = self.session.get(
                f"{self.base_url}/games",
                params={
                    "key": self.api_key,
                    "search": query,
                    "search_precise": "true",
                    "platforms": self.PC_PLATFORM_ID,
                    "page_size": 1,
                },
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise ExternalServiceError(
                "RAWG took too long to respond. Please try again."
            ) from exc
        except requests.RequestException as exc:
            raise ExternalServiceError(
                "RAWG could not be reached. Check your connection and try again."
            ) from exc

        if response.status_code == 401:
            raise ExternalServiceError(
                "RAWG rejected the API key. Check RAWG_API_KEY in your .env file.",
                status_code=401,
            )
        if response.status_code == 429:
            raise ExternalServiceError(
                "RAWG's request limit was reached. Please wait and try again.",
                status_code=429,
            )
        if not response.ok:
            raise ExternalServiceError(
                f"RAWG returned an unsuccessful response ({response.status_code}).",
                status_code=response.status_code,
            )

        try:
            results = response.json().get("results", [])
        except (ValueError, AttributeError) as exc:
            raise ExternalServiceError("RAWG returned data that could not be read.") from exc

        if not results:
            raise ExternalServiceError(f'RAWG found no PC game matching "{query}".')

        game = results[0]
        return {
            "id": game.get("id"),
            "title": game.get("name") or query,
            "released": game.get("released") or "Unknown",
            "rating": game.get("rating"),
            "ratings_count": game.get("ratings_count", 0),
            "metacritic": game.get("metacritic"),
            "playtime": game.get("playtime"),
            "image": game.get("background_image"),
            "genres": [item.get("name") for item in game.get("genres", []) if item.get("name")],
            "platforms": [
                item.get("platform", {}).get("name")
                for item in game.get("platforms", [])
                if item.get("platform", {}).get("name")
            ],
            "source_url": f"https://rawg.io/games/{game.get('slug')}" if game.get("slug") else "https://rawg.io/",
        }
