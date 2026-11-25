"""A6 decision interface, verified Steam linking, and scoped feedback."""
import hmac
import json
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse
from uuid import UUID, uuid4

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func

from models import DecisionFeedback, DecisionImpression, DecisionRun, PlayerProfile, SteamLoginAttempt, db
from services.decision_retrieval import enrich_played_games, get_catalog, get_discovery_catalog, refresh_catalog, snapshot_context
from services.decision_support import STYLES, avoided_styles, build_affinity, recommend, style_key, usual_styles
from services.external_errors import ExternalServiceError
from services.steam_account_service import SteamAccountService

decisions = Blueprint("decisions", __name__)


@decisions.before_request
def prepare():
    db.create_all()  # Additive A6 tables; existing A1–A5 rows are preserved.
    if "decision_csrf" not in session:
        session["decision_csrf"] = secrets.token_hex(32)
    if request.method == "POST" and not hmac.compare_digest(session["decision_csrf"], request.form.get("csrf_token", "")):
        abort(400, "This form expired. Reload Play Next and try again.")


@decisions.errorhandler(SQLAlchemyError)
def database_unavailable(error):
    db.session.rollback()
    current_app.logger.error("Decision support database operation failed (%s)", type(error).__name__)
    return render_template("decision_error.html"), 503


@decisions.errorhandler(400)
def invalid_input(error):
    return render_template("decision_input_error.html", message=error.description), 400


def profile():
    record = db.session.get(PlayerProfile, session.get("player_profile_id", ""))
    if record is None:
        record = PlayerProfile(id=str(uuid4()), games_json="[]")
        db.session.add(record)
        db.session.commit()
        session["player_profile_id"] = record.id
    return record


def steam_service():
    return SteamAccountService(current_app.config.get("STEAM_WEB_API_KEY"), timeout=current_app.config["EXTERNAL_REQUEST_TIMEOUT"])


def owned_run(run_id):
    record = db.get_or_404(DecisionRun, run_id)
    if record.profile_id != profile().id:
        abort(404)
    return record


@decisions.route("/play-next")
def dashboard():
    player = profile()
    games = json.loads(player.games_json)
    affinity, _, _ = build_affinity(games)
    history = db.session.scalars(db.select(DecisionRun).where(DecisionRun.profile_id == player.id).order_by(DecisionRun.created_at.desc()).limit(10)).all()
    run_id = request.args.get("run")
    run = owned_run(run_id) if run_id else (history[0] if history else None)
    options = json.loads(run.options_json) if run else []
    context = json.loads(run.context_json) if run else {}
    feedback = db.session.scalar(db.select(DecisionFeedback).where(DecisionFeedback.run_id == run.id)) if run else None
    if run:
        db.session.add(DecisionImpression(run_id=run.id, displayed_json=json.dumps([
            {"app_id": option["app_id"], "confidence": option["confidence"]} for option in options
        ])))
        db.session.commit()
    run_ids = db.select(DecisionRun.id).where(DecisionRun.profile_id == player.id)
    feedback_count, rating_count, mean_rating = db.session.execute(db.select(
        func.count(DecisionFeedback.id), func.count(DecisionFeedback.usefulness), func.avg(DecisionFeedback.usefulness)
    ).where(DecisionFeedback.run_id.in_(run_ids))).one()
    stats = {"decisions": feedback_count, "ratings": rating_count, "mean_rating": round(float(mean_rating), 1) if mean_rating is not None else None,
             "views": db.session.scalar(db.select(func.count(DecisionImpression.id)).where(DecisionImpression.run_id.in_(run_ids)))}
    history_cards = [{"run": item, "options": json.loads(item.options_json), "context": json.loads(item.context_json)} for item in history]
    return render_template(
        "decisions.html", player=player, styles=STYLES, context=context, run=run, options=options,
        history=history, history_cards=history_cards, feedback=feedback, affinity=sorted(affinity.items(), key=lambda item: -item[1]),
        csrf_token=session["decision_csrf"], stats=stats, generation_id=str(uuid4()), usual=sorted(usual_styles(affinity)),
    )


