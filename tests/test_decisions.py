import json
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from app import create_app
from models import CatalogSnapshot, DecisionFeedback, DecisionImpression, DecisionRun, PlayerProfile, db
from services.decision_support import recommend
from services.external_errors import ExternalServiceError
from services.rawg_service import RawgService
from services.steam_account_service import OPENID_ENDPOINT, OPENID_NS, SteamAccountService


def chart_game(app_id, tag="Strategy", approval=95):
    return {"steam_app_id": str(app_id), "title": f"Gem {app_id}", "tag": tag,
            "rank": int(app_id), "approval": approval, "review_count": 400, "price": "$9.99"}


def history():
    return [{"app_id": "100", "title": "Played Strategy", "recent_minutes": 120,
             "lifetime_minutes": 800, "genres": ["Strategy"], "genre_source": "https://rawg.io/games/played-strategy"},
            {"app_id": "101", "title": "More Strategy", "recent_minutes": 60,
             "lifetime_minutes": 300, "genres": ["Strategy"]}]


def provenance(mode="live"):
    return {"source_mode": mode, "fetched_at": datetime.now(timezone.utc).isoformat() if mode == "live" else None,
            "chart_url": "https://steam250.com/hidden_gems"}


@pytest.fixture()
def app():
    app = create_app("default", {"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                                "SECRET_KEY": "a-private-test-key-at-least-32-characters", "OPENAI_API_KEY": None,
                                "PUBLIC_BASE_URL": "http://localhost"})
    with app.app_context():
        db.create_all()
        db.session.add(CatalogSnapshot(id=1, source_mode="live", fetched_at=datetime.now(timezone.utc),
            saved_at=datetime.now(timezone.utc), games_json=json.dumps([chart_game(1), chart_game(2), chart_game(3)])) )
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def token(client):
    client.get("/play-next")
    with client.session_transaction() as session:
        return session["decision_csrf"]


def make_plan(client, **overrides):
    data = {"csrf_token": token(client), "style": "Strategy", "path": "familiar", "minutes": "30", **overrides}
    response = client.post("/play-next/generate", data=data)
    assert response.status_code == 302
    return response.headers["Location"].split("run=")[1]


def test_ranking_excludes_owned_and_explains_behavior():
    games = history()
    options = recommend(games, [chart_game(100), chart_game(1), chart_game(2, "Puzzle"), chart_game(3)],
                        {"style": "", "path": "familiar", "minutes": 20}, provenance(), datetime.now(timezone.utc).isoformat())
    assert len(options) == 3
    assert all(o["app_id"] != "100" for o in options)
    assert options[0]["tag"] == "Strategy"
    assert options[0]["history_evidence"][0]["title"] == "Played Strategy"
    assert options[0]["confidence"] == "High"
    assert "20 minutes" in options[0]["timing"]
    assert "save" in options[0]["timing"]


def test_unknown_freshness_and_no_fit_have_low_confidence():
    options = recommend(history(), [chart_game(1)], {"minutes": 30}, provenance("snapshot"))
    assert options[0]["confidence"] == "Low"
    assert any("acquisition date" in text for text in options[0]["uncertainties"])
    unrelated = recommend(history(), [chart_game(2, "Puzzle")], {"minutes": 30}, provenance())
    assert unrelated[0]["confidence"] == "Low"
    assert recommend(history(), [chart_game(100)], {"minutes": 30}, provenance()) == []


def test_decision_page_comparison_feedback_and_snapshot_immutability(app):
    client = app.test_client()
    run_id = make_plan(client)
    page = client.get(f"/play-next?run={run_id}")
    assert page.status_code == 200
    for label in [b"Primary recommendation", b"Alternative 1", b"Alternative 2", b"Compare your options", b"Medium confidence"]:
        assert label in page.data
    with app.app_context():
        alternative_id = json.loads(db.session.get(DecisionRun, run_id).options_json)[1]["app_id"]
    response = client.post(f"/play-next/{run_id}/feedback", data={
        "csrf_token": token(client), "action": "alternative", "selected_app_id": alternative_id, "usefulness": "4", "comment": "Good match"})
    assert response.status_code == 302
    with app.app_context():
        feedback = DecisionFeedback.query.one()
        assert feedback.action == "alternative" and feedback.selected_app_id == alternative_id and feedback.usefulness == 4
        snapshot = db.session.get(CatalogSnapshot, 1)
        snapshot.games_json = "[]"
        db.session.commit()
        assert len(json.loads(db.session.get(DecisionRun, run_id).options_json)) == 3
    assert b"Gem 1" in client.get(f"/play-next?run={run_id}").data


