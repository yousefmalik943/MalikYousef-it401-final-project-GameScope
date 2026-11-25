"""Bounded, cached discovery from Steam's catalog, store data and reviews.

GetAppList and GetAppReviews are documented APIs. The public store appdetails
endpoint is undocumented and isolated here so failures can fall back safely.
"""
import json
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
from flask import current_app

from models import SteamCatalogIndex, SteamDiscoveryGame, db
from services.external_errors import ExternalServiceError
from services.steam_tag_service import SteamTagService

MIN_REVIEWS = 20
MAX_REVIEWS = 5000
MIN_APPROVAL = 85
CATALOG_URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
CATALOG_DOCS = "https://partner.steamgames.com/doc/webapi/IStoreService#GetAppList"
REVIEWS_URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/"


class SteamDiscoveryService:
    def __init__(self, api_key, timeout=6, session=None):
        self.api_key = api_key
        self.timeout = timeout
        # requests.get creates a separate session per call in threaded scans.
        self.session = session or requests

    def _json(self, url, params):
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Expected object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            raise ExternalServiceError("Steam discovery data is unavailable or rate limited. Cached candidates remain available.") from exc

    def get_index(self):
        if not self.api_key:
            raise ExternalServiceError("Steam-wide discovery needs STEAM_WEB_API_KEY on the server.")
        apps = {}
        cursor = 0
        complete = False
        started = time.monotonic()
        for _ in range(10):
            if time.monotonic() - started > 25:
                break
            payload = self._json(CATALOG_URL, {"key": self.api_key, "input_json": json.dumps({
                "include_games": True, "include_dlc": False, "include_software": False,
                "include_videos": False, "include_hardware": False,
                "max_results": 50000, "last_appid": cursor,
            })}).get("response")
            if not isinstance(payload, dict) or not isinstance(payload.get("apps"), list):
                raise ExternalServiceError("Steam returned an unreadable game catalog.")
            for item in payload["apps"]:
                if isinstance(item, dict) and str(item.get("appid", "")).isdigit():
                    apps[str(item["appid"])] = {"app_id": str(item["appid"]), "title": str(item.get("name") or "")[:200]}
            if not payload.get("have_more_results"):
                complete = True
                break
            next_cursor = payload.get("last_appid")
            if type(next_cursor) is not int or next_cursor <= cursor:
                break
            cursor = next_cursor
        if not apps:
            raise ExternalServiceError("Steam returned an empty game catalog.")
        return list(apps.values()), complete

    def inspect_game(self, app):
        app_id = app["app_id"]
        details_url = "https://store.steampowered.com/api/appdetails"
        details = self._json(details_url, {"appids": app_id, "cc": "us", "l": "english"}).get(app_id)
        if not isinstance(details, dict) or not details.get("success") or not isinstance(details.get("data"), dict):
            return None
        game = details["data"]
        if (game.get("type") != "game" or not (game.get("platforms") or {}).get("windows")
                or (game.get("release_date") or {}).get("coming_soon") or game.get("is_free") is None):
            return None
        summary = self._json(REVIEWS_URL, {"input_json": json.dumps({"appid": int(app_id),
            "languages": ["all"], "purchase_type": 1, "review_type": 0, "filter": 0,
            "day_range": 0, "num_per_page": 1, "filter_offtopic_activity": True})}).get("response")
        if not isinstance(summary, dict) or not isinstance(summary.get("query_summary"), dict):
            raise ExternalServiceError("Steam returned an unreadable review summary.")
        summary = summary["query_summary"]
        count, positive = summary.get("total_reviews"), summary.get("total_positive")
        if type(count) is not int or type(positive) is not int or not 0 <= positive <= count:
            raise ExternalServiceError("Steam returned invalid review counts.")
        if not MIN_REVIEWS <= count <= MAX_REVIEWS or positive * 100 < MIN_APPROVAL * count:
            return None
        genres = [str(g["description"])[:120] for g in game.get("genres", []) if isinstance(g, dict) and g.get("description")]
        price = game.get("price_overview") or {}
        now = datetime.now(timezone.utc).isoformat()
        try:
            tags = SteamTagService(timeout=self.timeout, session=self.session).get_tags(app_id)
        except ExternalServiceError:
            tags = []
        return {
            "steam_app_id": app_id, "title": str(game.get("name") or app["title"])[:200],
            "tag": genres[0] if genres else "Unknown", "genres": genres,
            "tags": tags, "tag_source": f"https://store.steampowered.com/app/{app_id}/",
            "tags_checked_at": now,
            "approval": round(100 * positive / count), "review_count": count,
            "price": "Free" if game.get("is_free") else str(price.get("final_formatted") or "Unknown")[:40],
            "currency": price.get("currency"), "price_region": "US", "rank": None,
            "steam_url": f"https://store.steampowered.com/app/{app_id}/",
            "evidence_source": {"source_mode": "steam", "fetched_at": now, "chart_url": f"https://store.steampowered.com/app/{app_id}/#app_reviews_hash",
                "store_url": f"https://store.steampowered.com/app/{app_id}/", "label": "Steam Store and reviews",
                "definition": f"GameScope criteria: {MIN_REVIEWS}–{MAX_REVIEWS:,} reviews and at least {MIN_APPROVAL}% positive; released Windows games only."},
        }


