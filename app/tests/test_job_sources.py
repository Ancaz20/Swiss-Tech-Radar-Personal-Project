from infrastructure import job_sources


def test_fetch_jobs_ch_parses_results(monkeypatch):
    monkeypatch.setattr(
        job_sources,
        "_fetch_html",
        lambda url, timeout=25: """
            <html><body>
              <ul>
                <li>
                  <a href="/en/vacancies/detail/123/">4 weeks ago Save job Software Engineer Place of work: Langenthal Workload: 80 - 100% Contract type: Permanent position Acme AG Is this job relevant to you?</a>
                  <p>Acme AG, Zurich</p>
                  <p>4 d</p>
                </li>
              </ul>
            </body></html>
        """,
    )

    jobs = job_sources.fetch_jobs_ch(limit=5, query="software engineer")

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Software Engineer"
    assert jobs[0]["company"] == "Acme AG"
    assert jobs[0]["location"] == "Langenthal"


def test_fetch_jobscout24_parses_results(monkeypatch):
    monkeypatch.setattr(
        job_sources,
        "_fetch_html",
        lambda url, timeout=25: """
            <html><body>
              <ul>
                <li>
                  <a href="/en/job/abc123/">Mobile and Web Software Engineer 80 - 100% (m/w/d)</a>
                  <p>Universal-Job AG, St. Gallen</p>
                  <p>1 w</p>
                </li>
              </ul>
            </body></html>
        """,
    )

    jobs = job_sources.fetch_jobscout24(limit=5, query="software engineer")

    assert len(jobs) == 1
    assert jobs[0]["title"].startswith("Mobile and Web Software Engineer")
    assert jobs[0]["company"] == "Universal-Job AG"
    assert jobs[0]["location"] == "St. Gallen"


def test_fetch_eures_filters_tech_jobs(monkeypatch):
    monkeypatch.setattr(
        job_sources,
        "_fetch_json",
        lambda url, payload, timeout=25: {
            "numberRecords": 1,
            "jvs": [
                {
                    "id": "xyz",
                    "title": "Junior Planning Master Data Analyst (temporary)",
                    "description": "Systems analysts",
                    "creationDate": "2026-07-15T10:00:00",
                    "locationMap": {"NO": ["NO021"]},
                    "employer": {"name": "SYSTEM TAK AS"},
                }
            ],
            "facets": {},
        },
    )

    jobs = job_sources.fetch_eures(limit=5, query="data analyst")

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Junior Planning Master Data Analyst (temporary)"
    assert jobs[0]["company"] == "SYSTEM TAK AS"
    assert jobs[0]["location"] == "Norway"


def test_fetch_eures_filters_by_country_terms(monkeypatch):
    monkeypatch.setattr(
        job_sources,
        "_fetch_json",
        lambda url, payload, timeout=25: {
            "numberRecords": 2,
            "jvs": [
                {
                    "id": "de-job",
                    "title": "Senior Softwareentwickler",
                    "description": "Backend platform role",
                    "creationDate": "2026-07-15T10:00:00",
                    "locationMap": {"DE": ["DE9"]},
                    "employer": {"name": "Tech Company GmbH"},
                },
                {
                    "id": "nl-job",
                    "title": "Senior Ontwikkelaar",
                    "description": "Cloud engineering role",
                    "creationDate": "2026-07-15T10:00:00",
                    "locationMap": {"NL": [None]},
                    "employer": {"name": "Tech Company BV"},
                },
            ],
            "facets": {},
        },
    )

    germany_jobs = job_sources.fetch_eures(limit=5, query="software engineer", country_terms=("Germany", "Deutschland"))
    netherlands_jobs = job_sources.fetch_eures(limit=5, query="software engineer", country_terms=("Netherlands", "Nederland"))

    assert len(germany_jobs) == 1
    assert germany_jobs[0]["location"] == "Germany"
    assert len(netherlands_jobs) == 1
    assert netherlands_jobs[0]["location"] == "Netherlands"