def test_feedback_validation_scope_and_optional_fields(app):
    client = app.test_client()
    run_id = make_plan(client)
    csrf = token(client)
    endpoint = f"/play-next/{run_id}/feedback"
    assert client.post(endpoint, data={"action": "accept"}).status_code == 400
    assert client.post(endpoint, data={"csrf_token": csrf, "action": "alternative", "selected_app_id": "999"}).status_code == 400
    assert client.post(endpoint, data={"csrf_token": csrf, "action": "rate"}).status_code == 400
    assert client.post(endpoint, data={"csrf_token": csrf, "action": "accept", "usefulness": "9"}).status_code == 400
    stranger = app.test_client()
    stranger_token = token(stranger)
    assert stranger.get(f"/play-next?run={run_id}").status_code == 404
    assert stranger.post(endpoint, data={"csrf_token": stranger_token, "action": "accept"}).status_code == 404
    assert client.post(endpoint, data={"csrf_token": csrf, "action": "accept"}).status_code == 302
    assert client.post(endpoint, data={"csrf_token": csrf, "action": "reject"}).status_code == 302
    with app.app_context():
        feedback = DecisionFeedback.query.one()
        assert feedback.action == "reject" and feedback.usefulness is None and feedback.selected_app_id is None


def test_empty_catalog_missing_evidence_and_clear(app):
    client = app.test_client()
    with app.app_context():
        db.session.get(CatalogSnapshot, 1).games_json = "[]"
        db.session.commit()
    run_id = make_plan(client)
    assert b"No eligible recommendation available" in client.get(f"/play-next?run={run_id}").data
    response = client.post("/play-next/clear", data={"csrf_token": token(client)})
    assert response.status_code == 302
    with app.app_context():
        assert DecisionRun.query.count() == 0 and PlayerProfile.query.count() == 0


def test_private_history_failure_clears_import(app, monkeypatch):
    client = app.test_client()
    csrf = token(client)
    with app.app_context():
        player = PlayerProfile.query.one()
        player.steam_id = "76561198000000000"
        player.games_json = json.dumps(history())
        db.session.commit()
    def fail(self, steam_id):
        raise ExternalServiceError("Private game details")
    monkeypatch.setattr(SteamAccountService, "get_play_history", fail)
    response = client.post("/steam/sync", data={"csrf_token": csrf}, follow_redirects=True)
    assert response.status_code == 200 and b"Private game details" in response.data
    with app.app_context():
        assert PlayerProfile.query.one().games_json == "[]"


def test_link_callback_checks_state_verification_and_replay(app, monkeypatch):
    client = app.test_client()
    response = client.post("/steam/link", data={"csrf_token": token(client)})
    assert response.status_code == 302 and response.location.startswith(OPENID_ENDPOINT)
    query = parse_qs(urlparse(response.location).query)
    callback = query["openid.return_to"][0]
    monkeypatch.setattr(SteamAccountService, "verify_login", lambda self, args, return_to: "76561198000000000")
    with client.session_transaction() as session:
        saved_attempt = session["steam_login"]
    assert client.get(callback).status_code == 302
    with app.app_context():
        assert PlayerProfile.query.one().steam_id == "76561198000000000"
    with client.session_transaction() as session:
        session["steam_login"] = saved_attempt
    assert client.get(callback).status_code == 400


def test_steam_verification_rejects_forged_identity_and_invalid_provider():
    service = SteamAccountService()
    with pytest.raises(ExternalServiceError):
        service.verify_login({"openid.claimed_id": "https://steamcommunity.com/openid/id/76561198000000000"}, "https://example.test/callback")


def valid_openid_fields():
    return {"openid.ns": OPENID_NS, "openid.mode": "id_res", "openid.op_endpoint": OPENID_ENDPOINT,
        "openid.return_to": "https://example.test/callback", "openid.identity": "https://steamcommunity.com/openid/id/76561198000000000",
        "openid.claimed_id": "https://steamcommunity.com/openid/id/76561198000000000",
        "openid.response_nonce": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "nonce",
        "openid.signed": "op_endpoint,claimed_id,identity,return_to,response_nonce,assoc_handle", "openid.assoc_handle": "test", "openid.sig": "signature"}


