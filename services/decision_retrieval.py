"""Acquire decision evidence separately from ranking and explanation."""
import json
from flask import current_app

from models import CatalogSnapshot, db
from services.external_errors import ExternalServiceError
from services.persistence_service import persist_steam250_games
from services.rawg_service import RawgService
from services.steam250_scraper import Steam250Scraper


def refresh_catalog():
    config = current_app.config
    scraper = Steam250Scraper(
        config["STEAM250_URL"], timeout=config["SCRAPER_REQUEST_TIMEOUT"],
        cache_seconds=config["SCRAPER_CACHE_SECONDS"], fallback_path=config["STEAM250_FALLBACK_PATH"],
        alternate_urls=[config["STEAM250_MIRROR_URL"]],
    )
    games = scraper.get_hidden_gems(limit=250)
    mode = "snapshot" if scraper.used_fallback else "mirror" if scraper.used_mirror else "live"
    persist_steam250_games(games, mode, scraper.fetched_at)
    return db.session.get(CatalogSnapshot, 1)


def get_catalog():
    snapshot = db.session.get(CatalogSnapshot, 1)
    if snapshot is None:
        snapshot = refresh_catalog()
    return snapshot


def enrich_played_games(games):
    # Bound enrichment to five seed games, never an API call for every owned game.
    from services.decision_support import category_keys, play_weight
    from services.steam_tag_service import SteamTagService
    seeds = sorted((g for g in games if g["lifetime_minutes"] or g["recent_minutes"]), key=play_weight, reverse=True)[:5]
    rawg = RawgService(current_app.config["RAWG_API_URL"], current_app.config.get("RAWG_API_KEY"), timeout=5)
    missing = 0
    for game in seeds:
        try:
            metadata = rawg.search_game(game["title"])
            game["genres"] = metadata["genres"]
            game["genre_source"] = metadata["source_url"]
        except ExternalServiceError:
            pass
        try:
            game["tags"] = SteamTagService(timeout=5).get_tags(game["app_id"])
            game["tag_source"] = f"https://store.steampowered.com/app/{game['app_id']}/"
        except ExternalServiceError:
            game["tags"] = []
        if not category_keys(game):
            missing += 1
    note = f"Styles could not be resolved for {missing} of {len(seeds)} played-game samples." if missing else ""
    if not current_app.config.get("RAWG_API_KEY") and seeds:
        note += " Set RAWG_API_KEY to enable title-matched genre enrichment."
    return games, note.strip()


def snapshot_context(snapshot):
    return {
        "source_mode": snapshot.source_mode,
        "fetched_at": snapshot.fetched_at.isoformat() if snapshot.fetched_at else None,
        "saved_at": snapshot.saved_at.isoformat(),
        "chart_url": current_app.config["STEAM250_URL"],
    }


def get_discovery_catalog(owned_ids, *, preferences=None, played_games=None, seen_app_ids=None):
    from services.steam_discovery_service import CATALOG_DOCS, steam_candidates
    from services.decision_support import build_affinity, matches_preferences
    preferences = preferences or {}
    affinity, _, _ = build_affinity(played_games or [])
    excluded = set() if preferences.get("allow_repeats") else set(seen_app_ids or ())
    snapshot = db.session.get(CatalogSnapshot, 1)
    seeds = [{"app_id": str(g["steam_app_id"]), "title": g["title"]} for g in json.loads(snapshot.games_json)
             if isinstance(g, dict) and str(g.get("steam_app_id", "")).isdigit() and g.get("title")
             and str(g["steam_app_id"]) not in excluded and matches_preferences(g, preferences, affinity)] if snapshot else []
    games, details = steam_candidates(owned_ids, seed_apps=seeds, prioritize_seeds=bool(preferences.get("style") or preferences.get("avoid_styles") or preferences.get("path") == "discovery"))
    notes = list(details["notes"])
    fallback = []
    fallback_context = None
    matching_count = sum(str(g["steam_app_id"]) not in excluded and matches_preferences(g, preferences, affinity) for g in games)
    if matching_count < 3:
        try:
            snapshot = get_catalog()
            fallback_context = snapshot_context(snapshot)
            fallback = [{**game, "evidence_source": fallback_context} for game in json.loads(snapshot.games_json)
                        if str(game.get("steam_app_id")) not in owned_ids]
            notes.append(f"Only {matching_count} unseen Steam-verified candidates match your filters. Matching Steam 250 candidates can supplement this plan; each card identifies its evidence source. Category and history filters still apply.")
        except ExternalServiceError:
            notes.append("The Steam 250 backup was unavailable.")
    provenance = {
        "source_mode": "mixed" if fallback and games else "steam" if games else (fallback_context or {}).get("source_mode", "unavailable"),
        "fetched_at": details.get("index_fetched_at") if games else (fallback_context or {}).get("fetched_at"),
        "chart_url": CATALOG_DOCS, "notes": notes,
        "steam_indexed": details["indexed"], "steam_scanned": details["checked"], "steam_eligible": details["eligible"],
        "steam_seeded": details.get("seeded", 0),
    }
    return games + fallback, provenance
