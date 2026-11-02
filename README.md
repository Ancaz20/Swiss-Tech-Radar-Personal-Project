# Swiss Tech Radar

**A full-stack personal project for discovering, evaluating and tracking junior technology opportunities in Switzerland.**

[Live application](https://swiss-tech-radar.onrender.com) · [Source code](https://github.com/Ancaz20/Swiss-Tech-Radar-Personal-Project)

Swiss Tech Radar turns job-search data into a practical workflow: collect junior and entry-level technology vacancies, extract technical skills, estimate how closely each role matches a configurable profile, and keep track of applications in one place.

> Personal project built end-to-end. The live deployment depends on external Adzuna API credentials and service availability; use the local setup below to run your own instance.

## Product overview

- **Multi-source job discovery:** imports Swiss vacancies from Adzuna and, when configured, Jooble through a shared ingestion pipeline. Each listing records its source.
- **Junior-role filtering:** keeps entry-level, graduate, trainee and junior opportunities while filtering titles that indicate seniority.
- **Skill extraction:** identifies technologies and keywords in job titles and descriptions.
- **Profile matching:** calculates an explainable fit estimate across skills, languages, experience and contract type.
- **Application tracking:** save opportunities, update their status, and keep notes and follow-up details.
- **Internationalized interface:** Spanish, English, German and French.
- **Useful job details:** company, location, publication date, salary range when supplied by the source, detected skills and a link to the original listing.
- **Export:** writes the collected job data and detected skills to CSV.

## Screens and workflow

1. Refresh the listings from the web interface.
2. Review and sort the opportunities by publication date, location, company or shared skills.
3. Inspect the compatibility estimate and its factor breakdown.
4. Open the original listing or translate it.
5. Save interesting roles and manage their progress in **My Applications**.

The application stores jobs separately from application records, so refreshing job data does not intentionally erase a user's tracking history.

## How the matching works

The compatibility estimate is a transparent heuristic, not a hiring prediction:

| Factor | Weight |
| --- | ---: |
| Technical skills | 45% |
| Languages | 25% |
| Experience | 20% |
| Contract type | 10% |

The score includes a breakdown and a confidence indicator showing how much information could be identified in the listing. Unspecified requirements receive a neutral estimate rather than automatically being treated as a mismatch.

The profile can be configured with environment variables such as:

- `PROFILE_SKILLS`: comma-separated technical skills.
- `PROFILE_LANGUAGES`: language levels, for example `spanish:NATIVE,english:C1,french:B1,german:A1`.
- `PROFILE_EXPERIENCE_YEARS`: years of experience used by the heuristic.
- `STACK_FOCUS`: optional terms to focus the job search.

## Architecture

```text
Adzuna API       Jooble REST API (optional)
      |                 |
      +--------+--------+
               v
Python ingestion pipeline (ingest.py)
  - provider-specific adapters
  - common job normalization
  - query construction
  - junior/seniority filtering
  - skill extraction
  - duplicate-safe persistence
  - CSV export
      |
      v
SQLite (local) / PostgreSQL (deployed or Docker)
      |
      v
Flask web application (app/app.py)
  - job listing and sorting
  - profile matching
  - application tracking
  - CSRF-protected form actions
      |
      v
Responsive, multilingual web interface
```

### Technology

- **Backend:** Python, Flask
- **Data and persistence:** PostgreSQL, SQLite, SQL
- **External integration:** Adzuna REST API; optional Jooble REST API
- **Frontend:** server-rendered HTML, Jinja templates, CSS and Bootstrap
- **Packaging and deployment:** Docker, Docker Compose, Render
- **Quality:** Python `unittest` suite and GitHub Actions CI

The refresh action currently launches the ingestion script as a bounded subprocess from the Flask application. It has a timeout and a cooldown to limit repeated requests. The ingestion client retries transient HTTP 429 and 5xx responses. This is a deliberately simple pipeline; it is not presented as a distributed or asynchronous job queue.

## Run locally

### Requirements

- Python 3.11+
- Adzuna API credentials and/or a Jooble API key for importing live listings
- Docker and Docker Compose if you prefer the containerized setup

### Python

From the repository root:

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python app/app.py
```

Open [http://localhost:5000](http://localhost:5000).

Without `DATABASE_URL`, the app uses a local SQLite database. Configure Adzuna (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`) and/or Jooble (`JOOBLE_API_KEY`) before requesting a refresh. Jooble uses a country-specific key and the Switzerland endpoint (`https://ch.jooble.org/api`). Its free API quota is 500 lifetime requests per key, so the default configuration keeps the query list short. See the [Jooble REST API documentation](https://help.jooble.org/en/support/solutions/articles/60001448238).

### Docker Compose

1. Copy `app/.env.example` to `app/.env`.
2. Replace every placeholder with your own credentials and strong secrets.
3. From the `app` directory, run:

```bash
docker compose up --build
```

4. Open [http://localhost:5000](http://localhost:5000).

Compose starts the Flask service and PostgreSQL. The database is available to the app over the internal Compose network.

## Tests and CI

Run the automated tests:

```bash
python -m unittest discover -v
```

GitHub Actions runs the unit tests and builds the Docker image for pushes to `main` and `fix/**` branches and for pull requests targeting `main`.

## Configuration and security

- Never commit `app/.env`, API keys, database passwords or Flask secrets.
- Jooble's API key is embedded in its request URL path by the provider's API design; do not log request URLs or raw request exceptions. The connector reports sanitized provider errors.
- Generate a unique `FLASK_SECRET_KEY` for each deployment.
- The refresh and application-management form actions validate CSRF tokens.
- The refresh subprocess has a time limit and a minimum interval between requests.
- Adzuna query credentials are redacted from ingestion error details before they are logged.
- In Docker Compose, PostgreSQL is not published as a host port; the app uses the private Compose network.

## Why this project is relevant to product engineering

This project gave me hands-on practice owning a feature across the user interface, server-side logic, external API integration, data processing, persistence, deployment and automated tests. It also forced me to handle imperfect real-world inputs: incomplete job descriptions, missing salary data, duplicate listings, provider errors and requirements written in different languages.

That experience is transferable to a product such as Pedra, where a user-facing feature also depends on reliable pipelines and external services. The domain is different: Swiss Tech Radar does **not** currently implement generative image or video models, an iOS capture app, Swift, Next.js or React. Those are areas I would be excited to learn and contribute to.

## Project status and next steps

Swiss Tech Radar is a working personal project with a live deployment and a local Docker setup. Potential next improvements include moving ingestion to a dedicated background worker, adding observability and provider-level integration tests, and expanding the interface with a modern component-based frontend.

---

Built by [Antonio Cazorla González](https://github.com/Ancaz20).
