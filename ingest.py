import csv
import os
import re
import sqlite3
import time
import requests
import psycopg2

# Detect whether to use Postgres
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)

JUNIOR_TERMS = [
    "junior",
    "graduate",
    "entry level",
    "entry-level",
    "trainee",
    "apprentice",
    "young professional",
    "associate",
]

SENIOR_TERMS = [
    "senior",
    "principal",
    "lead",
    "staff",
    "manager",
    "architect",
    "head of",
    "director",
]

STACK_FOCUS = os.environ.get("STACK_FOCUS")

APP_ID = os.environ.get("ADZUNA_APP_ID")
APP_KEY = os.environ.get("ADZUNA_APP_KEY")
JOOBLE_API_KEY = os.environ.get("JOOBLE_API_KEY", "").strip()
JOOBLE_BASE_URL = os.environ.get("JOOBLE_BASE_URL", "https://ch.jooble.org/api").rstrip("/")
JOOBLE_LOCATION = os.environ.get("JOOBLE_LOCATION", "Switzerland")
JOOBLE_SEARCH_TERMS = [term.strip() for term in os.environ.get("JOOBLE_SEARCH_TERMS", "junior developer,junior software engineer,trainee").split(",") if term.strip()]
COUNTRY = "ch"  # Switzerland
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, "swiss_tech_radar.db")

# Keywords used for simple skill-matching against title + description.
# Extend this list as you notice more relevant terms in real postings.
SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "sql", "docker",
    "kubernetes", "aws", "azure", "gcp", "react", "angular", "vue",
    "c#", ".net", "git", "ci/cd", "fastapi", "flask", "spring", "node",
    "go", "linux", "postgresql", "mysql", "mongodb", "redis", "terraform",
    "jenkins", "github", "gitlab", "devops", "api", "rest", "graphql",
    "microservices", "data", "analyst", "machine learning", "ai"
]

# Feel free to tweak/add search terms (e.g. "entwickler" for German-speaking cantons)
SEARCH_TERMS = [
    "junior developer",
    "junior software engineer",
    "entry level developer",
    "graduate developer",
    "software engineer",
    "entwickler",
    "it junior",
]


def fetch_jobs(search_term, page=1, results_per_page=20):
    """Call the Adzuna API and return a list of raw job dicts."""
    url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/{page}"
    params = {
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "what": search_term,
        "results_per_page": results_per_page,
        "content-type": "application/json",
    }
    # Adzuna occasionally returns transient 5xx/429 responses. Retry briefly
    # before failing the import so one temporary outage does not abort immediately.
    retryable_statuses = {429, 500, 502, 503, 504}
    for attempt in range(3):
        response = requests.get(url, params=params, timeout=15)
        if response.status_code not in retryable_statuses or attempt == 2:
            break
        time.sleep(2 ** attempt)

    response.raise_for_status()
    return response.json().get("results", [])



def normalize_jooble_job(item):
    """Map Jooble's response to the common job shape used by Swiss Tech Radar."""
    external_id = str(item.get("id") or item.get("link") or "").strip()
    if not external_id:
        return None
    return {
        "id": f"jooble:{external_id}",
        "_source": "jooble",
        "title": item.get("title") or "",
        "company": {"display_name": item.get("company") or ""},
        "location": {"display_name": item.get("location") or ""},
        "salary_min": None,
        "salary_max": None,
        "contract_type": item.get("type") or "",
        "created": item.get("updated") or "",
        "redirect_url": item.get("link") or "",
        "description": item.get("snippet") or "",
    }


def fetch_jooble_jobs(search_term, page=1, results_per_page=20):
    """Fetch Swiss listings using Jooble's country-specific REST API."""
    if not JOOBLE_API_KEY:
        return []
    url = f"{JOOBLE_BASE_URL}/{JOOBLE_API_KEY}"
    payload = {
        "keywords": search_term,
        "location": JOOBLE_LOCATION,
        "page": page,
        "ResultOnPage": results_per_page,
        "companysearch": False,
    }
    retryable_statuses = {429, 500, 502, 503, 504}
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
        except requests.RequestException:
            if attempt == 2:
                raise RuntimeError("Jooble request failed due to a network error.")
            time.sleep(2 ** attempt)
            continue
        if response.status_code in retryable_statuses and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        if response.status_code >= 400:
            raise RuntimeError(f"Jooble returned HTTP {response.status_code}. Check the regional API key and access.")
        try:
            data = response.json()
        except ValueError:
            raise RuntimeError("Jooble returned an invalid JSON response.")
        return [job for item in data.get("jobs", []) if (job := normalize_jooble_job(item))]
    return []