def test_steam_provider_signature_verification_and_timeout():
    class Session:
        valid = True
        def post(self, url, **kwargs):
            assert url == OPENID_ENDPOINT and kwargs["data"]["openid.mode"] == "check_authentication"
            return type("Response", (), {"status_code": 200, "text": "is_valid:true\n" if self.valid else "is_valid:false\n"})()
    session = Session()
    service = SteamAccountService(session=session)
    assert service.verify_login(valid_openid_fields(), "https://example.test/callback") == "76561198000000000"
    session.valid = False
    with pytest.raises(ExternalServiceError):
        service.verify_login(valid_openid_fields(), "https://example.test/callback")


def test_steam_history_import_and_recent_fallback():
    class Session:
        def get(self, url, **kwargs):
            params = json.loads(kwargs["params"]["input_json"])
            assert params["steamid"] == "76561198000000000"
            if "GetRecentlyPlayedGames" in url:
                raise requests.Timeout()
            return type("Response", (), {"raise_for_status": lambda self: None,
                "json": lambda self: {"response": {"games": [{"appid": 100, "name": "Played Strategy", "playtime_forever": 500}]}}})()
    games, note = SteamAccountService(api_key="test", session=Session()).get_play_history("76561198000000000")
    assert games[0]["lifetime_minutes"] == 500 and games[0]["recent_minutes"] == 0
    assert "lifetime" in note


def test_rawg_mismatched_title_is_not_attached():
    class Session:
        def get(self, *args, **kwargs):
            return type("Response", (), {"status_code": 200, "ok": True,
                "json": lambda self: {"results": [{"name": "Wrong Sequel"}]}})()
    with pytest.raises(ExternalServiceError, match="different title"):
        RawgService("https://example.test", "test", session=Session()).search_game("Original Game")


def test_successful_sync_uses_played_styles_and_records_render_telemetry(app, monkeypatch):
    client = app.test_client()
    csrf = token(client)
    with app.app_context():
        player = PlayerProfile.query.one()
        player.steam_id = "76561198000000000"
        db.session.commit()
    monkeypatch.setattr(SteamAccountService, "get_play_history", lambda self, steam_id: (history(), ""))
    monkeypatch.setattr("routes.decisions.enrich_played_games", lambda games: (games, ""))
    assert client.post("/steam/sync", data={"csrf_token": csrf}).status_code == 302
    run_id = make_plan(client, style="")
    page = client.get(f"/play-next?run={run_id}")
    assert b"Played Strategy" in page.data and b"High confidence" in page.data
    with app.app_context():
        impression = DecisionImpression.query.one()
        displayed = json.loads(impression.displayed_json)
        assert impression.run_id == run_id and displayed[0]["confidence"] == "High"
    assert client.post("/play-next/clear", data={"csrf_token": csrf}).status_code == 302
    with app.app_context():
        assert DecisionImpression.query.count() == 0


def test_real_bundled_chart_supports_offline_decision_flow(app, monkeypatch):
    from services.steam250_scraper import Steam250Scraper
    with app.app_context():
        db.session.delete(db.session.get(CatalogSnapshot, 1))
        db.session.commit()
    monkeypatch.setattr(Steam250Scraper, "_cache", {})
    def offline(self, url):
        raise ExternalServiceError("Offline")
    monkeypatch.setattr(Steam250Scraper, "_fetch_games", offline)
    client = app.test_client()
    run_id = make_plan(client, style="RPG")
    page = client.get(f"/play-next?run={run_id}")
    assert page.status_code == 200 and b"Alternative 2" in page.data
    assert b"Low confidence" in page.data and b"unknown" in page.data
    with app.app_context():
        snapshot = db.session.get(CatalogSnapshot, 1)
        assert snapshot.source_mode == "snapshot" and snapshot.fetched_at is None
        assert len(json.loads(snapshot.games_json)) == 250


