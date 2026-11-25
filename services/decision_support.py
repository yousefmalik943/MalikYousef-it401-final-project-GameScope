"""Deterministic, explainable A6 ranking. No language model is required."""
import math
import random
from collections import defaultdict
from datetime import datetime, timezone

STYLES = ("Action", "Adventure", "RPG", "Strategy", "Simulation", "Puzzle", "Casual", "Racing", "Sports", "Horror", "Platformer", "Roguelike")
ALIASES = {
    "role-playing": "rpg", "role playing games rpg": "rpg", "role-playing (rpg)": "rpg",
    "jrpg": "rpg", "action rpg": "rpg", "crpg": "rpg",
    "turn-based tactics": "strategy", "turn-based strategy": "strategy",
    "rts": "strategy", "tower defense": "strategy", "grand strategy": "strategy",
    "city builder": "simulation", "life sim": "simulation", "farming sim": "simulation",
    "walking simulator": "adventure", "point & click": "adventure", "visual novel": "adventure",
    "puzzle platformer": "puzzle", "logic": "puzzle",
    "sokoban": "puzzle", "hidden object": "puzzle", "programming": "puzzle",
    "collectathon": "platformer", "metroidvania": "platformer", "side scroller": "platformer",
    "exploration": "adventure", "detective": "adventure", "creature collector": "rpg",
    "hack and slash": "action", "arcade": "action", "runner": "action",
    "precision platformer": "platformer", "2d platformer": "platformer", "3d platformer": "platformer",
    "roguelite": "roguelike", "action roguelike": "roguelike", "traditional roguelike": "roguelike",
    "rogue-like": "roguelike", "rogue-lite": "roguelike", "roguelike deckbuilder": "roguelike",
    "survival horror": "horror", "psychological horror": "horror",
    "fps": "action", "third-person shooter": "action", "shoot 'em up": "action", "bullet hell": "action",
}


def style_key(value):
    value = (value or "").strip().casefold()
    return ALIASES.get(value, value)


def category_labels(game):
    """Preserve source labels; never infer a subgenre from a broad genre."""
    labels = []
    for value in [*(game.get("tags") or []), *(game.get("genres") or []), game.get("tag")]:
        if isinstance(value, str) and value.strip() and value.strip() not in labels:
            labels.append(value.strip())
    return labels


def category_keys(game):
    supported = {style_key(style) for style in STYLES}
    return set().union(*(label_keys(label) for label in category_labels(game))) & supported


def label_keys(label):
    compounds = {
        "puzzle platformer": {"puzzle", "platformer"},
        "action roguelike": {"action", "roguelike"},
        "action rpg": {"action", "rpg"},
        "action-adventure": {"action", "adventure"},
    }
    return compounds.get(label.strip().casefold(), {style_key(label)})


def usual_styles(affinity):
    supported = {style_key(style) for style in STYLES}
    return {key for key, weight in affinity.items() if weight >= .5 and key in supported}


def avoided_styles(preferences, affinity):
    explicit = {style_key(style) for style in preferences.get("avoid_styles", [])}
    if preferences.get("path", "familiar") == "discovery":
        explicit |= usual_styles(affinity)
    return explicit


def category_distance(keys, affinity, avoided):
    """A documented category heuristic, not an inference about pace or mood."""
    families = (
        {"action", "adventure", "rpg", "horror", "platformer", "roguelike"},
        {"puzzle", "strategy", "simulation", "casual"},
        {"racing", "sports"},
    )
    references = {**affinity, **{style: 1.0 for style in avoided}}
    if not keys or not references:
        return 0.0
    def similarity(left, right):
        if left == right:
            return 1.0
        return .5 if any(left in family and right in family for family in families) else 0.0
    return 1 - max(similarity(key, reference) * weight for key in keys for reference, weight in references.items())


def matches_preferences(game, preferences, affinity):
    keys = category_keys(game)
    selected = style_key(preferences.get("style"))
    if selected and selected not in keys:
        return False
    blocked = avoided_styles(preferences, affinity)
    if keys.intersection(blocked):
        return False
    if preferences.get("path", "familiar") == "discovery":
        return bool(blocked and keys)
    return True


def play_weight(game):
    # Log scaling prevents one thousands-of-hours game from consuming the profile.
    return .7 * math.log1p(game.get("recent_minutes", 0)) + .3 * math.log1p(game.get("lifetime_minutes", 0))


def build_affinity(games):
    weights = defaultdict(float)
    evidence = defaultdict(list)
    played = sorted((g for g in games if play_weight(g) > 0), key=play_weight, reverse=True)[:5]
    for game in played:
        genres = category_keys(game)
        for genre in genres:
            weights[genre] += play_weight(game) / len(genres)
            evidence[genre].append({
                "title": game["title"], "app_id": game["app_id"],
                "recent_hours": round(game.get("recent_minutes", 0) / 60, 1),
                "lifetime_hours": round(game.get("lifetime_minutes", 0) / 60, 1),
                "genre_source": game.get("genre_source"),
                "tag_source": game.get("tag_source"),
            })
    maximum = max(weights.values(), default=1)
    return {tag: weight / maximum for tag, weight in weights.items()}, evidence, len(played)