def test_fetch_eures_builds_api_payload(monkeypatch):
    requests_seen = []

    def fake_fetch_json(url, payload, timeout=25):
        requests_seen.append((url, payload))
        return {"numberRecords": 0, "jvs": [], "facets": {}}

    monkeypatch.setattr(job_sources, "_fetch_json", fake_fetch_json)
    monkeypatch.setenv("EURES_QUERY", "data analyst")
    monkeypatch.setenv("EURES_LANG", "es")

    jobs = job_sources.fetch_eures(limit=1)

    assert jobs == []
    assert requests_seen == [
        (
            "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search",
            {
                "resultsPerPage": 25,
                "page": 1,
                "sortSearch": "BEST_MATCH",
                "keywords": [{"keyword": "data analyst", "specificSearchCode": "EVERYWHERE"}],
                "publicationPeriod": None,
                "occupationUris": [],
                "skillUris": [],
                "requiredExperienceCodes": [],
                "positionScheduleCodes": [],
                "sectorCodes": [],
                "educationAndQualificationLevelCodes": [],
                "positionOfferingCodes": [],
                "locationCodes": [],
                "euresFlagCodes": [],
                "otherBenefitsCodes": [],
                "requiredLanguages": [],
                "minNumberPost": None,
                "userPreferredLanguage": None,
                "requestLanguage": "es",
                "sessionId": "swiss-tech-radar",
            },
        )
    ]


def test_fetch_jobs_interleaves_multiple_sources(monkeypatch):
    monkeypatch.setattr(job_sources, "fetch_adzuna", lambda limit: [{"title": "A1", "company": "A", "location": "Z", "created": "2026-07-15", "redirect_url": "a1", "skills": [], "contract_type": ""}])
    monkeypatch.setattr(job_sources, "fetch_swissdevjobs", lambda limit: [{"title": "B1", "company": "B", "location": "Z", "created": "2026-07-15", "redirect_url": "b1", "skills": [], "contract_type": ""}])
    monkeypatch.setattr(job_sources, "fetch_jobs_ch", lambda limit: [{"title": "C1", "company": "C", "location": "Z", "created": "2026-07-15", "redirect_url": "c1", "skills": [], "contract_type": ""}])
    monkeypatch.setattr(job_sources, "fetch_jobscout24", lambda limit: [{"title": "D1", "company": "D", "location": "Z", "created": "2026-07-15", "redirect_url": "d1", "skills": [], "contract_type": ""}])
    monkeypatch.setattr(job_sources, "fetch_eures", lambda limit: [{"title": "E1", "company": "E", "location": "Z", "created": "2026-07-15", "redirect_url": "e1", "skills": [], "contract_type": ""}])
    monkeypatch.setattr(job_sources, "fetch_eures_germany", lambda limit: [{"title": "F1", "company": "F", "location": "Z", "created": "2026-07-15", "redirect_url": "f1", "skills": [], "contract_type": ""}])
    monkeypatch.setattr(job_sources, "fetch_eures_netherlands", lambda limit: [{"title": "G1", "company": "G", "location": "Z", "created": "2026-07-15", "redirect_url": "g1", "skills": [], "contract_type": ""}])

    jobs = job_sources.fetch_jobs(limit=5)

    assert [job["title"] for job in jobs] == ["A1", "B1", "C1", "D1", "E1"]


def test_fetch_swissdevjobs_parses_rss(monkeypatch):
    monkeypatch.setattr(
        job_sources,
        "_fetch_html",
        lambda url, timeout=25: """
            <rss><channel>
              <item>
                <title>Senior Platform Engineer (80%-100%) @ ONZACK AG [CHF 115'000 - 130'000]</title>
                <link>https://swissdevjobs.ch/jobs/onzack-platform-engineer</link>
                <pubDate>Wed, 01 Jul 2026 12:50:06 GMT</pubDate>
                <description><![CDATA[<p><b>Salary: CHF 115'000 - 130'000 per year</b></p><b>Requirements:</b><ul><li>Python</li></ul>]]></description>
              </item>
            </channel></rss>
        """,
    )

    jobs = job_sources.fetch_swissdevjobs(limit=5)

    assert len(jobs) == 1
    assert jobs[0]["title"] == "Senior Platform Engineer (80%-100%)"
    assert jobs[0]["company"] == "ONZACK AG"
    assert jobs[0]["salary_min"] == 115000.0
    assert jobs[0]["salary_max"] == 130000.0
