import json

import pytest
import requests

from app import create_app
from models import GameRecord, db
from services.external_errors import ExternalServiceError
from services.rawg_service import RawgService
from services.steam250_scraper import Steam250Scraper


SAMPLE_GEMS = [
    {"rank": 1, "title": "Small Strategy", "steam_app_id": "12345", "tag": "Strategy", "year": "2024", "score": "9.20", "review_count": 420, "approval": 95, "price": "$9.99", "image": None, "steam_url": "https://store.steampowered.com/app/12345/"},
    {"rank": 2, "title": "Quiet Adventure", "steam_app_id": "67890", "tag": "Adventure", "year": "2023", "score": "9.10", "review_count": 810, "approval": 93, "price": "$14.99", "image": None, "steam_url": "https://store.steampowered.com/app/67890/"},
]


@pytest.fixture()
def app():
    flask_app = create_app("default")
    flask_app.config.update(
        TESTING=True,
        RAWG_API_KEY="test-key",
        SQLALCHEMY_DATABASE_URI="sqlite://",
    )
    with flask_app.app_context():
        db.create_all()
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_database(app):
    yield
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_homepage_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"GameScope" in response.data
    assert b"Discover beyond the obvious" in response.data


def test_explore_page_displays_all_games(client):
    response = client.get("/explore")
    assert response.status_code == 200
    assert b"24 games found" in response.data
    assert b"Echoes of Aether" in response.data


def test_combined_local_filters_return_expected_game(client):
    response = client.get("/explore?query=tactical&genre=Strategy&min_rating=90")
    assert response.status_code == 200
    assert b"1 game found" in response.data
    assert b"Clockwork Tactics" in response.data
    assert b"Colony Architect" not in response.data


def test_no_local_results_message(client):
    response = client.get("/explore?query=basketball")
    assert response.status_code == 200
    assert b"No matching games found" in response.data


def test_steam250_parser_extracts_structured_fields():
    html = """
    <section class="applist compact"><div id="1">
      <div class="rank">1</div><div class="img"><img data-src="//example.com/game.jpg"></div>
      <div class="title"><div><a href="https://club.steam250.com/app/12345" title="Small Strategy">Small Strategy</a>
      <span class="date"><a>2024</a></span></div><div><a class="tag">Strategy</a></div></div>
      <div class="score"><span>9.20</span></div>
      <div class="reviews"><span class="votes">420</span><div class="rating">95%</div></div>
      <div class="price"><span>$9.99</span></div>
      <div class="actions"><a class="store" href="https://store.steampowered.com/app/12345/"></a></div>
    </div></section>
    """
    game = Steam250Scraper.parse_games(html)[0]
    assert game["title"] == "Small Strategy"
    assert game["steam_app_id"] == "12345"
    assert game["tag"] == "Strategy"
    assert game["review_count"] == 420
    assert game["approval"] == 95


def test_rawg_requires_api_key():
    service = RawgService("https://example.test", api_key=None)
    with pytest.raises(ExternalServiceError, match="RAWG_API_KEY"):
        service.search_game("Small Strategy")


def test_steam250_uses_saved_fallback_on_network_failure(tmp_path):
    fallback_path = tmp_path / "steam250.json"
    fallback_path.write_text(json.dumps(SAMPLE_GEMS), encoding="utf-8")

    class FailingSession:
        def get(self, *args, **kwargs):
            raise requests.ConnectionError("offline")

    scraper = Steam250Scraper(
        "https://example.test/hidden-gems",
        session=FailingSession(),
        fallback_path=fallback_path,
    )
    games = scraper.get_hidden_gems()

    assert scraper.used_fallback is True
    assert games[0]["title"] == "Small Strategy"


def test_hidden_gems_filters_scraped_results(client, monkeypatch):
    monkeypatch.setattr("routes.main.Steam250Scraper.get_hidden_gems", lambda self, limit=50: SAMPLE_GEMS)
    response = client.get("/hidden-gems?genre=Strategy")
    assert response.status_code == 200
    assert b"Small Strategy" in response.data
    assert b"Quiet Adventure" not in response.data
    assert b"Live ranking data" in response.data


