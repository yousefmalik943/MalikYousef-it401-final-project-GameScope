import os

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    DATA_DIR = os.path.join(BASE_DIR, "data")

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
