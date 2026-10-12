import os

from flask import Flask

from config import config
from models import db
from routes.main import register_routes


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    register_routes(app)

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        print("Database tables created.")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=app.config.get("DEBUG", False))