@decisions.route("/play-next/generate", methods=["POST"])
def generate():
    player = profile()
    generation_id = request.form.get("generation_id") or str(uuid4())
    try:
        generation_id = str(UUID(generation_id, version=4))
    except ValueError:
        abort(400, "Reload Play Next before generating a new plan.")
    existing = db.session.get(DecisionRun, generation_id)
    if existing:
        if existing.profile_id != player.id:
            abort(404)
        return redirect(url_for("decisions.dashboard", run=existing.id))
    style = request.form.get("style", "")
    path = request.form.get("path", "familiar")
    catalog_source = request.form.get("catalog_source", "chart")
    avoid_styles = list(dict.fromkeys(request.form.getlist("avoid_styles")))
    try:
        minutes = int(request.form.get("minutes", "30"))
    except ValueError:
        abort(400, "Choose a valid trial duration.")
    if (style and style not in STYLES) or any(value not in STYLES for value in avoid_styles) or path not in {"familiar", "discovery"} or minutes not in {20, 30, 60, 120} or catalog_source not in {"chart", "steam"}:
        abort(400, "Choose one of the available preferences.")
    preferences = {"style": style, "path": path, "minutes": minutes, "catalog_source": catalog_source,
                   "allow_repeats": request.form.get("allow_repeats") == "1", "avoid_styles": avoid_styles}
    played = json.loads(player.games_json)
    previous = db.session.scalars(db.select(DecisionRun.options_json).where(DecisionRun.profile_id == player.id)
        .order_by(DecisionRun.created_at.desc(), DecisionRun.id.desc())).all()
    previous_options = [json.loads(value) for value in previous]
    seen_app_ids = {str(option["app_id"]) for options in previous_options for option in options}
    affinity, _, _ = build_affinity(played)
    usual = usual_styles(affinity)
    blocked = avoided_styles(preferences, affinity)
    conflict = style and style_key(style) in blocked
    try:
        if conflict or (path == "discovery" and not blocked):
            note = (f"{style} is already one of your usual styles or explicitly avoided categories. Choose another required category, change the avoided categories, or select Stay close to my style."
                    if conflict else "Different-style discovery needs resolved Steam play styles or categories to avoid. Sync Steam or choose the categories you want to steer away from below.")
            catalog, provenance = [], {"source_mode": "filters", "notes": [note]}
        elif catalog_source == "steam":
            catalog, provenance = get_discovery_catalog({g["app_id"] for g in played}, preferences=preferences,
                                                       played_games=played, seen_app_ids=seen_app_ids)
        else:
            snapshot = get_catalog()
            catalog, provenance = json.loads(snapshot.games_json), snapshot_context(snapshot)
    except ExternalServiceError as exc:
        flash(str(exc), "error")
        return redirect(url_for("decisions.dashboard"))
    options = recommend(
        played, catalog, preferences, provenance,
        synced_at=player.synced_at.isoformat() if player.synced_at else None,
        recent_runs=previous_options[:10], seen_app_ids=seen_app_ids,
    )
    context = {**preferences, **provenance, "history_synced_at": player.synced_at.isoformat() if player.synced_at else None,
               "engine": "A6-v4 category distance and strict exclusions",
               "excluded_usual_styles": sorted(usual) if path == "discovery" else [],
               "excluded_styles": sorted(blocked),
               "previously_shown_excluded": 0 if preferences["allow_repeats"] else len(seen_app_ids)}
    run = DecisionRun(id=generation_id, profile_id=player.id, strategy_version="A6-v4", context_json=json.dumps(context), options_json=json.dumps(options))
    db.session.add(run)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = db.session.get(DecisionRun, generation_id)
        if existing is None or existing.profile_id != player.id:
            raise
        # A double click of the same form resolves to the already-saved plan.
    return redirect(url_for("decisions.dashboard", run=run.id))