def age_days(timestamp):
    if not timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - parsed).total_seconds() / 86400)
    except (ValueError, TypeError):
        return None


def recommend(games, catalog, preferences, provenance, synced_at=None, recent_runs=None, rng=None, seen_app_ids=None):
    affinity, evidence_by_style, sample_size = build_affinity(games)
    owned = {str(g["app_id"]) for g in games}
    preference = style_key(preferences.get("style"))
    mode = preferences.get("path", "familiar")
    minutes = preferences.get("minutes", 30)
    previously_shown = set(seen_app_ids or ())
    previously_shown.update(str(option["app_id"]) for run in (recent_runs or []) for option in run)
    if preferences.get("allow_repeats"):
        previously_shown.clear()
    history_age = age_days(synced_at)
    ranked = []
    seen = set()
    # A chart row must not erase a familiar genre already reported by Steam for
    # the same App ID. Combine category knowledge before enforcing novelty.
    all_categories = defaultdict(list)
    category_evidence = defaultdict(list)
    for candidate in catalog:
        if not isinstance(candidate, dict):
            continue
        candidate_id = str(candidate.get("steam_app_id") or "")
        candidate_source = candidate.get("evidence_source") or provenance
        url = candidate.get("tag_source") or candidate_source.get("store_url") or candidate_source.get("chart_url")
        for label in category_labels(candidate):
            if label not in all_categories[candidate_id]:
                all_categories[candidate_id].append(label)
            item = {"label": label, "url": url}
            if item not in category_evidence[candidate_id]:
                category_evidence[candidate_id].append(item)
    for game in catalog:
        if not isinstance(game, dict):
            continue
        app_id = str(game.get("steam_app_id") or "")
        source = game.get("evidence_source") or provenance
        freshness = age_days(source.get("fetched_at"))
        fresh = source.get("source_mode") in {"live", "mirror", "steam"} and freshness is not None and freshness <= 2
        categories = category_labels(game)
        if (not app_id.isdigit() or app_id in owned or app_id in seen or app_id in previously_shown
                or not game.get("title") or not matches_preferences(game, preferences, affinity)):
            continue
        combined_keys = category_keys({"tags": all_categories[app_id]})
        blocked = avoided_styles(preferences, affinity)
        if combined_keys.intersection(blocked):
            continue
        display_categories = [label for label in categories if style_key(label) in category_keys(game)] or categories
        tag = max(display_categories or ["Unknown"], key=lambda value: (float(bool(preference and preference in label_keys(value))), affinity.get(style_key(value), 0)))
        seen.add(app_id)
        key = preference if preference and preference in label_keys(tag) else style_key(tag)
        known_style = bool(category_keys(game))
        behavior = affinity.get(key, 0)
        explicit = float(bool(preference and key == preference))
        if preference and affinity:
            fit = .6 * explicit + .4 * behavior
        else:
            fit = explicit if preference else behavior
        approval = game.get("approval")
        review_count = game.get("review_count")
        valid_approval = isinstance(approval, (int, float)) and 0 <= approval <= 100
        valid_count = isinstance(review_count, int) and review_count > 0
        quality = approval / 100 if valid_approval else 0
        support = min(1, math.log1p(review_count) / math.log1p(1000)) if valid_count else 0
        # Discovery eligibility already excludes every usual category. A selected
        # new category is an exact fit; otherwise evidence supports category novelty.
        if mode == "discovery":
            fit = category_distance(combined_keys, affinity, blocked)
        score = 65 * fit + 25 * quality + 10 * support
        matching = evidence_by_style.get(key, [])
        uncertainties = []
        if not known_style:
            uncertainties.append("Primary gameplay category is missing.")
        if mode == "discovery":
            uncertainties.append("Category distance is a design heuristic; it does not establish opposite gameplay or enjoyment.")
        elif not matching and not explicit:
            uncertainties.append("No category match to your resolved play history or stated style.")
        if not fresh:
            uncertainties.append("Source acquisition date is unknown or older than two days.")
        if not valid_approval or not valid_count:
            uncertainties.append("Approval or review-count evidence is incomplete.")
        if matching and (history_age is None or history_age > 7):
            uncertainties.append("Steam history is older than seven days or its sync date is unknown.")
        if not games:
            uncertainties.append("No Steam history is available; ownership is unknown.")
        if sample_size and len({e["app_id"] for items in evidence_by_style.values() for e in items}) < sample_size:
            uncertainties.append("Some sampled games have unresolved genres.")
        confidence = "Low"
        if fit >= .6 and known_style and fresh and valid_approval and valid_count:
            confidence = "Medium"
            if len(matching) >= 2 and history_age is not None and history_age <= 7 and review_count >= 100:
                confidence = "High"
        confidence_reason = {
            "High": "Strong category fit, at least two supporting played games, recent history, source data fetched within two days, and at least 100 reviews.",
            "Medium": "Category fit is supported by a stated preference or resolved play history, with source data fetched within two days and rating evidence; personal evidence is still limited.",
            "Low": "Personal category fit, freshness, or rating evidence is insufficient. Treat this as a discovery suggestion.",
        }[confidence]
        if mode == "discovery" and confidence == "Medium":
            confidence_reason = "Fresh category and rating evidence supports a game outside your excluded reference categories. This does not establish that you will enjoy an unfamiliar category."
        factors = [f"{'Category distance' if mode == 'discovery' else 'Style fit'}: {round(fit * 100)} / 100 ({'farther from your play history and avoided styles' if mode == 'discovery' else 'category similarity'}, not a probability)."]
        if explicit:
            factors.append(f"Matches your selected {preferences['style']} style.")
        if matching:
            factors.append(f"Shares the {tag} category (using the documented category mapping) with {', '.join(e['title'] for e in matching[:3])}.")
        if mode == "discovery":
            factors.append("None of this game's resolved gameplay categories overlap your usual styles: " + ", ".join(sorted(usual_styles(affinity))) + "." if usual_styles(affinity) else "Uses your explicit avoided categories as the discovery reference.")
            factors.append("Favors categories in different broad families from your reference styles; nearby categories receive less weight.")
        if blocked:
            factors.append("Excluded category overlap with: " + ", ".join(sorted(blocked)) + ".")
        if valid_approval:
            label = "Steam's review summary" if source.get("source_mode") == "steam" else "Steam 250"
            factors.append(f"{label} reports {approval}% approval" + (f" across {review_count:,} reviews." if valid_count else "; review count is unavailable."))
        if source.get("source_mode") == "steam":
            factors.append(source["definition"])
            if game.get("discovery_origin") == "chart_seed":
                factors.append("Discovered via a chart seed, then independently checked against Steam Store metadata and review criteria.")
            else:
                factors.append("Discovered through random sampling of Steam's broader game catalog.")
        else:
            factors.append(f"Included in the acquired Steam 250 Hidden Gems chart at rank #{game.get('rank') or '?' }.")
        timing = f"Set aside up to {minutes} minutes for an exploratory trial when you next have free time. Check the game's save and pause options before starting."
        ranked.append({
            "app_id": app_id, "title": str(game["title"])[:200], "tag": tag,
            "score": round(score, 1), "fit": round(fit * 100), "approval": approval if valid_approval else None,
            "review_count": review_count if valid_count else None, "price": game.get("price") or "Unknown",
            "rank": game.get("rank"), "confidence": confidence, "confidence_reason": confidence_reason,
            "factors": factors, "history_evidence": matching[:3], "uncertainties": uncertainties,
            "timing": timing, "steam_url": f"https://store.steampowered.com/app/{app_id}/",
            "ownership": "Not in visible library" if games else "Unknown",
            "source": source,
            "categories": all_categories[app_id], "category_evidence": category_evidence[app_id],
            "fit_label": "Category distance" if mode == "discovery" else "Style fit",
            "category_source": game.get("tag_source") or source.get("store_url") or source.get("chart_url"),
        })
    ranked.sort(key=lambda g: (-g["score"], g["rank"] if isinstance(g["rank"], int) else 9999, g["app_id"]))
    varied = recent_runs is not None
    options = select_varied(ranked, [] if preferences.get("allow_repeats") else recent_runs, rng, diversify_categories=mode == "discovery") if varied else ranked[:3]
    for index, option in enumerate(options):
        option["role"] = "Primary recommendation" if index == 0 else f"Alternative {index}"
        option["selection_reason"] = (
            "Random selection among eligible matches after applying your category, discovery-path, ownership, and history filters. Fewer options are shown when there are not enough fresh matches."
            if varied else
            "Highest score among eligible, unowned chart candidates using your selected path."
            if index == 0 else f"Next eligible candidate at position {index + 1} under the same scoring rules; compare its category, approval and quoted price with the primary choice."
        )
    return options


