import os
from pathlib import Path
from typing import Any, List

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from domain.models import JobOffer
from domain.ports import JobRepository


class SqlAlchemyJobRepository(JobRepository):
    def __init__(self, database_url: str | None = None, db_path: str | None = None) -> None:
        self.database_url = database_url or os.environ.get("DATABASE_URL", "").strip()
        self.db_path = db_path or str(Path(__file__).resolve().parents[1] / "swiss_tech_radar.db")

    def _get_engine(self) -> Engine:
        if self.database_url:
            return create_engine(self.database_url)
        db_path = Path(self.db_path).expanduser().resolve()
        return create_engine(f"sqlite:///{db_path.as_posix()}")

    def _initialize(self, engine: Engine) -> None:
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

    def list_jobs(self, limit: int = 200, sort: str = "date") -> List[JobOffer]:
        engine = self._get_engine()
        self._initialize(engine)

        order_clause = {
            "date": "jobs.created DESC",
            "location": "jobs.location COLLATE NOCASE ASC, jobs.created DESC",
            "company": "jobs.company COLLATE NOCASE ASC, jobs.created DESC",
            "skills": "skill_count DESC, jobs.created DESC",
        }.get(sort, "jobs.created DESC")

        if engine.dialect.name == "postgresql":
            skills_expression = "COALESCE(STRING_AGG(skills.name, ', '), '')"
        else:
            skills_expression = "COALESCE(GROUP_CONCAT(skills.name, ', '), '')"

        sql = text(
            f"""
            SELECT
                jobs.id AS id,
                jobs.title AS title,
                jobs.company AS company,
                jobs.location AS location,
                jobs.salary_min AS salary_min,
                jobs.salary_max AS salary_max,
                jobs.contract_type AS contract_type,
                jobs.created AS created,
                jobs.redirect_url AS redirect_url,
                COUNT(skills.id) AS skill_count,
                {skills_expression} AS skills
            FROM jobs
            LEFT JOIN job_skills ON job_skills.job_id = jobs.id
            LEFT JOIN skills ON skills.id = job_skills.skill_id
            GROUP BY jobs.id
            ORDER BY {order_clause}
            LIMIT :limit
            """
        )

        with engine.connect() as connection:
            rows = connection.execute(sql, {"limit": int(limit)}).mappings().all()
            return [
                JobOffer(
                    id=row["id"],
                    title=row["title"],
                    company=row["company"],
                    location=row["location"],
                    salary_min=row["salary_min"],
                    salary_max=row["salary_max"],
                    contract_type=row["contract_type"],
                    created=row["created"],
                    redirect_url=row["redirect_url"],
                    skills=row["skills"],
                    skill_count=row["skill_count"],
                )
                for row in rows
            ]
