import json
import os

from flask import current_app, flash, render_template, request
from sqlalchemy.exc import SQLAlchemyError

from models import GameRecord, SearchEvent, db
from routes.library import register_library_routes
from services.external_errors import ExternalServiceError
from services.persistence_service import persist_steam250_games
from services.rawg_service import RawgService
from services.search_service import (
    PAGE_SIZE,
    SORT_OPTIONS,
    SearchInputError,
    normalize_query,
    retrieve_records,
)
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

    @app.route("/search")
    def search():
        raw_query = request.args.get("q", "")
        original_query = raw_query.strip()
        errors = []
        try:
            query = normalize_query(raw_query)
        except SearchInputError as exc:
            query = ""
            errors.append(str(exc))
        source_filter = request.args.get("source", "").strip()
        tag_filter = request.args.get("tag", "").strip()
        sort_by = request.args.get("sort", "relevance").strip()
        requested_page = request.args.get("page", "1")
        try:
            page = int(requested_page)
        except (TypeError, ValueError):
            page = 1
            errors.append("Page number was invalid; showing page 1.")
        if page < 1:
            page = 1
            errors.append("Page number must be positive; showing page 1.")

        try:
            sources = [row[0] for row in db.session.query(GameRecord.source).distinct().order_by(GameRecord.source).all()]
            tags = [row[0] for row in db.session.query(GameRecord.tag).filter(GameRecord.tag.isnot(None)).distinct().order_by(GameRecord.tag).all()]
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Search filter values could not be loaded")
            return render_template(
                "search.html", query=original_query, searched=bool(original_query),
                errors=["Search is temporarily unavailable."], records=[], total=0,
                page=1, page_count=1, page_size=PAGE_SIZE, sources=[], tags=[],
                source_filter="", tag_filter="", sort_by="relevance",
                sort_options=SORT_OPTIONS, start=0, end=0,
            ), 503

        if source_filter and source_filter not in sources:
            source_filter = ""
            errors.append("Unknown source filter was removed.")
        if tag_filter and tag_filter not in tags:
            tag_filter = ""
            errors.append("Unknown genre filter was removed.")
        if sort_by not in SORT_OPTIONS:
            sort_by = "relevance"
            errors.append("Unknown sort option was replaced with relevance.")

        records = []
        total = 0
        searched = bool(request.args.get("q") is not None)
        response_status = 200
        if query:
            try:
                records, total = retrieve_records(
                    query, source_filter, tag_filter, sort_by, page
                )
                page_count = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
                if page > page_count:
                    page = page_count
                    records, total = retrieve_records(
                        query, source_filter, tag_filter, sort_by, page
                    )
            except SQLAlchemyError:
                db.session.rollback()
                current_app.logger.exception("Search retrieval failed")
                errors.append("Search is temporarily unavailable.")
                records = []
                total = 0
                page_count = 1
                response_status = 503
            else:
                event = SearchEvent(
                    query=query,
                    result_count=total,
                    source_filter=source_filter or None,
                    tag_filter=tag_filter or None,
                    sort_by=sort_by,
                    no_results=(total == 0),
                )
                try:
                    with db.session.begin_nested():
                        db.session.add(event)
                    db.session.commit()
                except SQLAlchemyError:
                    db.session.rollback()
                    current_app.logger.exception("Search telemetry could not be recorded")
                    errors.append("Results are available, but search activity could not be recorded.")
                if any("characters or fewer" in error for error in errors):
                    response_status = 400
        else:
            page_count = 1
            if any("characters or fewer" in error for error in errors):
                response_status = 400

        start = (page - 1) * PAGE_SIZE + 1 if total else 0
        end = min(page * PAGE_SIZE, total)
        return render_template(
            "search.html", query=query, original_query=original_query,
            searched=searched, errors=errors, records=records, total=total,
            page=page, page_count=page_count, page_size=PAGE_SIZE,
            sources=sources, tags=tags, source_filter=source_filter,
            tag_filter=tag_filter, sort_by=sort_by, sort_options=SORT_OPTIONS,
            start=start, end=end,
        ), response_status

    @app.route("/search/history")
    def search_history():
        try:
            events = db.session.scalars(
                db.select(SearchEvent).order_by(SearchEvent.created_at.desc()).limit(50)
            ).all()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Search history could not be loaded")
            return render_template("search_history.html", events=[], error=True), 503
        return render_template("search_history.html", events=events, error=False)

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
            try:
                saved_count = persist_steam250_games(games)
                if saved_count:
                    flash(f"Updated {saved_count} Steam 250 records in the database.", "success")
            except SQLAlchemyError:
                db.session.rollback()
                flash("Steam 250 is available, but its records could not be saved to the database.", "error")
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

    register_library_routes(app)
