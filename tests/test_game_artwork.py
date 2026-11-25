import requests

from services.game_artwork_service import _cache, get_game_artwork


def test_artwork_resolves_hashed_source_url_and_caches_lookup():
    _cache.clear()
    class Session:
        calls = 0
        def get(self, url, params, **kwargs):
            self.calls += 1
            return type("Response", (), {"raise_for_status": lambda self: None, "json": lambda self: {
                params["appids"]: {"success": True, "data": {"header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/123/hash/header.jpg"}}
            }})()
    session = Session()
    assert "/hash/header.jpg" in get_game_artwork(123, session)
    get_game_artwork(123, session)
    assert session.calls == 1
    _cache.clear()


def test_artwork_rejects_non_steam_redirect_and_handles_network_failure():
    _cache.clear()
    class Session:
        def get(self, url, params, **kwargs):
            return type("Response", (), {"raise_for_status": lambda self: None, "json": lambda self: {
                params["appids"]: {"success": True, "data": {"header_image": "https://unrelated.example/image.jpg"}}
            }})()
    assert get_game_artwork(124, Session()) is None
    class Offline:
        def get(self, *args, **kwargs):
            raise requests.Timeout()
    assert get_game_artwork(125, Offline()) is None
    assert get_game_artwork(0, Offline()) is None
    _cache.clear()