def fetch_provider_jobs():
    """Yield jobs from each configured source; a provider failure won't stop the others."""
    if APP_ID and APP_KEY:
        for term in SEARCH_TERMS:
            query = build_search_query(term)
            try:
                for job in fetch_jobs(query):
                    job["_source"] = "adzuna"
                    yield "Adzuna", job
            except Exception as exc:
                print(f"Adzuna search failed for '{term}': {exc}")
    else:
        print("Adzuna skipped: credentials not configured.")

    if JOOBLE_API_KEY:
        for term in JOOBLE_SEARCH_TERMS:
            try:
                for job in fetch_jooble_jobs(build_search_query(term)):
                    yield "Jooble", job
            except Exception as exc:
                print(f"Jooble search failed for '{term}': {exc}")
    else:
        print("Jooble skipped: JOOBLE_API_KEY not configured.")


def extract_skills(text):
    """Return the subset of SKILL_KEYWORDS found in `text`, no duplicates."""
    lowered_text = (text or "").lower()
    found_skills = []
    for skill in SKILL_KEYWORDS:
        pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, lowered_text):
            found_skills.append(skill)
    return found_skills


def get_stack_focus_terms():
    """Return the configured stack focus terms as a normalized list."""
    focus_value = (STACK_FOCUS or os.environ.get("STACK_FOCUS") or "").strip()
    return [part.strip().lower() for part in focus_value.split(",") if part.strip()]


def build_search_query(search_term):
    """Build the API query while keeping the default search broad and stack-specific terms optional."""
    focus_terms = get_stack_focus_terms()
    if not focus_terms:
        return search_term

    return " ".join([search_term, *focus_terms])


def matches_stack_focus(text):
    """Return True when the text matches the configured stack focus, if any."""
    focus_terms = get_stack_focus_terms()
    if not focus_terms:
        return True

    lowered_text = (text or "").lower()
    for term in focus_terms:
        if term in lowered_text:
            return True

    return False  # Exclude jobs that do not match any configured focus term.


def looks_like_junior_role(job):
    """Return True when the title/description looks like a junior or entry-level role."""
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()

    if any(term in text for term in SENIOR_TERMS):
        return False

    if any(term in text for term in JUNIOR_TERMS):
        return True

    return False


