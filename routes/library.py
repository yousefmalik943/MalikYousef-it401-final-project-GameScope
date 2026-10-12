from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models import GameRecord, db


def _validated_form(form):
    values = {
        field: (form.get(field) or "").strip()
        for field in ("title", "description", "source", "source_url")
    }
    errors = []
    for field, label in (
        ("title", "Title"),
        ("description", "Description"),
        ("source", "Source"),
        ("source_url", "Source URL"),
    ):
        if not values[field]:
            errors.append(f"{label} is required.")

    parsed_url = urlparse(values["source_url"])
    if values["source_url"] and (
        parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc
    ):
        errors.append("Source URL must be a valid http or https URL.")
    if len(values["title"]) > 200:
        errors.append("Title must be 200 characters or fewer.")
    if len(values["source"]) > 120:
        errors.append("Source must be 120 characters or fewer.")
    if len(values["source_url"]) > 500:
        errors.append("Source URL must be 500 characters or fewer.")
    return values, errors


def register_library_routes(app):
    @app.route("/library")
    def library():
        query = request.args.get("query", "").strip()[:80]
        records_query = GameRecord.query
        if query:
            records_query = records_query.filter(
                db.or_(
                    GameRecord.title.ilike(f"%{query}%"),
                    GameRecord.description.ilike(f"%{query}%"),
                    GameRecord.tag.ilike(f"%{query}%"),
                )
            )
        records = records_query.order_by(GameRecord.title.asc()).all()
        return render_template("library.html", records=records, query=query)

    @app.route("/library/new", methods=["GET", "POST"])
    def create_record():
        if request.method == "POST":
            values, errors = _validated_form(request.form)
            duplicate = GameRecord.query.filter_by(source_url=values["source_url"]).first()
            if duplicate:
                errors.append("A record with this source URL already exists.")
            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template("record_form.html", record=None, values=values), 400
            record = GameRecord(**values)
            db.session.add(record)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("A record with this source URL already exists.", "error")
                return render_template("record_form.html", record=None, values=values), 400
            except SQLAlchemyError:
                db.session.rollback()
                flash("The record could not be saved because of a database error.", "error")
                return render_template("record_form.html", record=None, values=values), 500
            flash("Record created.", "success")
            return redirect(url_for("library"))
        return render_template("record_form.html", record=None, values={})

    @app.route("/library/<int:record_id>/edit", methods=["GET", "POST"])
    def edit_record(record_id):
        record = db.get_or_404(GameRecord, record_id)
        if request.method == "POST":
            values, errors = _validated_form(request.form)
            duplicate = GameRecord.query.filter_by(source_url=values["source_url"]).first()
            if duplicate and duplicate.id != record.id:
                errors.append("A record with this source URL already exists.")
            if errors:
                for error in errors:
                    flash(error, "error")
                return render_template("record_form.html", record=record, values=values), 400
            for field, value in values.items():
                setattr(record, field, value)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("A record with this source URL already exists.", "error")
                return render_template("record_form.html", record=record, values=values), 400
            except SQLAlchemyError:
                db.session.rollback()
                flash("The record could not be updated because of a database error.", "error")
                return render_template("record_form.html", record=record, values=values), 500
            flash("Record updated.", "success")
            return redirect(url_for("library"))
        return render_template("record_form.html", record=record, values={})

    @app.route("/library/<int:record_id>/delete", methods=["POST"])
    def delete_record(record_id):
        record = db.get_or_404(GameRecord, record_id)
        db.session.delete(record)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            flash("The record could not be deleted because of a database error.", "error")
        else:
            flash("Record deleted.", "success")
        return redirect(url_for("library"))