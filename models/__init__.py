from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy


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
