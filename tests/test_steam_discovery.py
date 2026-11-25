import json
from datetime import datetime, timezone

import pytest
import requests

from app import create_app
from models import SteamCatalogIndex, SteamDiscoveryGame, db
from services.external_errors import ExternalServiceError
from services.steam_discovery_service import SteamDiscoveryService, steam_candidates


class Response:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self.payload


class SteamSession:
    def __init__(self, count=400, positive=380, game_type="game"):
        self.count = count
        self.positive = positive
        self.game_type = game_type
        self.calls = []
    def get(self, url, params, **kwargs):
        self.calls.append((url, params))
        if "store.steampowered.com/app/" in url:
            response = Response({})
            response.text = '<meta property="og:url" content="https://store.steampowered.com/app/123/"><div class="glance_tags"><a class="app_tag">Strategy</a></div>'
            return response
        if "appdetails" in url:
            return Response({params["appids"]: {"success": True, "data": {
                "type": self.game_type, "name": "Steam Gem", "is_free": False,
                "platforms": {"windows": True}, "release_date": {"coming_soon": False},
                "genres": [{"description": "Strategy"}], "price_overview": {"final_formatted": "$4.99", "currency": "USD"},
            }}})
        options = json.loads(params["input_json"])
        assert options["languages"] == ["all"] and options["purchase_type"] == 1 and options["review_type"] == 0
        return Response({"response": {"query_summary": {"total_reviews": self.count, "total_positive": self.positive}}})


def test_direct_steam_review_qualification_and_metadata():
    service = SteamDiscoveryService("server-key", session=SteamSession())
    game = service.inspect_game({"app_id": "123", "title": "Name"})
    assert game["steam_app_id"] == "123" and game["tag"] == "Strategy"
    assert game["approval"] == 95 and game["price"] == "$4.99"
    assert game["evidence_source"]["source_mode"] == "steam"
    assert game["rank"] is None


@pytest.mark.parametrize("count,positive", [(19, 19), (5001, 5001), (100, 84), (20, 16)])
def test_non_qualifying_games_are_excluded(count, positive):
    service = SteamDiscoveryService("key", session=SteamSession(count, positive))
    assert service.inspect_game({"app_id": "123", "title": "Name"}) is None


def test_dlc_excluded_before_review_request():
    session = SteamSession(game_type="dlc")
    assert SteamDiscoveryService("key", session=session).inspect_game({"app_id": "123", "title": "Name"}) is None
    assert len(session.calls) == 1


def test_catalog_pagination_uses_cursor_and_excludes_non_games():
    class Session:
        def get(self, url, params, **kwargs):
            options = json.loads(params["input_json"])
            assert options["include_dlc"] is False and options["include_software"] is False
            if options["last_appid"] == 0:
                return Response({"response": {"apps": [{"appid": 10, "name": "First"}], "have_more_results": True, "last_appid": 10}})
            assert options["last_appid"] == 10
            return Response({"response": {"apps": [{"appid": 20, "name": "Second"}], "have_more_results": False}})
    apps, complete = SteamDiscoveryService("key", session=Session()).get_index()
    assert complete and [g["app_id"] for g in apps] == ["10", "20"]


def test_discovery_cache_avoids_rechecking_and_excludes_owned(monkeypatch):
    app = create_app("default", {"SQLALCHEMY_DATABASE_URI": "sqlite://", "TESTING": True})
    with app.app_context():
        db.create_all()
        db.session.add(SteamCatalogIndex(id=1, fetched_at=datetime.now(timezone.utc), complete=True,
            apps_json=json.dumps([{"app_id": "1", "title": "One"}, {"app_id": "2", "title": "Two"}])))
        db.session.commit()
        checked = []
        def inspect(self, game):
            checked.append(game["app_id"])
            return {"steam_app_id": game["app_id"], "title": game["title"]}
        monkeypatch.setattr(SteamDiscoveryService, "inspect_game", inspect)
        candidates, details = steam_candidates({"2"})
        assert len(candidates) == 1 and checked == ["1"]
        assert details["checked"] == 1
        steam_candidates({"2"})
        assert checked == ["1"]
        assert SteamDiscoveryGame.query.count() == 1
        db.session.remove()
        db.drop_all()


def test_transport_failure_does_not_cache_ineligible_game(monkeypatch):
    app = create_app("default", {"SQLALCHEMY_DATABASE_URI": "sqlite://", "TESTING": True})
    with app.app_context():
        db.create_all()
        db.session.add(SteamCatalogIndex(id=1, fetched_at=datetime.now(timezone.utc), complete=True,
            apps_json=json.dumps([{"app_id": "1", "title": "One"}])))
        db.session.commit()
        def fail(self, app):
            raise ExternalServiceError("Unavailable")
        monkeypatch.setattr(SteamDiscoveryService, "inspect_game", fail)
        candidates, details = steam_candidates(set())
        assert candidates == [] and any("unavailable" in note for note in details["notes"])
        assert SteamDiscoveryGame.query.count() == 0
        db.session.remove()
        db.drop_all()


def test_hidden_gems_reviews_use_migrated_api_and_response_envelope():
    from services.steam_review_service import SteamReviewService
    class Session:
        def get(self, url, params, **kwargs):
            assert url == "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"
            options = json.loads(params["input_json"])
            assert options["appid"] == 123 and options["languages"] == ["english"]
            assert options["filter"] == 0 and options["review_type"] == 0 and options["purchase_type"] == 1
            response = Response({"response": {"query_summary": {"total_positive": 95, "total_negative": 5, "total_reviews": 100,
                "review_score_desc": "Very Positive"}, "reviews": [{"review": "A thoughtful gem.", "voted_up": True,
                    "author": {"playtime_at_review": 120}}]}})
            response.status_code = 200
            response.ok = True
            return response
    result = SteamReviewService("https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1", session=Session()).get_reviews("123")
    assert result["total_reviews"] == 100 and result["reviews"][0]["playtime_hours"] == 2.0


def test_popular_steam_tags_are_sourced_and_identity_checked():
    from services.steam_tag_service import SteamTagService
    html = '''<meta property="og:url" content="https://store.steampowered.com/app/123/">
    <div class="glance_tags"><a class="app_tag">Action Roguelike</a><a class="app_tag">Roguelite</a>
    <a class="app_tag">Roguelite</a><a class="app_tag">+</a></div>'''
    assert SteamTagService.parse_tags(html, "123") == ["Action Roguelike", "Roguelite"]
    with pytest.raises(ExternalServiceError, match="different game"):
        SteamTagService.parse_tags(html, "456")
    assert SteamTagService.parse_tags("<title>Welcome to Steam</title>", "123") == []