def get_connection():
    """Return a DB connection. If DATABASE_URL is set, connect to Postgres and
    ensure schema exists there; otherwise use SQLite with schema.sql."""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        # Create Postgres-compatible schema if not exists
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                adzuna_id TEXT UNIQUE NOT NULL,
                title TEXT,
                company TEXT,
                location TEXT,
                salary_min DOUBLE PRECISION,
                salary_max DOUBLE PRECISION,
                contract_type TEXT,
                created TEXT,
                redirect_url TEXT,
                description TEXT,
                source TEXT NOT NULL DEFAULT 'adzuna'
            );

            CREATE TABLE IF NOT EXISTS skills (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_skills (
                job_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                PRIMARY KEY (job_id, skill_id),
                FOREIGN KEY (job_id) REFERENCES jobs (id),
                FOREIGN KEY (skill_id) REFERENCES skills (id)
            );
            """
        )
        cur.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'adzuna'")
        conn.commit()
        cur.close()
        return conn

    # SQLite fallback
    conn = sqlite3.connect(DB_PATH)
    with open(os.path.join(PROJECT_ROOT, "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    if "source" not in columns:
        conn.execute("ALTER TABLE jobs ADD COLUMN source TEXT NOT NULL DEFAULT 'adzuna'")
        conn.commit()
    return conn


def save_job(conn, job, skills):
    """
    Insert `job` (a raw Adzuna dict) into the jobs table, then link it
    to each skill name in `skills` via the job_skills table.

    TODO: implement this yourself. Hints:
      - Use "INSERT OR IGNORE INTO jobs (...) VALUES (...)" with the
        Adzuna fields you care about (id, title, company, location,
        salary_min, salary_max, contract_type, created, redirect_url,
        description) so re-running the script never creates duplicates
        (adzuna_id is UNIQUE).
      - Adzuna's raw fields are usually: job["id"], job["title"],
        job["company"]["display_name"], job["location"]["display_name"],
        job["salary_min"], job["salary_max"], job["contract_type"],
        job["created"], job["redirect_url"], job["description"].
      - After inserting the job, get its `id` — either from
        cursor.lastrowid, or with a SELECT by adzuna_id if the row
        already existed.
      - For each skill name: INSERT OR IGNORE it into `skills`, look up
        its id, then INSERT OR IGNORE the (job_id, skill_id) pair into
        `job_skills`.
      - Remember to conn.commit() at the end.
    """
    company_data = job.get("company")
    location_data = job.get("location")
    company = company_data.get("display_name") if isinstance(company_data, dict) else company_data
    location = location_data.get("display_name") if isinstance(location_data, dict) else location_data
    source = (job.get("_source") or "adzuna").lower()
    external_id = str(job.get("id") or "").strip()
    if not external_id:
        return

    if USE_POSTGRES:
        cur = conn.cursor()
        # Insert job (avoid duplicates)
        cur.execute(
            """
            INSERT INTO jobs (adzuna_id, title, company, location, salary_min, salary_max,
                              contract_type, created, redirect_url, description, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (adzuna_id) DO NOTHING
            RETURNING id
            """,
            (
                external_id,
                job.get("title"),
                company,
                location,
                job.get("salary_min"),
                job.get("salary_max"),
                job.get("contract_type"),
                job.get("created"),
                job.get("redirect_url"),
                job.get("description"),
                source,
            ),
        )
        inserted = cur.fetchone()
        if inserted:
            job_id = inserted[0]
        else:
            # Row existed; fetch its id
            cur.execute("SELECT id FROM jobs WHERE adzuna_id = %s", (external_id,))
            job_id = cur.fetchone()[0]

        for skill_name in skills:
            cur.execute(
                "INSERT INTO skills (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                (skill_name,),
            )
            cur.execute("SELECT id FROM skills WHERE name = %s", (skill_name,))
            skill_row = cur.fetchone()
            if skill_row:
                cur.execute(
                    "INSERT INTO job_skills (job_id, skill_id) VALUES (%s, %s) ON CONFLICT (job_id, skill_id) DO NOTHING",
                    (job_id, skill_row[0]),
                )

        conn.commit()
        cur.close()
    else:
        conn.execute(
            """
            INSERT OR IGNORE INTO jobs (
                adzuna_id, title, company, location, salary_min, salary_max,
                contract_type, created, redirect_url, description, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                external_id,
                job.get("title"),
                company,
                location,
                job.get("salary_min"),
                job.get("salary_max"),
                job.get("contract_type"),
                job.get("created"),
                job.get("redirect_url"),
                job.get("description"),
                source,
            ),
        )

        cursor = conn.execute("SELECT id FROM jobs WHERE adzuna_id = ?", (external_id,))
        job_row = cursor.fetchone()
        if not job_row:
            return

        job_id = job_row[0]
        for skill_name in skills:
            conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (skill_name,))
            skill_row = conn.execute("SELECT id FROM skills WHERE name = ?", (skill_name,)).fetchone()
            if skill_row:
                conn.execute(
                    "INSERT OR IGNORE INTO job_skills (job_id, skill_id) VALUES (?, ?)",
                    (job_id, skill_row[0]),
                )

        conn.commit()


def export_jobs_to_csv(conn, output_path="job_report.csv"):
    """Export the current jobs and their skills to a CSV file."""
    if USE_POSTGRES:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT jobs.title, jobs.company, jobs.location, jobs.salary_min, jobs.salary_max,
                   jobs.contract_type, jobs.created, jobs.redirect_url, COALESCE(STRING_AGG(skills.name, ', '), ''), jobs.source
            FROM jobs
            LEFT JOIN job_skills ON job_skills.job_id = jobs.id
            LEFT JOIN skills ON skills.id = job_skills.skill_id
            GROUP BY jobs.id
            ORDER BY jobs.id
            """
        )
        rows = cur.fetchall()
        cur.close()
    else:
        rows = conn.execute(
            """
            SELECT jobs.title, jobs.company, jobs.location, jobs.salary_min, jobs.salary_max,
                   jobs.contract_type, jobs.created, jobs.redirect_url, GROUP_CONCAT(skills.name, ', '), jobs.source
            FROM jobs
            LEFT JOIN job_skills ON job_skills.job_id = jobs.id
            LEFT JOIN skills ON skills.id = job_skills.skill_id
            GROUP BY jobs.id
            ORDER BY jobs.id
            """
        ).fetchall()

    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "title",
            "company",
            "location",
            "salary_min",
            "salary_max",
            "contract_type",
            "created",
            "redirect_url",
            "skills",
            "source",
        ])
        writer.writerows(rows)


def main():
    if not ((APP_ID and APP_KEY) or JOOBLE_API_KEY):
        raise SystemExit("Configure Adzuna credentials or JOOBLE_API_KEY before importing jobs.")

    conn = get_connection()
    processed = 0
    try:
        for provider, job in fetch_provider_jobs():
            if not looks_like_junior_role(job):
                continue
            searchable_text = f"{job.get('title', '')} {job.get('description', '')}"
            if not matches_stack_focus(searchable_text):
                continue
            save_job(conn, job, extract_skills(searchable_text))
            processed += 1

        export_jobs_to_csv(conn)
        print(f"Import complete. Processed {processed} job records from configured providers.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
