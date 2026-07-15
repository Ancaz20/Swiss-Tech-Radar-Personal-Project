from sqlalchemy import create_engine, text

from infrastructure.sqlalchemy_repository import SqlAlchemyJobRepository


def test_sqlalchemy_repository_reads_jobs_and_skills(tmp_path):
    db_path = tmp_path / "jobs.sqlite"
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
            text("INSERT INTO jobs (title, company, location, created, redirect_url) VALUES (:title, :company, :location, :created, :redirect_url)"),
            {
                "title": "Data Engineer",
                "company": "Beta",
                "location": "Geneva",
                "created": "2026-02-01",
                "redirect_url": "https://example.com/job/2",
            },
        )
        connection.execute(text("INSERT INTO skills (name) VALUES (:name)"), {"name": "SQL"})
        connection.execute(text("INSERT INTO job_skills (job_id, skill_id) VALUES (1, 1)"))

    repository = SqlAlchemyJobRepository(db_path=str(db_path))

    jobs = repository.list_jobs(limit=5)

    assert len(jobs) == 1
    assert jobs[0].title == "Data Engineer"
    assert jobs[0].skills == "SQL"