@decisions.route("/play-next/history")
def history():
    player = profile()
    page = max(1, request.args.get("page", 1, type=int) or 1)
    statement = db.select(DecisionRun).where(DecisionRun.profile_id == player.id)
    total = db.session.scalar(db.select(func.count()).select_from(statement.subquery()))
    pages = max(1, (total + 19) // 20)
    page = min(page, pages)
    runs = db.session.scalars(statement.order_by(DecisionRun.created_at.desc(), DecisionRun.id.desc()).offset((page - 1) * 20).limit(20)).all()
    cards = [{"run": run, "options": json.loads(run.options_json), "context": json.loads(run.context_json)} for run in runs]
    return render_template("decision_history.html", cards=cards, page=page, pages=pages, total=total)


@decisions.route("/play-next/refresh", methods=["POST"])
def refresh():
    try:
        snapshot = refresh_catalog()
        flash(f"Chart loaded from {snapshot.source_mode}. Generate a new plan to use it.", "success")
    except ExternalServiceError as exc:
        flash(str(exc), "error")
    return redirect(url_for("decisions.dashboard"))


@decisions.route("/play-next/<run_id>/feedback", methods=["POST"])
def save_feedback(run_id):
    run = owned_run(run_id)
    options = json.loads(run.options_json)
    action = request.form.get("action", "")
    selected = request.form.get("selected_app_id", "")
    rating = request.form.get("usefulness", "")
    comment = request.form.get("comment", "").strip()
    ids = [o["app_id"] for o in options]
    if not ids or action not in {"accept", "reject", "alternative", "rate"}:
        abort(400, "Choose a valid decision for the displayed options.")
    if action == "accept":
        selected = ids[0]
    elif action == "alternative":
        if selected not in ids[1:]:
            abort(400, "Select one of the displayed alternatives.")
    else:
        selected = None
    if rating and rating not in {"1", "2", "3", "4", "5"}:
        abort(400, "Usefulness must be between 1 and 5.")
    if action == "rate" and not rating:
        abort(400, "Choose a usefulness rating, or accept or reject without one.")
    if len(comment) > 2000:
        abort(400, "Comments must be 2,000 characters or fewer.")
    feedback = db.session.scalar(db.select(DecisionFeedback).where(DecisionFeedback.run_id == run.id))
    if feedback is None:
        feedback = DecisionFeedback(run_id=run.id)
        db.session.add(feedback)
    feedback.action = action
    feedback.selected_app_id = selected
    feedback.usefulness = int(rating) if rating else None
    feedback.comment = comment or None
    feedback.created_at = datetime.now(timezone.utc)
    db.session.commit()
    flash("Your decision was saved. You can update it below.", "success")
    return redirect(url_for("decisions.dashboard", run=run.id, _anchor="feedback"))


@decisions.route("/steam/link", methods=["POST"])
def link():
    profile()
    secret = current_app.config.get("SECRET_KEY", "")
    if len(secret) < 32 or secret == "replace-with-a-random-development-secret":
        flash("Set SECRET_KEY to a private random value of at least 32 characters before linking Steam.", "error")
        return redirect(url_for("decisions.dashboard"))
    base = current_app.config["PUBLIC_BASE_URL"]
    parsed = urlparse(base)
    if (parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"})) or parsed.path not in {"", "/"} or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
        flash("PUBLIC_BASE_URL must be your HTTPS origin, or an HTTP localhost origin for development.", "error")
        return redirect(url_for("decisions.dashboard"))
    token = secrets.token_hex(32)
    callback = base + url_for("decisions.callback") + "?" + urlencode({"state": token})
    session["steam_login"] = {"state": token, "return_to": callback, "started": time.time()}
    db.session.add(SteamLoginAttempt(token=token))
    db.session.commit()
    return redirect(steam_service().login_url(callback, base + "/"))


@decisions.route("/steam/callback")
def callback():
    attempt = session.pop("steam_login", None)
    if (not attempt or not hmac.compare_digest(attempt["state"], request.args.get("state", ""))
            or time.time() - attempt["started"] > 600 or any(len(request.args.getlist(key)) != 1 for key in request.args)):
        flash("Steam sign-in expired or was not started in this browser. Please try again.", "error")
        return redirect(url_for("decisions.dashboard"))
    # Atomic one-time consumption also rejects a replay with an old signed cookie.
    consumed = db.session.execute(db.update(SteamLoginAttempt).where(
        SteamLoginAttempt.token == attempt["state"], SteamLoginAttempt.consumed.is_(False)
    ).values(consumed=True)).rowcount
    db.session.commit()
    if consumed != 1:
        abort(400, "This Steam sign-in was already used. Start again.")
    try:
        steam_id = steam_service().verify_login(request.args, attempt["return_to"])
    except ExternalServiceError as exc:
        flash(str(exc), "error")
        return redirect(url_for("decisions.dashboard"))
    existing = db.session.scalar(db.select(PlayerProfile).where(PlayerProfile.steam_id == steam_id))
    player = existing or profile()
    if player.steam_id and player.steam_id != steam_id:
        # Linking another account must not carry over the previous account's library.
        player = PlayerProfile(id=str(uuid4()), games_json="[]")
        db.session.add(player)
    player.steam_id = steam_id
    db.session.commit()
    session.clear()
    session["player_profile_id"] = player.id
    flash("Steam account verified. Choose Sync Steam history to import visible games and playtime.", "success")
    return redirect(url_for("decisions.dashboard"))


@decisions.route("/steam/sync", methods=["POST"])
def sync():
    player = profile()
    if not player.steam_id:
        abort(400, "Link Steam before syncing history.")
    try:
        games, note = steam_service().get_play_history(player.steam_id)
        games, enrichment_note = enrich_played_games(games)
    except ExternalServiceError as exc:
        # Do not silently use an old import after privacy changes or an API failure.
        player.games_json = "[]"
        player.synced_at = None
        player.sync_note = str(exc)
        db.session.commit()
        flash(str(exc), "error")
        return redirect(url_for("decisions.dashboard"))
    player.games_json = json.dumps(games, ensure_ascii=False)
    player.synced_at = datetime.now(timezone.utc)
    player.sync_note = " ".join(part for part in [note, enrichment_note] if part) or "Visible history imported successfully."
    db.session.commit()
    flash("Steam history updated. Generate a new plan to use it.", "success")
    return redirect(url_for("decisions.dashboard"))


@decisions.route("/play-next/clear", methods=["POST"])
def clear():
    player = profile()
    ids = db.select(DecisionRun.id).where(DecisionRun.profile_id == player.id)
    db.session.execute(db.delete(DecisionFeedback).where(DecisionFeedback.run_id.in_(ids)))
    db.session.execute(db.delete(DecisionImpression).where(DecisionImpression.run_id.in_(ids)))
    db.session.execute(db.delete(DecisionRun).where(DecisionRun.profile_id == player.id))
    db.session.delete(player)
    db.session.commit()
    session.clear()
    flash("Steam disconnected and your imported history, plans, and feedback were deleted.", "success")
    return redirect(url_for("decisions.dashboard"))
