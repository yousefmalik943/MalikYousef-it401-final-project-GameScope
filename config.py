import os
from urllib.parse import quote_plus

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    DATA_DIR = os.path.join(BASE_DIR, "data")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        mysql_host = os.environ.get("MYSQL_HOST")
        mysql_user = os.environ.get("MYSQL_USER")
        mysql_database = os.environ.get("MYSQL_DATABASE")
        if mysql_host and mysql_user and mysql_database:
            mysql_password = quote_plus(os.environ.get("MYSQL_PASSWORD", ""))
            mysql_port = os.environ.get("MYSQL_PORT", "3306")
            SQLALCHEMY_DATABASE_URI = (
                f"mysql+pymysql://{quote_plus(mysql_user)}:{mysql_password}"
                f"@{mysql_host}:{mysql_port}/{quote_plus(mysql_database)}?charset=utf8mb4"
            )
        else:
            SQLALCHEMY_DATABASE_URI = "sqlite:///gamescope.db"
    elif SQLALCHEMY_DATABASE_URI.startswith("mysql://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "mysql://", "mysql+pymysql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # A2 external information sources
    RAWG_API_KEY = os.environ.get("RAWG_API_KEY")
    RAWG_API_URL = "https://api.rawg.io/api"
    STEAM_REVIEWS_URL = "https://store.steampowered.com/appreviews"
    STEAM250_URL = "https://steam250.com/hidden_gems"
    STEAM250_MIRROR_URL = "https://raw.githubusercontent.com/250/Steam-250/gh-pages/hidden_gems.html"
    STEAM250_FALLBACK_PATH = os.path.join(DATA_DIR, "steam250_fallback.json")
    EXTERNAL_REQUEST_TIMEOUT = 10
    SCRAPER_REQUEST_TIMEOUT = 30
    SCRAPER_CACHE_SECONDS = 900


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
