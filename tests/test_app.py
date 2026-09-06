import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app("development")
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app("default")
    app.config.update(TESTING=True)

    with app.test_client() as test_client:
        yield test_client


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
    assert b"Drift Horizon" in response.data


def test_genre_filter_returns_only_strategy_games(client):
    response = client.get("/explore?genre=Strategy")

    assert response.status_code == 200
    assert b"2 games found" in response.data
    assert b"Clockwork Tactics" in response.data
    assert b"Colony Architect" in response.data
    assert b"Neon Divide" not in response.data


def test_combined_filters_return_expected_game(client):
    response = client.get(
        "/explore?query=tactical&genre=Strategy&min_rating=90"
    )

    assert response.status_code == 200
    assert b"1 game found" in response.data
    assert b"Clockwork Tactics" in response.data
    assert b"Colony Architect" not in response.data


def test_no_results_message(client):
    response = client.get("/explore?query=basketball")

    assert response.status_code == 200
    assert b"0 games found" in response.data
    assert b"No matching games found" in response.data
