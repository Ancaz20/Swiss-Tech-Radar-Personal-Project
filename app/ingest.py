import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from infrastructure.job_sources import fetch_jobs

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = str(ROOT_DIR / "swiss_tech_radar.db")


def get_engine(database_url: str | None = None, db_path: str | None = None) -> Engine:
    database_url = (database_url or os.environ.get("DATABASE_URL", "")).strip()
    if database_url:
        return create_engine(database_url)

    database_path = Path(db_path or DEFAULT_DB_PATH).expanduser().resolve()
    return create_engine(f"sqlite:///{database_path.as_posix()}")


def initialize_database(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT NOT NULL,
                    salary_min REAL,
                    salary_max REAL,
                    contract_type TEXT,
                    created TEXT NOT NULL,
                    redirect_url TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS job_skills (
                    job_id INTEGER NOT NULL,
                    skill_id INTEGER NOT NULL
                )
                """
            )
        )


def import_jobs(database_url: str | None = None, db_path: str | None = None, limit: int = 20) -> int:
    engine = get_engine(database_url=database_url, db_path=db_path)
    initialize_database(engine)

    jobs = fetch_jobs(limit=limit)

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM job_skills"))
        connection.execute(text("DELETE FROM skills"))
        connection.execute(text("DELETE FROM jobs"))

        for job in jobs:
            result = connection.execute(
                text(
                    """
                    INSERT INTO jobs (
                        title, company, location, salary_min, salary_max,
                        contract_type, created, redirect_url
                    ) VALUES (:title, :company, :location, :salary_min, :salary_max, :contract_type, :created, :redirect_url)
                    """
                ),
                {
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "contract_type": job.get("contract_type"),
                    "created": job.get("created", ""),
                    "redirect_url": job.get("redirect_url", ""),
                },
            )
            job_id = result.lastrowid
            for skill_name in job.get("skills", []):
                skill_result = connection.execute(
                    text("INSERT INTO skills (name) VALUES (:name)"),
                    {"name": skill_name},
                )
                connection.execute(
                    text("INSERT INTO job_skills (job_id, skill_id) VALUES (:job_id, :skill_id)"),
                    {"job_id": job_id, "skill_id": skill_result.lastrowid},
                )

    return len(jobs)


def main() -> int:
    try:
        count = import_jobs()
    except Exception as exc:  # pragma: no cover - CLI guardrail
        print(f"Refresh failed: {exc}", file=sys.stderr)
        return 1

    print(f"Imported {count} jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