def test_decision_database_failure_has_readable_response(app, monkeypatch):
    from sqlalchemy.exc import OperationalError
    client = app.test_client()
    csrf = token(client)
    def unavailable():
        raise OperationalError("select", {}, Exception("offline"))
    monkeypatch.setattr("routes.decisions.get_catalog", unavailable)
    response = client.post("/play-next/generate", data={"csrf_token": csrf})
    assert response.status_code == 503
    assert b"temporarily unavailable" in response.data


def test_variety_avoids_previous_primary_and_preserves_fit():
    import random
    from services.decision_support import select_varied
    ranked = [{"app_id": str(index), "score": 98 - index} for index in range(10)]
    ranked.append({"app_id": "poor-fit", "score": 10})
    first = select_varied(ranked, [], random.Random(4))
    second = select_varied(ranked, [first], random.Random(5))
    assert len(second) == 3
    assert not {o["app_id"] for o in first}.intersection(o["app_id"] for o in second)
    assert all(o["app_id"] != "poor-fit" for o in first + second)
    assert select_varied([], []) == []
    assert all(o["app_id"] not in {p["app_id"] for p in first} for o in select_varied(ranked[:1], [first]))
    scarce = [{"app_id": "strong", "score": 99}, {"app_id": "weak", "score": 20}]
    changed = select_varied(scarce, [[scarce[0]]], random.Random(3))
    assert changed[0]["app_id"] == "weak" and changed[0]["score"] == 20


def test_new_plans_vary_and_named_history_keeps_saved_results(app):
    client = app.test_client()
    with app.app_context():
        db.session.get(CatalogSnapshot, 1).games_json = json.dumps([chart_game(i) for i in range(1, 11)])
        db.session.commit()
    first = make_plan(client)
    second = make_plan(client)
    with app.app_context():
        old = json.loads(db.session.get(DecisionRun, first).options_json)
        new = json.loads(db.session.get(DecisionRun, second).options_json)
        assert not {o["app_id"] for o in old}.intersection(o["app_id"] for o in new)
    assert old[0]["title"].encode() in client.get(f"/play-next?run={first}").data
    page = client.get("/play-next/history")
    assert page.status_code == 200 and b"2 saved plans" in page.data
    assert old[0]["title"].encode() in page.data and new[0]["title"].encode() in page.data
    assert b"0 saved plans" in app.test_client().get("/play-next/history").data


def test_steam_direct_candidate_has_its_own_source_evidence(app, monkeypatch):
    from services.steam_discovery_service import MIN_REVIEWS, MAX_REVIEWS, MIN_APPROVAL
    direct = chart_game(999, "Strategy")
    direct["rank"] = None
    direct["genres"] = ["Indie", "Strategy"]
    direct["evidence_source"] = {**provenance(), "source_mode": "steam", "definition": "GameScope review criteria"}
    monkeypatch.setattr("routes.decisions.get_discovery_catalog", lambda owned, **kwargs: ([direct], {**provenance(), "source_mode": "steam"}))
    client = app.test_client()
    run_id = make_plan(client, catalog_source="steam")
    page = client.get(f"/play-next?run={run_id}")
    assert page.status_code == 200 and b"Steam Store and reviews" in page.data
    assert b"Steam&#39;s review summary" in page.data and b"GameScope review criteria" in page.data
    with app.app_context():
        option = json.loads(db.session.get(DecisionRun, run_id).options_json)[0]
        assert option["tag"] == "Strategy" and option["fit"] == 100


def test_selected_roguelike_is_required_for_primary_and_all_alternatives():
    catalog = [chart_game(1, "Adventure", 100), chart_game(2, "Roguelite", 90),
               chart_game(3, "Action Roguelike", 87), chart_game(4, "RPG", 99)]
    options = recommend([], catalog, {"style": "Roguelike", "minutes": 30}, provenance(), recent_runs=[])
    assert {option["app_id"] for option in options} == {"2", "3"}
    assert all("rogue" in option["tag"].lower() for option in options)
    assert len(options) == 2  # No unrelated third option is used to fill the plan.


def test_specific_tags_resolve_roguelike_without_relabeling_adventure():
    catalog = [{**chart_game(1, "Adventure"), "genres": ["Adventure", "Indie"], "tags": ["Roguelike", "Dungeon Crawler"]},
               {**chart_game(2, "Adventure"), "genres": ["Adventure", "Indie"]}]
    options = recommend([], catalog, {"style": "Roguelike"}, provenance(), recent_runs=[])
    assert len(options) == 1 and options[0]["app_id"] == "1"
    assert options[0]["tag"] == "Roguelike" and "Adventure" in options[0]["categories"]


