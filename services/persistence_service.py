from datetime import datetime, timezone
from urllib.parse import urlparse
import json

from models import CatalogSnapshot, GameRecord, db


def persist_steam250_games(games, source_mode="unknown", fetched_at=None):
    saved_count = 0
    valid_games = []
    retrieved_at = datetime.now(timezone.utc)

    for game in games:
        if not isinstance(game, dict):
            continue
        source_url = (game.get("steam_url") or "").strip()
        title = (game.get("title") or "").strip()
        parsed_url = urlparse(source_url)
        app_id = str(game.get("steam_app_id") or "").strip()
        tag = game.get("tag") or "Unknown"
        year = game.get("year") or "Unknown"
        if (
            not title
            or len(title) > 200
            or len(source_url) > 500
            or parsed_url.scheme not in {"http", "https"}
            or not parsed_url.netloc
            or (app_id and (not app_id.isdigit() or len(app_id) > 20))
            or len(str(tag)) > 120
            or len(str(year)) > 20
            or len(str(game.get("score") or "")) > 20
            or len(str(game.get("price") or "")) > 40
            or (game.get("approval") is not None and (type(game["approval"]) is not int or not 0 <= game["approval"] <= 100))
            or (game.get("review_count") is not None and (type(game["review_count"]) is not int or game["review_count"] < 0))
            or (game.get("rank") is not None and (type(game["rank"]) is not int or game["rank"] < 1))
        ):
            continue

        record = GameRecord.query.filter_by(source_url=source_url).first()
        if record is None and game.get("steam_app_id"):
            record = GameRecord.query.filter_by(
                steam_app_id=str(game["steam_app_id"])
            ).first()
        if record is None:
            record = GameRecord(source_url=source_url, created_date=retrieved_at)
            db.session.add(record)

        record.title = title
        record.description = (
            f"Ranked #{game.get('rank', 'unknown')} in Steam 250's Hidden Gems chart. "
            f"Primary tag: {tag}. Release year: {year}."
        )
        record.source = "Steam 250"
        record.source_url = source_url
        # Preserve the original retrieval time for cached data. A snapshot's age is unknown.
        if fetched_at is not None:
            record.retrieved_date = fetched_at
        record.steam_app_id = app_id or None
        record.rank = game.get("rank")
        record.tag = tag
        record.release_year = year
        record.steam250_score = game.get("score")
        record.review_count = game.get("review_count")
        record.approval = game.get("approval")
        record.price = game.get("price")
        image_url = game.get("image") or ""
        parsed_image_url = urlparse(image_url)
        record.image_url = (
            image_url
            if len(image_url) <= 500
            and parsed_image_url.scheme in {"http", "https"}
            and parsed_image_url.netloc
            else None
        )
        saved_count += 1
        valid_games.append(game)

    snapshot = db.session.get(CatalogSnapshot, 1)
    if snapshot is None:
        snapshot = CatalogSnapshot(id=1)
        db.session.add(snapshot)
    snapshot.source_mode = source_mode
    snapshot.fetched_at = fetched_at
    snapshot.saved_at = retrieved_at
    snapshot.games_json = json.dumps(valid_games, ensure_ascii=False)
    db.session.commit()
    return saved_count
