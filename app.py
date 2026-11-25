import os

from flask import Flask

from config import config
from models import db
from routes.main import register_routes


def create_app(config_name=None, config_overrides=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    register_routes(app)
    from routes.decisions import decisions
    app.register_blueprint(decisions)

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Database tables created.")

    @app.cli.command("reset-db")
    def reset_db():
        db.drop_all()
        db.create_all()
        print("Database tables reset and recreated.")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config.get("DEBUG", False))