def test_different_style_excludes_any_usual_genre_even_if_display_tag_is_new():
    catalog = [chart_game(1, "Strategy"), chart_game(2, "Puzzle"),
               {**chart_game(3, "Puzzle"), "genres": ["Puzzle", "Strategy"]}]
    options = recommend(history(), catalog, {"path": "discovery"}, provenance(), recent_runs=[])
    assert [option["app_id"] for option in options] == ["2"]
    assert any("usual styles: strategy" in factor for factor in options[0]["factors"])
    assert recommend([], catalog, {"path": "discovery"}, provenance(), recent_runs=[]) == []
    assert recommend(history(), catalog, {"path": "discovery", "style": "Strategy"}, provenance(), recent_runs=[]) == []


def test_history_exclusion_is_strict_even_when_only_one_new_option_remains():
    catalog = [chart_game(index) for index in range(1, 6)]
    prior = [[{"app_id": "1"}, {"app_id": "2"}, {"app_id": "3"}]]
    options = recommend([], catalog, {"style": "Strategy"}, provenance(), recent_runs=prior, seen_app_ids={"4"})
    assert [option["app_id"] for option in options] == ["5"]
    assert recommend([], catalog, {"style": "Strategy"}, provenance(), recent_runs=prior, seen_app_ids={"4", "5"}) == []
    repeats = recommend([], catalog, {"style": "Strategy", "allow_repeats": True}, provenance(), recent_runs=prior, seen_app_ids={"4", "5"})
    assert len(repeats) == 3


def test_generation_excludes_all_history_beyond_last_ten_plans(app):
    client = app.test_client()
    token(client)
    with app.app_context():
        player = PlayerProfile.query.one()
        for index in range(12):
            db.session.add(DecisionRun(id=f"prior-{index}", profile_id=player.id,
                options_json=json.dumps(recommend([], [chart_game(index+1)], {"style": "Strategy"}, provenance())), context_json="{}"))
        db.session.get(CatalogSnapshot, 1).games_json = json.dumps([chart_game(index) for index in range(1, 14)])
        db.session.commit()
    run_id = make_plan(client)
    with app.app_context():
        options = json.loads(db.session.get(DecisionRun, run_id).options_json)
        assert [option["app_id"] for option in options] == ["13"]


def test_discovery_without_play_styles_explains_blocked_filter(app):
    client = app.test_client()
    run_id = make_plan(client, path="discovery")
    page = client.get(f"/play-next?run={run_id}")
    assert page.status_code == 200 and b"needs resolved Steam play styles" in page.data
    assert b"No eligible recommendation available" in page.data


def test_same_app_can_use_more_specific_chart_evidence_without_duplicate_cards():
    broad = {**chart_game(1, "Adventure"), "genres": ["Adventure"]}
    specific = chart_game(1, "Roguelite")
    options = recommend([], [broad, specific, specific], {"style": "Roguelike"}, provenance(), recent_runs=[])
    assert len(options) == 1 and options[0]["tag"] == "Roguelite"


def test_explicit_repeat_opt_in_keeps_category_and_ownership_filters():
    options = recommend([{"app_id": "1", "genres": [], "recent_minutes": 0, "lifetime_minutes": 0}],
        [chart_game(1, "Roguelite"), chart_game(2, "Roguelite"), chart_game(3, "Adventure")],
        {"style": "Roguelike", "allow_repeats": True}, provenance(), recent_runs=[[{"app_id": "2"}]])
    assert [option["app_id"] for option in options] == ["2"]


def test_discovery_conflicting_category_has_clear_notice(app):
    client = app.test_client()
    token(client)
    with app.app_context():
        PlayerProfile.query.one().games_json = json.dumps(history())
        db.session.commit()
    run_id = make_plan(client, path="discovery", style="Strategy")
    page = client.get(f"/play-next?run={run_id}")
    assert page.status_code == 200 and b"already one of your usual styles" in page.data
    with app.app_context():
        assert json.loads(db.session.get(DecisionRun, run_id).options_json) == []


