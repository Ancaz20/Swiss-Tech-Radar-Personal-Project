# Swiss Tech Radar — project presentation for Pedra

This document is a short, interview-ready walkthrough tailored to Pedra's product engineering internship. It describes the implementation in this repository and separates existing experience from areas to learn.

## Slide 1 — Swiss Tech Radar

**From job listings to an actionable job-search workflow**

A full-stack personal project that collects junior technology vacancies in Switzerland, analyses their requirements against a configurable profile, and helps a user manage applications.

- Live demo: https://swiss-tech-radar.onrender.com
- Repository: https://github.com/Ancaz20/Swiss-Tech-Radar-Personal-Project
- Developer: Antonio Cazorla González

**Talk track:** I wanted to solve a problem I was facing myself: finding relevant junior technology opportunities in Switzerland is fragmented. I built a small product that brings discovery, evaluation and follow-up into one workflow.

## Slide 2 — The problem and the user

Job listings are scattered and difficult to compare consistently. A title alone does not tell a junior applicant whether the required stack, languages, experience or contract fit.

Swiss Tech Radar helps the user:

1. Discover junior and entry-level technology roles in Switzerland.
2. See the skills and details extracted from each listing.
3. Compare the listing with a configurable profile.
4. Save opportunities and track the next step.

**Product decision:** optimise for a repeatable workflow rather than a one-off search result.

## Slide 3 — End-to-end feature ownership

The project connects several layers:

- **Interface:** multilingual job list, sorting, refresh action, compatibility details and application tracking.
- **Backend:** Flask routes, validation, matching logic and persistence operations.
- **Ingestion:** Adzuna API requests, junior-role filtering, skill extraction and duplicate-safe writes.
- **Data:** SQLite locally and PostgreSQL in the deployed/containerized configuration.
- **Delivery:** Docker, Docker Compose, Render deployment and GitHub Actions.

**Talk track:** I did not stop at displaying API results. I connected ingestion, storage, scoring and the user's follow-up workflow into one application.

## Slide 4 — The data pipeline

```text
Adzuna API
    |
    v
Search terms and query construction
    |
    v
Retry transient provider failures
    |
    v
Filter junior / entry-level roles
    |
    v
Extract skills from title and description
    |
    v
Persist jobs and skill relationships
    |
    +----> CSV export
    |
    v
Flask interface and matching
```

Implementation details:
- Search is focused on Switzerland and configurable search terms.
- Seniority filtering rejects senior-oriented titles and looks for junior/graduate/trainee signals.
- Skill extraction is case-insensitive and avoids duplicate matches.
- Duplicate listings are handled through a unique Adzuna identifier and conflict-safe inserts.
- The API client retries transient HTTP 429 and 5xx responses.

**Honest limitation:** the current refresh path runs the ingestion script as a bounded subprocess from the Flask application. It has a timeout and cooldown, but it is not a dedicated asynchronous worker or distributed queue.

## Slide 5 — Turning messy descriptions into an explainable estimate

The matching heuristic combines four dimensions:

| Dimension | Weight |
| --- | ---: |
| Technical skills | 45% |
| Languages | 25% |
| Experience | 20% |
| Contract type | 10% |

The UI presents the overall estimate, factor breakdown, detected matches and a confidence indicator based on how much of the listing could be interpreted.

**Why this matters:** the user can inspect why a listing appears relevant instead of receiving an unexplained ranking.

**Important:** this is a transparent heuristic, not an AI model and not a prediction of hiring success. Missing information is treated neutrally rather than automatically as a failure.

## Slide 6 — Reliability, security and iteration

Some of the engineering work was less visible than the UI:

- Create the PostgreSQL core tables before dependent application-tracking tables.
- Keep application records when refreshing job listings.
- Protect state-changing form routes with CSRF validation.
- Add a refresh timeout and cooldown to avoid hanging requests and repeated provider calls.
- Retry transient Adzuna errors.
- Redact API credentials from ingestion error details before logging.
- Add unit tests for matching, ingestion, persistence and request validation.
- Run tests and a Docker image build in GitHub Actions.

**Talk track:** I learned that a feature is not finished when the happy path works. It also needs to behave sensibly when data is incomplete, the provider is unavailable or the database starts empty.

## Slide 7 — What transfers to Pedra

| Pedra's environment | Relevant experience from this project |
| --- | --- |
| Own features end-to-end | Connected UI, Flask API, ingestion, data model and deployment |
| Production external services | Integrated Adzuna REST API and handled transient failures |
| Background processing and pipelines | Built a data-ingestion pipeline; next step is a dedicated worker architecture |
| Fast product iteration | Maintained the app, fixed real deployment and database issues, and improved the interface |
| Customer-facing problem solving | Designed around a concrete user workflow and made matching decisions explainable |

The product domain is different, but the engineering habit is similar: understand the user problem, trace it through the whole system, ship a usable change and improve it when real-world conditions expose a weakness.

## Slide 8 — What I want to learn next

I want to apply this end-to-end mindset to Pedra's image editor, virtual staging and video pipeline.

Areas I would actively develop:
- Working with image/video generation APIs and evaluating prompt quality, latency and cost.
- Designing robust background jobs for long-running media operations.
- Learning Pedra's iOS/Swift capture workflow.
- Contributing to its Next.js, React and Tailwind frontend.
- Closing the loop with users by reproducing reports, fixing issues and communicating releases.

I do **not** claim Swiss Tech Radar already implements generative image/video models, Swift/iOS, Next.js or React. These are explicit learning goals.

## Closing — Why this project is worth showing

Swiss Tech Radar is a deployed, inspectable project that demonstrates practical ownership across the stack: external API integration, data processing, backend logic, persistence, user interface, tests and deployment.

**Demo suggestion:** open the live application, refresh or inspect a few listings, show the match breakdown, then save one opportunity and update its application status. Use the repository and this walkthrough to explain the implementation behind each step.

---

### Suggested 60-second video outline

"Hi, I'm Antonio. I'm a software development student and I built Swiss Tech Radar to solve a problem I was experiencing: finding and comparing junior technology roles in Switzerland. The application imports listings from Adzuna, filters junior opportunities, extracts skills, estimates compatibility against a configurable profile and lets users track applications. I built the ingestion pipeline, Flask backend, database integration and interface, and deployed it with Docker and Render. One of the harder parts was making the data pipeline reliable when listings are incomplete, duplicated or the external API temporarily fails. I haven't built image or video generation yet, but I'm excited to bring the same end-to-end approach to Pedra's media pipeline, learn the model-specific trade-offs and work directly on product feedback. Thank you for taking a look."