def test_hidden_gems_combines_api_and_review_data(client, monkeypatch):
    monkeypatch.setattr("routes.main.Steam250Scraper.get_hidden_gems", lambda self, limit=50: SAMPLE_GEMS)
    monkeypatch.setattr("routes.main.RawgService.search_game", lambda self, query: {
        "title": "Small Strategy", "released": "2024-01-02", "rating": 4.5,
        "ratings_count": 120, "metacritic": 84, "playtime": 10, "image": None,
        "genres": ["Strategy"], "platforms": ["PC"],
        "source_url": "https://rawg.io/games/small-strategy",
    })
    monkeypatch.setattr("routes.main.SteamReviewService.get_reviews", lambda self, app_id: {
        "score_description": "Very Positive", "total_positive": 399,
        "total_negative": 21, "total_reviews": 420,
        "reviews": [{"text": "Clever systems and thoughtful battles.", "recommended": True,
                     "helpful_votes": 8, "comment_count": 1, "playtime_hours": 12.5,
                     "developer_response": None}],
        "source_url": "https://store.steampowered.com/app/12345/#app_reviews_hash",
    })
    response = client.get("/hidden-gems?query=Small+Strategy&appid=12345")
    assert response.status_code == 200
    assert b"API result" in response.data
    assert b"Very Positive" in response.data
    assert b"Clever systems and thoughtful battles" in response.data


def test_hidden_gems_handles_external_failure(client, monkeypatch):
    def fail(self, limit=50):
        raise ExternalServiceError("Source is temporarily unavailable.")

    monkeypatch.setattr("routes.main.Steam250Scraper.get_hidden_gems", fail)
    response = client.get("/hidden-gems")
    assert response.status_code == 200
    assert b"Source is temporarily unavailable" in response.data
    assert b"No matching hidden gems found" in response.data


def test_library_create_read_update_and_delete(client, app):
    fields = {
        "title": "Small Strategy",
        "description": "A thoughtful strategy game.",
        "source": "Steam 250",
        "source_url": "https://store.steampowered.com/app/12345/",
    }
    response = client.post("/library/new", data=fields, follow_redirects=True)
    assert response.status_code == 200
    assert b"Small Strategy" in response.data

    with app.app_context():
        record_id = GameRecord.query.one().id
    fields["title"] = "Updated Strategy"
    response = client.post(f"/library/{record_id}/edit", data=fields, follow_redirects=True)
    assert response.status_code == 200
    assert b"Updated Strategy" in response.data

    response = client.post(f"/library/{record_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"No saved game records" in response.data


def test_library_rejects_missing_invalid_and_duplicate_values(client, app):
    response = client.post("/library/new", data={"title": "Incomplete"})
    assert response.status_code == 400
    assert b"Description is required" in response.data

    fields = {
        "title": "Invalid URL",
        "description": "Description",
        "source": "Test",
        "source_url": "javascript:alert(1)",
    }
    response = client.post("/library/new", data=fields)
    assert response.status_code == 400
    assert b"valid http or https URL" in response.data

    fields["title"] = "Valid URL"
    fields["source_url"] = "https://example.test/record"
    assert client.post("/library/new", data=fields).status_code == 302
    assert client.post("/library/new", data=fields).status_code == 400

    with app.app_context():
        assert GameRecord.query.count() == 1


def test_hidden_gems_persists_and_deduplicates_scraped_records(client, app, monkeypatch):
    monkeypatch.setattr(
        "routes.main.Steam250Scraper.get_hidden_gems",
        lambda self, limit=50: SAMPLE_GEMS,
    )
    client.get("/hidden-gems")
    client.get("/hidden-gems")

    with app.app_context():
        records = GameRecord.query.order_by(GameRecord.rank).all()
        assert len(records) == 2
        assert records[0].description.startswith("Ranked #1")
        assert records[0].source == "Steam 250"
        assert records[0].steam_app_id == "12345"


def test_acquired_invalid_records_are_skipped(client, app, monkeypatch):
    invalid_games = [
        {**SAMPLE_GEMS[0], "steam_url": "javascript:alert(1)"},
        {**SAMPLE_GEMS[1], "title": ""},
    ]
    monkeypatch.setattr(
        "routes.main.Steam250Scraper.get_hidden_gems",
        lambda self, limit=50: invalid_games,
    )
    client.get("/hidden-gems")

    with app.app_context():
        assert GameRecord.query.count() == 0


def test_saved_record_survives_new_app_instance(tmp_path):
    database_path = tmp_path / "persistent.sqlite"
    database_uri = f"sqlite:///{database_path.as_posix()}"
    first_app = create_app("default")
    first_app.config.update(SQLALCHEMY_DATABASE_URI=database_uri)
    with first_app.app_context():
        db.create_all()
        db.session.add(GameRecord(
            title="Persistent Entry",
            description="Stored between application instances.",
            source="Test source",
            source_url="https://example.test/persistent",
        ))
        db.session.commit()

    second_app = create_app("default")
    second_app.config.update(SQLALCHEMY_DATABASE_URI=database_uri)
    with second_app.app_context():
        record = GameRecord.query.one()
        assert record.title == "Persistent Entry"