def select_varied(ranked, recent_runs, rng=None, diversify_categories=False):
    """Sample only unseen eligible options; never backfill with prior results."""
    excluded = {option["app_id"] for run in recent_runs for option in run}
    ranked = [option for option in ranked if option["app_id"] not in excluded]
    if not ranked:
        return []
    rng = rng or random.SystemRandom()
    pool = [o for o in ranked[:30] if o["score"] >= ranked[0]["score"] - 20]
    if len(pool) < min(3, len(ranked)):
        pool = ranked[:3]
    def pick(items):
        return rng.choices(items, weights=[max(1, o["score"]) ** 2 for o in items], k=1)[0]
    primary = pick(pool)
    options = [primary]
    remaining = [o for o in pool if o["app_id"] != primary["app_id"]]
    while remaining and len(options) < 3:
        chosen_categories = {style_key(option.get("tag")) for option in options}
        different = [option for option in remaining if style_key(option.get("tag")) not in chosen_categories]
        chosen = pick(different if diversify_categories and different else remaining)
        options.append(chosen)
        remaining.remove(chosen)
    # Preserve useful comparisons when fewer than three similarly scoring options exist.
    for option in ranked:
        if len(options) >= 3:
            break
        if option not in options:
            options.append(option)
    for option in options:
        option["seen_in_recent_plans"] = 0
    return options