def steam_candidates(owned_ids, seed_apps=None, prioritize_seeds=False):
    """Scan at most 16 random unchecked games; reuse successful checks for 7 days."""
    now = datetime.now(timezone.utc)
    service = SteamDiscoveryService(current_app.config.get("STEAM_WEB_API_KEY"))
    index = db.session.get(SteamCatalogIndex, 1)
    notes = []
    stale_index = index is None or (now - index.fetched_at.replace(tzinfo=timezone.utc)).total_seconds() > 86400
    if stale_index:
        try:
            apps, complete = service.get_index()
            if index is None:
                index = SteamCatalogIndex(id=1)
                db.session.add(index)
            index.apps_json = json.dumps(apps, separators=(",", ":"))
            index.complete = complete
            index.fetched_at = now
            db.session.commit()
        except ExternalServiceError as exc:
            notes.append(str(exc))
    if index is None:
        return [], {"notes": notes, "indexed": 0, "checked": 0, "eligible": 0}
    if not index.complete:
        notes.append("The Steam catalog index is partial; this is not an exhaustive search.")
    records = db.session.scalars(db.select(SteamDiscoveryGame)).all()
    recent_checks = {r.app_id for r in records if (now - r.checked_at.replace(tzinfo=timezone.utc)).total_seconds() < 7 * 86400}
    apps = [app for app in json.loads(index.apps_json) if app["app_id"] not in owned_ids and app["app_id"] not in recent_checks]
    # Seed an initially sparse pool with chart IDs, but recheck all facts on Steam.
    # Most of every scan still explores random entries in the broader catalog.
    cached_eligible = sum(r.eligible for r in records)
    seeds = [app for app in (seed_apps or []) if app["app_id"] not in owned_ids and app["app_id"] not in recent_checks]
    seeds = secrets.SystemRandom().sample(seeds, min(4, len(seeds))) if cached_eligible < 12 or prioritize_seeds else []
    seed_ids = {app["app_id"] for app in seeds}
    apps = [app for app in apps if app["app_id"] not in seed_ids]
    sample = seeds + secrets.SystemRandom().sample(apps, min(16 - len(seeds), len(apps)))
    def inspect(app):
        try:
            game = service.inspect_game(app)
            if game:
                game["discovery_origin"] = "chart_seed" if app["app_id"] in seed_ids else "catalog_sample"
            return app["app_id"], game, None
        except (ExternalServiceError, TypeError, ValueError, AttributeError):
            return app["app_id"], None, "unavailable"
    failed = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(inspect, sample))
    existing = {r.app_id: r for r in records}
    for app_id, game, error in results:
        if error:
            failed += 1
            continue  # Transport failures must not mark games ineligible for seven days.
        record = existing.get(app_id)
        if record is None:
            record = SteamDiscoveryGame(app_id=app_id)
            db.session.add(record)
            existing[app_id] = record
        record.checked_at = now
        record.eligible = game is not None
        record.data_json = json.dumps(game)
    # Upgrade existing positive cache rows without changing their review fetch time.
    pending_tags = []
    for record in records:
        if not record.eligible:
            continue
        data = json.loads(record.data_json)
        checked = data.get("tags_checked_at")
        due = not checked or (now - datetime.fromisoformat(checked).replace(tzinfo=timezone.utc)).total_seconds() >= 86400
        if not data.get("tags") and due and (data.get("evidence_source") or {}).get("source_mode") == "steam":
            pending_tags.append((record.app_id, data))
    def resolve_tags(item):
        app_id, data = item
        try:
            tags = SteamTagService(timeout=service.timeout).get_tags(app_id)
        except ExternalServiceError:
            tags = []
        return app_id, {**data, "tags": tags, "tag_source": f"https://store.steampowered.com/app/{app_id}/", "tags_checked_at": now.isoformat()}
    with ThreadPoolExecutor(max_workers=4) as pool:
        upgrades = list(pool.map(resolve_tags, pending_tags[:8]))
    for app_id, data in upgrades:
        existing[app_id].data_json = json.dumps(data)
    db.session.commit()
    candidates = [json.loads(r.data_json) for r in existing.values() if r.eligible and r.app_id not in owned_ids
                  and (now - r.checked_at.replace(tzinfo=timezone.utc)).total_seconds() < 7 * 86400]
    if failed:
        notes.append(f"Steam metadata was unavailable for {failed} of {len(sample)} sampled games.")
    notes.append("Steam-wide discovery samples the catalog; uninspected games may also qualify. The pool grows as you generate plans.")
    return candidates, {"notes": notes, "indexed": len(json.loads(index.apps_json)), "checked": len(sample), "eligible": len(candidates),
                        "seeded": len(seeds),
                        "index_fetched_at": index.fetched_at.isoformat()}
