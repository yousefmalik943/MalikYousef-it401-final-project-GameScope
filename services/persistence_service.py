from datetime import datetime, timezone
from urllib.parse import urlparse

from models import GameRecord, db


def persist_steam250_games(games):
    saved_count = 0
    retrieved_at = datetime.now(timezone.utc)

    for game in games:
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
        record.retrieved_date = retrieved_at
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

    db.session.commit()
    return saved_count