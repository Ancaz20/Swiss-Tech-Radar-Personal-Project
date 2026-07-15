CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    adzuna_id TEXT UNIQUE NOT NULL,
    title TEXT,
    company TEXT,
    location TEXT,
    salary_min REAL,
    salary_max REAL,
    contract_type TEXT,
    created TEXT,
    redirect_url TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    PRIMARY KEY (job_id, skill_id),
    FOREIGN KEY (job_id) REFERENCES jobs (id),
    FOREIGN KEY (skill_id) REFERENCES skills (id)
);
