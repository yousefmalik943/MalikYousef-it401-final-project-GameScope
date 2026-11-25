from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import LONGTEXT


db = SQLAlchemy()


class GameRecord(db.Model):
	__tablename__ = "game_records"

	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(200), nullable=False, index=True)
	description = db.Column(db.Text, nullable=False)
	source = db.Column(db.String(120), nullable=False)
	source_url = db.Column(db.String(500), nullable=False, unique=True)
	retrieved_date = db.Column(
		db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
	)
	created_date = db.Column(
		db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
	)
	steam_app_id = db.Column(db.String(20), unique=True, index=True)
	rank = db.Column(db.Integer)
	tag = db.Column(db.String(120))
	release_year = db.Column(db.String(20))
	steam250_score = db.Column(db.String(20))
	review_count = db.Column(db.Integer)
	approval = db.Column(db.Integer)
	price = db.Column(db.String(40))
	image_url = db.Column(db.String(500))


class SearchEvent(db.Model):
	__tablename__ = "search_events"

	id = db.Column(db.Integer, primary_key=True)
	query = db.Column(db.String(120), nullable=False, index=True)
	created_at = db.Column(
		db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
	)
	result_count = db.Column(db.Integer, nullable=False, default=0)
	source_filter = db.Column(db.String(120))
	tag_filter = db.Column(db.String(120))
	sort_by = db.Column(db.String(20), nullable=False, default="relevance")
	no_results = db.Column(db.Boolean, nullable=False, default=False)


class GeneratedIntelligence(db.Model):
	__tablename__ = "generated_intelligences"

	id = db.Column(db.Integer, primary_key=True)
	user_request = db.Column(db.Text, nullable=False)
	prompt_version = db.Column(db.String(40), nullable=False, default="A5-v1")
	model_used = db.Column(db.String(80), nullable=False, default="local-deterministic-engine")
	generated_at = db.Column(
		db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
	)
	source_record_ids = db.Column(db.Text, nullable=False, default="[]")
	output_data = db.Column(db.Text, nullable=False)
	summary = db.Column(db.Text, nullable=False)
	recommendation = db.Column(db.Text, nullable=False)
	confidence = db.Column(db.String(20), nullable=False)
	supporting_items = db.Column(db.Text, nullable=False)


class CatalogSnapshot(db.Model):
    """Latest acquired chart; separate acquisition time from local save time."""
    __tablename__ = "catalog_snapshots"
    id = db.Column(db.Integer, primary_key=True)
    source_mode = db.Column(db.String(30), nullable=False)
    fetched_at = db.Column(db.DateTime(timezone=True))
    saved_at = db.Column(db.DateTime(timezone=True), nullable=False)
    games_json = db.Column(db.Text().with_variant(LONGTEXT(), "mysql"), nullable=False)


class PlayerProfile(db.Model):
    __tablename__ = "player_profiles"
    id = db.Column(db.String(36), primary_key=True)
    steam_id = db.Column(db.String(20), unique=True)
    games_json = db.Column(db.Text().with_variant(LONGTEXT(), "mysql"), nullable=False, default="[]")
    synced_at = db.Column(db.DateTime(timezone=True))
    sync_note = db.Column(db.Text)


class DecisionRun(db.Model):
    __tablename__ = "decision_runs"
    id = db.Column(db.String(36), primary_key=True)
    profile_id = db.Column(db.String(36), db.ForeignKey("player_profiles.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    strategy_version = db.Column(db.String(30), nullable=False, default="A6-v1")
    context_json = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text, nullable=False)


class DecisionFeedback(db.Model):
    __tablename__ = "decision_feedback"
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(36), db.ForeignKey("decision_runs.id"), nullable=False, unique=True)
    action = db.Column(db.String(30), nullable=False)
    selected_app_id = db.Column(db.String(20))
    usefulness = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class SteamLoginAttempt(db.Model):
    __tablename__ = "steam_login_attempts"
    token = db.Column(db.String(64), primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    consumed = db.Column(db.Boolean, nullable=False, default=False)


class DecisionImpression(db.Model):
    __tablename__ = "decision_impressions"
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(36), db.ForeignKey("decision_runs.id"), nullable=False, index=True)
    shown_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    # Immutable option IDs and displayed confidence at the time of the render.
    displayed_json = db.Column(db.Text, nullable=False)


class SteamCatalogIndex(db.Model):
    __tablename__ = "steam_catalog_indexes"
    id = db.Column(db.Integer, primary_key=True)
    apps_json = db.Column(db.Text().with_variant(LONGTEXT(), "mysql"), nullable=False)
    fetched_at = db.Column(db.DateTime(timezone=True), nullable=False)
    complete = db.Column(db.Boolean, nullable=False, default=False)


class SteamDiscoveryGame(db.Model):
    __tablename__ = "steam_discovery_games"
    app_id = db.Column(db.String(20), primary_key=True)
    checked_at = db.Column(db.DateTime(timezone=True), nullable=False)
    eligible = db.Column(db.Boolean, nullable=False)
    data_json = db.Column(db.Text, nullable=False)
