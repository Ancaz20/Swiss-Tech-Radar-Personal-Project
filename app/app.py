import logging
import os

from flask import Flask

from config import DEFAULT_DB_PATH, DEFAULT_INGEST_SCRIPT, DevelopmentConfig
import core
from routes.home import home_bp
from routes.jobs import jobs_bp
from routes.refresh import refresh_bp

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

JOB_SERVICE = None


def _resolve_secret_key() -> str:
    secret_key = os.environ.get("FLASK_SECRET_KEY", "").strip()
    if secret_key:
        return secret_key

    if os.environ.get("FLASK_ENV", "").lower() == "production":
        raise RuntimeError(
            "FLASK_SECRET_KEY no está definida. Establece esta variable de entorno antes de arrancar la app en producción."
        )

    return "dev_secret_key"


def create_app(config_object: type = DevelopmentConfig, *, database_url: str | None = None, db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.config.update(
        SECRET_KEY=_resolve_secret_key(),
        DATABASE_URL=(database_url if database_url is not None else os.environ.get("DATABASE_URL", "").strip()),
        DB_PATH=db_path or DEFAULT_DB_PATH,
        INGEST_SCRIPT=DEFAULT_INGEST_SCRIPT,
    )

    job_service = core.build_job_service(app.config["DATABASE_URL"], app.config["DB_PATH"])
    app.extensions["job_service"] = job_service
    core.set_job_service(job_service)

    app.register_blueprint(home_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(refresh_bp)
    return app


app = create_app()
JOB_SERVICE = app.extensions["job_service"]
get_locale = core.get_locale
get_sort = core.get_sort
get_translations = core.get_translations
load_jobs = core.load_jobs
run_refresh = core.run_refresh


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, port=5000)
