from sqlalchemy import create_engine, text

import core
from app import create_app
from config import TestingConfig


def _seed_database(db_path):
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE jobs (
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
        """))
        connection.execute(text("""
            CREATE TABLE skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
        """))
        connection.execute(text("""
            CREATE TABLE job_skills (
                job_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL
            )
        """))


def test_refresh_route_redirects_and_flashes_success(tmp_path, monkeypatch):
    db_path = tmp_path / "jobs.sqlite"
    _seed_database(db_path)

    app = create_app(TestingConfig, database_url=f"sqlite:///{db_path}", db_path=str(db_path))
    client = app.test_client()
    monkeypatch.setattr(core, "run_refresh", lambda: (True, "refreshed"))

    response = client.post("/refresh", follow_redirects=True)

    assert response.status_code == 200
    assert b"Ofertas actualizadas correctamente" in response.data
