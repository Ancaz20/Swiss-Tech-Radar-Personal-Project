import logging
import os
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse

from flask import current_app, has_app_context, request

from application.services import JobService
from config import DEFAULT_LANG, DEFAULT_SORT, DEFAULT_DB_PATH, DEFAULT_INGEST_SCRIPT, SUPPORTED_LANGUAGES, SUPPORTED_SORTS
from infrastructure.sqlalchemy_repository import SqlAlchemyJobRepository
from translations import load_translations

logger = logging.getLogger(__name__)

COUNTRY_FLAGS = {
    "France": "🇫🇷",
    "Germany": "🇩🇪",
    "Netherlands": "🇳🇱",
    "Norway": "🇳🇴",
    "Switzerland": "🇨🇭",
}

COUNTRY_BY_HOST = {
    "europa.eu": None,
    "jobscout24.ch": "Switzerland",
    "jobs.ch": "Switzerland",
    "swissdevjobs.ch": "Switzerland",
}

_JOB_SERVICE: JobService | None = None


def build_job_service(database_url: str | None = None, db_path: str | None = None) -> JobService:
    repository = SqlAlchemyJobRepository(database_url=database_url, db_path=db_path or DEFAULT_DB_PATH)
    return JobService(repository)


def set_job_service(job_service: JobService) -> None:
    global _JOB_SERVICE
    _JOB_SERVICE = job_service


def get_job_service() -> JobService:
    global _JOB_SERVICE

    if has_app_context():
        job_service = current_app.extensions.get("job_service")
        if job_service is not None:
            return job_service

    if _JOB_SERVICE is None:
        _JOB_SERVICE = build_job_service(os.environ.get("DATABASE_URL", "").strip(), DEFAULT_DB_PATH)
    return _JOB_SERVICE


def get_locale() -> str:
    lang = request.values.get("lang", DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANG


def get_sort() -> str:
    sort = request.values.get("sort", DEFAULT_SORT)
    return sort if sort in SUPPORTED_SORTS else DEFAULT_SORT


def get_search_query() -> str:
    return request.values.get("q", "").strip()


def get_translations(lang: str) -> dict[str, Any]:
    return load_translations(lang)


def _format_salary_value(amount: float) -> str:
    return f"CHF {amount:,.0f}"


def _build_salary_display(job: dict[str, Any]) -> str:
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    if salary_min is not None and salary_max is not None:
        if salary_min == salary_max:
            return _format_salary_value(float(salary_min))
        return f"{_format_salary_value(float(salary_min))} - {_format_salary_value(float(salary_max))}"
    if salary_min is not None:
        return f"{_format_salary_value(float(salary_min))}+"
    if salary_max is not None:
        return _format_salary_value(float(salary_max))
    return ""


def _infer_country(location: str, redirect_url: str | None) -> tuple[str, str]:
    cleaned_location = (location or "").strip()
    if not cleaned_location:
        return "", ""

    if " - " in cleaned_location:
        left, right = [part.strip() for part in cleaned_location.split(" - ", 1)]
        if left in COUNTRY_FLAGS:
            return right, left
        if right in COUNTRY_FLAGS:
            return left, right

    if ", " in cleaned_location:
        left, right = [part.strip() for part in cleaned_location.rsplit(", ", 1)]
        if right in COUNTRY_FLAGS:
            return left, right

    if cleaned_location in COUNTRY_FLAGS:
        return "", cleaned_location

    host = urlparse(redirect_url or "").netloc.lower()
    inferred_country = None
    for known_host, country in COUNTRY_BY_HOST.items():
        if host.endswith(known_host):
            inferred_country = country
            break

    if inferred_country is None and host and not host.endswith("europa.eu"):
        inferred_country = "Switzerland"

    return cleaned_location, inferred_country or ""


def _add_job_display_fields(job: dict[str, Any]) -> dict[str, Any]:
    city, country = _infer_country(str(job.get("location") or ""), job.get("redirect_url"))
    flag = COUNTRY_FLAGS.get(country, "")
    salary_display = _build_salary_display(job)
    job["city_display"] = city or "—"
    job["country_display"] = f"{flag} {country}".strip() if country else "—"
    job["salary_display"] = salary_display or "—"
    return job


def _matches_search(job: dict[str, Any], query: str) -> bool:
    if not query:
        return True

    lowered_query = query.casefold()
    haystack = " ".join(
        [
            str(job.get("title") or ""),
            str(job.get("company") or ""),
            str(job.get("location") or ""),
            str(job.get("city_display") or ""),
            str(job.get("country_display") or ""),
            str(job.get("skills") or ""),
        ]
    ).casefold()
    return lowered_query in haystack


def load_jobs(limit: int = 200, sort: str = DEFAULT_SORT, query: str = "") -> list[dict[str, Any]]:
    logger.info("Loading jobs with limit=%s and sort=%s", limit, sort)
    jobs = get_job_service().list_jobs(limit=limit, sort=sort)
    display_jobs = [_add_job_display_fields(job.to_dict()) for job in jobs]
    if not query:
        return display_jobs
    return [job for job in display_jobs if _matches_search(job, query)]


def _resolve_refresh_setting(name: str, default: Any) -> Any:
    if has_app_context():
        return current_app.config.get(name, default)
    return default


def run_refresh() -> tuple[bool, str]:
    ingest_script = _resolve_refresh_setting("INGEST_SCRIPT", DEFAULT_INGEST_SCRIPT)
    refresh_timeout = _resolve_refresh_setting("REFRESH_TIMEOUT_SECONDS", 120)
    root_dir = os.path.dirname(ingest_script)

    if not os.path.exists(ingest_script):
        logger.warning("Ingest script missing at %s", ingest_script)
        return False, "No se encuentra ingest.py en el directorio raíz."

    try:
        logger.info("Refreshing jobs from %s", ingest_script)
        result = subprocess.run(
            [sys.executable, ingest_script],
            cwd=root_dir,
            capture_output=True,
            text=True,
            timeout=refresh_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("Refresh timed out: %s", exc)
        return False, "ingest.py tardó demasiado y se canceló."

    if result.returncode != 0:
        error_detail = (result.stderr or result.stdout or "Error desconocido.").strip()
        logger.error("Refresh failed with stderr: %s", error_detail)
        return False, error_detail

    logger.info("Refresh succeeded")
    return True, result.stdout.strip()
