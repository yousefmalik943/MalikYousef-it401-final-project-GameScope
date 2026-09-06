import json
import os

from flask import current_app, render_template, request


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
