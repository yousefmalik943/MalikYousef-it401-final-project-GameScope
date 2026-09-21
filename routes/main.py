import json
import os

from flask import current_app, render_template, request

from services.external_errors import ExternalServiceError
from services.rawg_service import RawgService
from services.steam250_scraper import Steam250Scraper
from services.steam_review_service import SteamReviewService


HIDDEN_GEM_GENRES = [
    "Action",
    "Adventure",
    "Casual",
    "Horror",
    "Platformer",
    "Puzzle",
    "Racing",
    "RPG",
    "Roguelike",
    "Simulation",
    "Strategy",
    "Survival",
]


def register_routes(app):
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/explore")
    def explore():
        data_path = os.path.join(current_app.config["DATA_DIR"], "games.json")

        with open(data_path, encoding="utf-8") as data_file:
            games = json.load(data_file)

        query = request.args.get("query", "").strip().lower()
        selected_genre = request.args.get("genre", "").strip()
        selected_mode = request.args.get("mode", "").strip()
        minimum_rating = request.args.get("min_rating", type=int)

        genres = sorted({game["genre"] for game in games})
        modes = sorted({game["mode"] for game in games})
        filtered_games = []

        for game in games:
            searchable_text = " ".join(
                [
                    game["title"],
                    game["description"],
                    game["genre"],
                    game["mode"],
                    *game["tags"],
                ]
            ).lower()

            matches_query = not query or query in searchable_text
            matches_genre = not selected_genre or game["genre"] == selected_genre
            matches_mode = not selected_mode or game["mode"] == selected_mode
            matches_rating = minimum_rating is None or game["rating"] >= minimum_rating

            if matches_query and matches_genre and matches_mode and matches_rating:
                filtered_games.append(game)

        filtered_games.sort(key=lambda game: game["rating"], reverse=True)

        return render_template(
            "explore.html",
            games=filtered_games,
            genres=genres,
            modes=modes,
            selected_genre=selected_genre,
            selected_mode=selected_mode,
            minimum_rating=minimum_rating,
            query=query,
        )

    @app.route("/hidden-gems")
    def hidden_gems():
        query = request.args.get("query", "").strip()[:80]
        selected_genre = request.args.get("genre", "").strip()[:40]
        selected_app_id = request.args.get("appid", "").strip()

        if selected_genre not in HIDDEN_GEM_GENRES:
            selected_genre = ""
        if selected_app_id and not selected_app_id.isdigit():
            selected_app_id = ""

        source_errors = []
        games = []
        api_game = None
        steam_data = None

        scraper = Steam250Scraper(
            source_url=current_app.config["STEAM250_URL"],
            timeout=current_app.config["SCRAPER_REQUEST_TIMEOUT"],
            cache_seconds=current_app.config["SCRAPER_CACHE_SECONDS"],
            fallback_path=current_app.config["STEAM250_FALLBACK_PATH"],
            alternate_urls=[current_app.config["STEAM250_MIRROR_URL"]],
        )
        try:
            games = scraper.get_hidden_gems(limit=250)
            if scraper.used_mirror:
                source_errors.append(
                    "The main Steam 250 hostname is temporarily unavailable. "
                    "Live results were retrieved from Steam 250's official GitHub mirror."
                )
            elif scraper.used_fallback:
                source_errors.append(
                    "Steam 250 is temporarily unavailable. Showing a saved "
                    "Steam 250 snapshot so discovery can continue."
                )
        except ExternalServiceError as exc:
            source_errors.append(str(exc))

        available_genres = [
            genre
            for genre in HIDDEN_GEM_GENRES
            if any(genre.lower() in game["tag"].lower() for game in games)
        ]

        if selected_genre:
            genre_lower = selected_genre.lower()
            games = [game for game in games if genre_lower in game["tag"].lower()]
        if query:
            query_lower = query.lower()
            games = [
                game
                for game in games
                if query_lower in game["title"].lower()
                or query_lower in game["tag"].lower()
            ]

            rawg = RawgService(
                base_url=current_app.config["RAWG_API_URL"],
                api_key=current_app.config.get("RAWG_API_KEY"),
                timeout=current_app.config["EXTERNAL_REQUEST_TIMEOUT"],
            )
            try:
                api_game = rawg.search_game(query)
            except ExternalServiceError as exc:
                source_errors.append(str(exc))

        if selected_app_id:
            steam = SteamReviewService(
                base_url=current_app.config["STEAM_REVIEWS_URL"],
                timeout=current_app.config["EXTERNAL_REQUEST_TIMEOUT"],
            )
            try:
                steam_data = steam.get_reviews(selected_app_id)
            except ExternalServiceError as exc:
                source_errors.append(str(exc))

        return render_template(
            "hidden_gems.html",
            games=games,
            genres=available_genres,
            query=query,
            selected_genre=selected_genre,
            selected_app_id=selected_app_id,
            api_game=api_game,
            steam_data=steam_data,
            source_errors=source_errors,
            steam250_url=current_app.config["STEAM250_URL"],
        )
