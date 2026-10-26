import json

import pytest
import requests

from app import create_app
from models import GameRecord, SearchEvent, db
from services.external_errors import ExternalServiceError
from services.rawg_service import RawgService
from services.search_service import retrieve_records
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


def _add_search_record(app, title, description, source="Steam 250", tag="Strategy", approval=90):
    record = GameRecord(
        title=title,
        description=description,
        source=source,
        source_url=f"https://example.test/{title.lower().replace(' ', '-')}",
        tag=tag,
        approval=approval,
    )
    with app.app_context():
        db.session.add(record)
        db.session.commit()
    return record


def test_search_normalizes_query_ranks_title_hits_and_records_telemetry(client, app):
    _add_search_record(app, "Tactical Echo", "A tactical strategy adventure.", approval=91)
    _add_search_record(app, "Echoes of Aether", "A tactical action adventure.", approval=99)

    response = client.get("/search?q=%20tAcTiCaL%20")

    assert response.status_code == 200
    assert b'value="tAcTiCaL"' in response.data
    assert response.data.index(b"Tactical Echo") < response.data.index(b"Echoes of Aether")
    with app.app_context():
        event = db.session.scalar(db.select(SearchEvent))
        assert event.query == "tAcTiCaL"
        assert event.result_count == 2
        assert event.no_results is False


def test_search_combines_keyword_source_and_tag_filters(client, app):
    _add_search_record(app, "Tactical Echo", "Tactical battles.", source="Steam 250", tag="Strategy")
    _add_search_record(app, "Tactical Harbor", "Tactical exploration.", source="Manual", tag="Adventure")

    response = client.get("/search?q=tactical&source=Steam+250&tag=Strategy")

    assert response.status_code == 200
    assert b"Tactical Echo" in response.data
    assert b"Tactical Harbor" not in response.data


def test_search_pagination_preserves_query_filters_and_sort(client, app):
    for index in range(12):
        _add_search_record(app,
            f"Tactical Entry {index:02}", "Tactical planning.", approval=index
        )

    first_page = client.get("/search?q=tactical&source=Steam+250&tag=Strategy&sort=approval")
    second_page = client.get(
        "/search?q=tactical&source=Steam+250&tag=Strategy&sort=approval&page=2"
    )

    assert b"12 results for" in first_page.data
    assert b"Page 1 of 2" in first_page.data
    assert b"Tactical Entry 11" in first_page.data
    assert b"q=tactical&amp;source=Steam+250&amp;tag=Strategy&amp;sort=approval&amp;page=2" in first_page.data
    assert b"Page 2 of 2" in second_page.data
    assert b"Tactical Entry 11" not in second_page.data


def test_search_handles_empty_long_invalid_and_no_result_queries(client, app):
    empty = client.get("/search?q=%20%20")
    too_long = client.get(f"/search?q={'x' * 121}")
    invalid = client.get("/search?q=missing&source=not-real&sort=invalid&page=-2")

    assert empty.status_code == 200
    assert b"Enter a keyword to begin" in empty.data
    assert too_long.status_code == 400
    assert b"120 characters or fewer" in too_long.data
    assert invalid.status_code == 200
    assert b"Unknown source filter was removed" in invalid.data
    assert b"Unknown sort option" in invalid.data
    assert b"Page number must be positive" in invalid.data
    assert b"No matching records were found" in invalid.data
    with app.app_context():
        event = db.session.scalar(db.select(SearchEvent))
        assert event.no_results is True


def test_search_escapes_like_wildcards_as_literal_query_text(client, app):
    _add_search_record(app, "Discount 100%", "A complete collection.")
    _add_search_record(app, "Discount 1000", "A different title.")

    response = client.get("/search?q=100%25")

    assert b"Discount 100%" in response.data
    assert b"Discount 1000" not in response.data


def test_search_history_displays_recorded_activity(client, app):
    _add_search_record(app, "Tactical Echo", "Tactical battles.")
    client.get("/search?q=tactical&tag=Strategy")

    response = client.get("/search/history")

    assert response.status_code == 200
    assert b"Search Activity" in response.data
    assert b"tactical" in response.data
    assert b"Strategy" in response.data


def test_search_evaluation_queries_return_expected_records(app):
    _add_search_record(app, "Tactical Echo", "A thoughtful strategy game.", tag="Strategy", approval=91)
    _add_search_record(app, "Echoes of Aether", "A tactical role-playing adventure.", tag="RPG", approval=92)
    _add_search_record(app, "Hollow Lantern", "Quiet action exploration across echoing caves.", tag="Adventure", approval=94)
    _add_search_record(app, "Garden Circuit", "Build and manage a peaceful garden.", tag="Simulation", approval=88)
    _add_search_record(app, "Neon Harbor", "Fast action through a crowded port.", tag="Action", approval=86)

    evaluation_cases = {
        "echo": {"Echoes of Aether", "Hollow Lantern", "Tactical Echo"},
        "tactical": {"Echoes of Aether", "Tactical Echo"},
        "garden": {"Garden Circuit"},
        "action": {"Hollow Lantern", "Neon Harbor"},
        "wireless headphones": set(),
    }

    with app.app_context():
        for query, expected_titles in evaluation_cases.items():
            records, _ = retrieve_records(query)
            assert {record.title for record in records} == expected_titles
