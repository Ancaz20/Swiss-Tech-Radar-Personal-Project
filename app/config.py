from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = str(ROOT_DIR / "swiss_tech_radar.db")
DEFAULT_INGEST_SCRIPT = str(ROOT_DIR / "ingest.py")
DEFAULT_LANG = "es"
DEFAULT_SORT = "date"
SUPPORTED_SORTS = {"date", "location", "company", "skills"}
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "fr": "Français",
}


class BaseConfig:
    TESTING = False
    DEBUG = False
    DATABASE_URL = ""
    DB_PATH = DEFAULT_DB_PATH
    INGEST_SCRIPT = DEFAULT_INGEST_SCRIPT
    REFRESH_TIMEOUT_SECONDS = 120
    REFRESH_MIN_INTERVAL_SECONDS = 60


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True


class ProductionConfig(BaseConfig):
    DEBUG = False
