from sqlalchemy import case, func

from models import GameRecord, db


PAGE_SIZE = 10
MAX_QUERY_LENGTH = 120
SORT_OPTIONS = {
    "relevance": "Relevance",
    "newest": "Newest first",
    "oldest": "Oldest first",
    "alphabetical": "Title A-Z",
    "approval": "Highest approval",
}


class SearchInputError(ValueError):
    pass


def normalize_query(raw_query):
    query = (raw_query or "").strip()
    if len(query) > MAX_QUERY_LENGTH:
        raise SearchInputError(f"Search terms must be {MAX_QUERY_LENGTH} characters or fewer.")
    return query


def _literal_pattern(query):
    escaped_query = query.replace("!", "!!").replace("%", "!%").replace("_", "!_")
    return f"%{escaped_query}%"


def _matching_conditions(query):
    pattern = _literal_pattern(query)
    return db.or_(
        GameRecord.title.ilike(pattern, escape="!"),
        GameRecord.description.ilike(pattern, escape="!"),
    )


def build_search_statement(query, source_filter="", tag_filter="", sort_by="relevance"):
    statement = db.select(GameRecord)
    conditions = []

    if query:
        conditions.append(_matching_conditions(query))
    if source_filter:
        conditions.append(GameRecord.source == source_filter)
    if tag_filter:
        conditions.append(GameRecord.tag == tag_filter)
    if conditions:
        statement = statement.where(*conditions)

    if query and sort_by == "relevance":
        pattern = _literal_pattern(query)
        relevance = case(
            (func.lower(GameRecord.title) == query.lower(), 5),
            (GameRecord.title.ilike(pattern, escape="!"), 3),
            (GameRecord.description.ilike(pattern, escape="!"), 1),
            else_=0,
        )
        approval_present = case((GameRecord.approval.isnot(None), 1), else_=0)
        statement = statement.order_by(
            relevance.desc(),
            approval_present.desc(),
            GameRecord.approval.desc(),
            GameRecord.retrieved_date.desc(),
            GameRecord.title.asc(),
            GameRecord.id.asc(),
        )
    elif sort_by == "newest":
        statement = statement.order_by(GameRecord.retrieved_date.desc(), GameRecord.id.desc())
    elif sort_by == "oldest":
        statement = statement.order_by(GameRecord.retrieved_date.asc(), GameRecord.id.asc())
    elif sort_by == "alphabetical":
        statement = statement.order_by(GameRecord.title.asc(), GameRecord.id.asc())
    elif sort_by == "approval":
        approval_present = case((GameRecord.approval.isnot(None), 1), else_=0)
        statement = statement.order_by(
            approval_present.desc(),
            GameRecord.approval.desc(),
            GameRecord.title.asc(),
            GameRecord.id.asc(),
        )
    else:
        statement = statement.order_by(GameRecord.title.asc(), GameRecord.id.asc())
    return statement


def retrieve_records(query, source_filter="", tag_filter="", sort_by="relevance", page=1):
    statement = build_search_statement(query, source_filter, tag_filter, sort_by)
    count_statement = db.select(func.count()).select_from(GameRecord)
    conditions = []
    if query:
        conditions.append(_matching_conditions(query))
    if source_filter:
        conditions.append(GameRecord.source == source_filter)
    if tag_filter:
        conditions.append(GameRecord.tag == tag_filter)
    if conditions:
        count_statement = count_statement.where(*conditions)

    total = db.session.scalar(count_statement) or 0
    records = db.session.scalars(
        statement.limit(PAGE_SIZE).offset((page - 1) * PAGE_SIZE)
    ).all()
    return records, total