def test_chart_fallback_cannot_hide_known_familiar_steam_genre():
    steam = {**chart_game(1, "Puzzle"), "genres": ["Puzzle", "Strategy"]}
    chart = chart_game(1, "Puzzle")
    options = recommend(history(), [steam, chart], {"style": "Puzzle", "path": "discovery"}, provenance(), recent_runs=[])
    assert options == []


def test_duplicate_generation_submission_reuses_one_saved_plan(app):
    from uuid import uuid4
    client = app.test_client()
    data = {"csrf_token": token(client), "generation_id": str(uuid4()), "style": "Strategy"}
    first = client.post("/play-next/generate", data=data)
    second = client.post("/play-next/generate", data=data)
    assert first.status_code == second.status_code == 302 and first.location == second.location
    with app.app_context():
        assert DecisionRun.query.count() == 1


def test_step_away_favors_different_category_families_and_respects_avoid_list():
    played = [{"app_id": "100", "title": "Typical Game", "genres": ["Action", "Adventure", "RPG"],
               "recent_minutes": 200, "lifetime_minutes": 500}]
    catalog = [chart_game(1, "Puzzle"), chart_game(2, "Strategy"), chart_game(3, "Simulation"),
               chart_game(4, "Platformer"), {**chart_game(5, "Puzzle"), "genres": ["Puzzle", "RPG"]}]
    preferences = {"path": "discovery", "avoid_styles": ["Action", "Adventure", "RPG"]}
    options = recommend(played, catalog, preferences, provenance(), recent_runs=[])
    assert {option["app_id"] for option in options} == {"1", "2", "3"}
    assert all(option["fit_label"] == "Category distance" for option in options)
    assert all(any("different broad families" in factor for factor in option["factors"]) for option in options)


def test_manual_avoidance_also_works_without_steam_history():
    catalog = [chart_game(1, "Action"), chart_game(2, "Puzzle"), chart_game(3, "Adventure")]
    options = recommend([], catalog, {"path": "discovery", "avoid_styles": ["Action", "Adventure", "RPG"]}, provenance(), recent_runs=[])
    assert [option["app_id"] for option in options] == ["2"]
    familiar = recommend([], catalog, {"path": "familiar", "avoid_styles": ["Action", "Adventure"]}, provenance(), recent_runs=[])
    assert [option["app_id"] for option in familiar] == ["2"]


def test_step_away_randomized_plans_remain_disjoint_with_explicit_avoids(app):
    client = app.test_client()
    with app.app_context():
        db.session.get(CatalogSnapshot, 1).games_json = json.dumps([
            chart_game(index, ("Puzzle", "Strategy", "Simulation")[(index-1) % 3]) for index in range(1, 10)])
        db.session.commit()
    first = make_plan(client, style="", path="discovery", avoid_styles=["Action", "Adventure", "RPG"])
    second = make_plan(client, style="", path="discovery", avoid_styles=["Action", "Adventure", "RPG"])
    with app.app_context():
        old = json.loads(db.session.get(DecisionRun, first).options_json)
        new = json.loads(db.session.get(DecisionRun, second).options_json)
        assert len(old) == len(new) == 3
        assert not {o["app_id"] for o in old}.intersection(o["app_id"] for o in new)
        context = json.loads(db.session.get(DecisionRun, second).context_json)
        assert context["avoid_styles"] == ["Action", "Adventure", "RPG"]
        assert db.session.get(DecisionRun, second).strategy_version == "A6-v4"
    page = client.get(f"/play-next?run={second}")
    assert b"Step outside my usual styles" in page.data and b"You explicitly chose to avoid" in page.data


def test_invalid_avoided_category_is_rejected(app):
    client = app.test_client()
    response = client.post("/play-next/generate", data={"csrf_token": token(client), "avoid_styles": ["Not a category"]})
    assert response.status_code == 400


def test_discovery_alternatives_prefer_category_variety():
    import random
    from services.decision_support import select_varied
    ranked = [{"app_id": str(index), "tag": tag, "score": 95} for index, tag in enumerate(["Puzzle", "Puzzle", "Strategy", "Simulation"])]
    options = select_varied(ranked, [], random.Random(4), diversify_categories=True)
    assert len({option["tag"] for option in options}) == 3
