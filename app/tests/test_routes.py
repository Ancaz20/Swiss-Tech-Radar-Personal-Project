from sqlalchemy import create_engine, text

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
        connection.execute(
            text("INSERT INTO jobs (title, company, location, salary_min, salary_max, created, redirect_url) VALUES (:title, :company, :location, :salary_min, :salary_max, :created, :redirect_url)"),
            {
                "title": "Python Developer",
                "company": "Acme",
                "location": "Zurich",
                "salary_min": 85000,
                "salary_max": 95000,
                "created": "2026-01-01",
                "redirect_url": "https://example.com/job/1",
            },
        )
        connection.execute(text("INSERT INTO skills (name) VALUES (:name)"), {"name": "Python"})
        connection.execute(text("INSERT INTO job_skills (job_id, skill_id) VALUES (1, 1)"))


def test_index_page_renders_jobs(tmp_path):
    db_path = tmp_path / "jobs.sqlite"
    _seed_database(db_path)

    app = create_app(TestingConfig, database_url=f"sqlite:///{db_path}", db_path=str(db_path))
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Python Developer" in response.data
    assert b"CHF 85,000 - CHF 95,000" in response.data
    assert "🇨🇭 Switzerland".encode("utf-8") in response.data


def test_index_page_filters_jobs_by_query(tmp_path):
    db_path = tmp_path / "jobs.sqlite"
    _seed_database(db_path)

    app = create_app(TestingConfig, database_url=f"sqlite:///{db_path}", db_path=str(db_path))
    client = app.test_client()

    response = client.get("/?q=Acme")

    assert response.status_code == 200
    assert b"Python Developer" in response.data

    response = client.get("/?q=NoMatch")

    assert response.status_code == 200
    assert b"No hay ofertas disponibles" in response.data


def test_jobs_endpoint_returns_json(tmp_path):
    db_path = tmp_path / "jobs.sqlite"
    _seed_database(db_path)

    app = create_app(TestingConfig, database_url=f"sqlite:///{db_path}", db_path=str(db_path))
    client = app.test_client()

    response = client.get("/jobs")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["jobs"][0]["title"] == "Python Developer"
    assert payload["jobs"][0]["city_display"] == "Zurich"
    assert payload["jobs"][0]["country_display"] == "🇨🇭 Switzerland"
    assert payload["jobs"][0]["salary_display"] == "CHF 85,000 - CHF 95,000"
    assert payload["query"] == ""


def test_jobs_endpoint_filters_by_query(tmp_path):
    db_path = tmp_path / "jobs.sqlite"
    _seed_database(db_path)

    app = create_app(TestingConfig, database_url=f"sqlite:///{db_path}", db_path=str(db_path))
    client = app.test_client()

    response = client.get("/jobs?q=Python")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["query"] == "Python"

    response = client.get("/jobs?q=NoMatch")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] == 0
