import os
import re
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup


TECH_KEYWORDS = (
    "software",
    "developer",
    "engineer",
    "entwickler",
    "ontwikkelaar",
    "softwareentwickler",
    "software-entwickler",
    "ingenieur",
    "informatiker",
    "data",
    "devops",
    "frontend",
    "backend",
    "fullstack",
    "full stack",
    "python",
    "java",
    "cloud",
    "system",
    "it",
    "ai",
)

EURES_COUNTRY_NAMES = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "CH": "Switzerland",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DE": "Germany",
    "DK": "Denmark",
    "EE": "Estonia",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GR": "Greece",
    "HR": "Croatia",
    "HU": "Hungary",
    "IE": "Ireland",
    "IS": "Iceland",
    "IT": "Italy",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MT": "Malta",
    "NL": "Netherlands",
    "NO": "Norway",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SE": "Sweden",
    "SI": "Slovenia",
    "SK": "Slovakia",
}


@dataclass(frozen=True)
class SourceJob:
    title: str
    company: str
    location: str
    created: str
    redirect_url: str
    contract_type: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    skills: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "created": self.created,
            "redirect_url": self.redirect_url,
            "contract_type": self.contract_type,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "skills": self.skills or [],
        }


FALLBACK_JOBS = [
    SourceJob(
        title="Junior Python Developer",
        company="SwissTech Labs",
        location="Zurich",
        created="2026-07-15",
        redirect_url="https://example.com/jobs/1",
        contract_type="Permanent",
        salary_min=70000,
        salary_max=90000,
        skills=["Python", "Flask", "SQL"],
    ),
    SourceJob(
        title="Junior Data Engineer",
        company="DataFlow AG",
        location="Geneva",
        created="2026-07-14",
        redirect_url="https://example.com/jobs/2",
        contract_type="Permanent",
        salary_min=75000,
        salary_max=95000,
        skills=["SQL", "Python", "ETL"],
    ),
    SourceJob(
        title="Frontend Developer Junior",
        company="Cloud Swiss",
        location="Lausanne",
        created="2026-07-13",
        redirect_url="https://example.com/jobs/3",
        contract_type="Contract",
        salary_min=68000,
        salary_max=86000,
        skills=["JavaScript", "React", "HTML"],
    ),
]


def _today() -> str:
    return date.today().isoformat()


def _fetch_html(url: str, timeout: int = 25) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="ignore")


def _fetch_json(url: str, payload: dict[str, Any], timeout: int = 25) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://europa.eu",
            "Referer": "https://europa.eu/eures/portal/jv-se/search?lang=en",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset, errors="ignore"))


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _is_tech_job(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in TECH_KEYWORDS)


def _parse_relative_date(label: str) -> str:
    lowered = label.lower().strip()
    today = date.today()

    if lowered in {"today", "just now", "now"}:
        return today.isoformat()
    if "yesterday" in lowered:
        return (today - timedelta(days=1)).isoformat()

    week_match = re.search(r"(\d+)\s*(?:w|week|weeks)", lowered)
    day_match = re.search(r"(\d+)\s*(?:d|day|days)", lowered)
    hour_match = re.search(r"(\d+)\s*(?:h|hour|hours)", lowered)
    month_match = re.search(r"(\d+)\s*(?:m|month|months)", lowered)

    if week_match:
        return (today - timedelta(weeks=int(week_match.group(1)))).isoformat()
    if day_match:
        return (today - timedelta(days=int(day_match.group(1)))).isoformat()
    if hour_match:
        return today.isoformat()
    if month_match:
        return (today - timedelta(days=30 * int(month_match.group(1)))).isoformat()

    if re.search(r"\d{1,2}/\d{1,2}/\d{4}", lowered):
        return lowered

    return today.isoformat()


def _deduplicate_jobs(jobs: list[SourceJob]) -> list[SourceJob]:
    seen: set[tuple[str, str, str, str]] = set()
    unique_jobs: list[SourceJob] = []

    for job in jobs:
        key = (
            job.title.lower(),
            job.company.lower(),
            job.location.lower(),
            job.redirect_url,
        )
        if key in seen:
            continue
        seen.add(key)
        unique_jobs.append(job)
    return unique_jobs


def _extract_company_location(text_block: str, separator: str = ",") -> tuple[str, str]:
    normalized = _normalize_text(text_block)
    if separator in normalized:
        company, location = normalized.split(separator, 1)
        return company.strip(), location.strip()
    return normalized or "Unknown", "Switzerland"


def _build_job(
    title: str,
    company: str,
    location: str,
    redirect_url: str,
    created: str | None = None,
    skills: list[str] | None = None,
    contract_type: str = "Permanent",
) -> SourceJob:
    return SourceJob(
        title=_normalize_text(title) or "Untitled role",
        company=_normalize_text(company) or "Unknown",
        location=_normalize_text(location) or "Switzerland",
        created=created or _today(),
        redirect_url=redirect_url,
        contract_type=contract_type,
        skills=skills or [],
    )


def _collect_from_anchors(soup: BeautifulSoup, href_fragment: str) -> list[Any]:
    return [anchor for anchor in soup.find_all("a", href=True) if href_fragment in anchor["href"]]


def _matches_any_term(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _build_eures_payload(query: str, language: str, location_codes: list[str] | None = None) -> dict[str, Any]:
    payload = {
        "resultsPerPage": 25,
        "page": 1,
        "sortSearch": "BEST_MATCH",
        "keywords": [],
        "publicationPeriod": None,
        "occupationUris": [],
        "skillUris": [],
        "requiredExperienceCodes": [],
        "positionScheduleCodes": [],
        "sectorCodes": [],
        "educationAndQualificationLevelCodes": [],
        "positionOfferingCodes": [],
        "locationCodes": location_codes or [],
        "euresFlagCodes": [],
        "otherBenefitsCodes": [],
        "requiredLanguages": [],
        "minNumberPost": None,
        "userPreferredLanguage": None,
        "requestLanguage": language,
        "sessionId": "swiss-tech-radar",
    }
    if query:
        payload["keywords"] = [{"keyword": query, "specificSearchCode": "EVERYWHERE"}]
    return payload


def _format_eures_location(location_map: dict[str, list[str] | None] | None) -> str:
    if not location_map:
        return "Europe"

    country_codes = [country_code for country_code in location_map.keys() if country_code]
    if not country_codes:
        return "Europe"

    labels = [EURES_COUNTRY_NAMES.get(country_code, country_code) for country_code in country_codes]
    return ", ".join(labels)


def _normalize_eures_created(value: Any) -> str:
    text = _normalize_text(str(value or ""))
    if not text:
        return _today()
    if text.isdigit():
        try:
            return datetime.fromtimestamp(int(text) / 1000, tz=timezone.utc).date().isoformat()
        except (OverflowError, ValueError):
            return _today()
    return text.split("T", 1)[0]


def fetch_swissdevjobs(limit: int = 10) -> list[dict[str, Any]]:
    rss = _fetch_html("https://swissdevjobs.ch/rss")
    root = ET.fromstring(rss)
    jobs: list[SourceJob] = []

    for item in root.findall("./channel/item"):
        raw_title = _normalize_text(item.findtext("title", default=""))
        if not raw_title:
            continue

        title = raw_title
        company = "SwissDevJobs"
        salary_min = None
        salary_max = None
        title_match = re.match(r"^(?P<title>.+?)\s*@\s*(?P<company>.+?)\s*(?:\[(?P<salary>.+)\])?$", raw_title)
        if title_match:
            title = title_match.group("title").strip()
            company = title_match.group("company").strip()
            salary_text = (title_match.group("salary") or "").strip()
            salary_match = re.search(r"CHF\s*([\d' ]+)\s*-\s*([\d' ]+)", salary_text)
            if salary_match:
                salary_min = float(salary_match.group(1).replace("'", "").replace(" ", ""))
                salary_max = float(salary_match.group(2).replace("'", "").replace(" ", ""))

        description = item.findtext("description", default="")
        if not _is_tech_job(title + " " + description):
            continue

        skills = [keyword.title() for keyword in TECH_KEYWORDS if keyword in (title + " " + description).lower()][:3]
        jobs.append(
            SourceJob(
                title=title,
                company=company,
                location="Switzerland",
                created=_normalize_text(item.findtext("pubDate", default="")) or _today(),
                redirect_url=_normalize_text(item.findtext("link", default="")),
                contract_type="Permanent",
                salary_min=salary_min,
                salary_max=salary_max,
                skills=skills,
            )
        )
        if len(jobs) >= limit:
            break

    return [job.to_dict() for job in _deduplicate_jobs(jobs)]


def fetch_jobs_ch(limit: int = 10, query: str | None = None) -> list[dict[str, Any]]:
    query = (query or os.environ.get("JOBS_CH_QUERY", "software engineer")).strip() or "software engineer"
    url = f"https://www.jobs.ch/en/vacancies/?{urlencode({'term': query})}"
    soup = BeautifulSoup(_fetch_html(url), "html.parser")
    jobs: list[SourceJob] = []

    for anchor in soup.find_all("a", href=re.compile(r"/en/vacancies/detail/")):
        card_text = _normalize_text(anchor.get_text(" ", strip=True))
        title = _normalize_text(anchor.get("title") or "")
        title_match = re.search(r"(?:.*?Save job\s+)?(.+?)\s+Place of work:", card_text)
        if not title:
            title = _normalize_text(title_match.group(1) if title_match else card_text)
        if not title or not _is_tech_job(title):
            continue

        container = anchor.find_parent("li") or anchor.find_parent("article") or anchor.parent
        container_text = _normalize_text(container.get_text(" ", strip=True) if container else card_text)
        company_match = re.search(r"position\s+(.+?)\s+(?:New\s+)?Is this job relevant to you\?", card_text)
        company = _normalize_text(company_match.group(1)) if company_match else "jobs.ch"

        location_match = re.search(r"Place of work\s*:\s*(.+?)\s+Workload\s*:", card_text)
        location = _normalize_text(location_match.group(1)) if location_match else "Switzerland"

        created_match = re.search(r"^(Yesterday|\d+\s+(?:minutes?|hours?|days?|weeks?|months?)\s+ago|\d+\s*[dwmh])", card_text, re.I)
        created = _parse_relative_date(created_match.group(1)) if created_match else _today()

        skills = [keyword.title() for keyword in TECH_KEYWORDS if keyword in container_text.lower()][:3]
        jobs.append(_build_job(title, company, location, urljoin("https://www.jobs.ch", anchor["href"]), created=created, skills=skills))
        if len(jobs) >= limit:
            break

    return [job.to_dict() for job in _deduplicate_jobs(jobs)]


def fetch_jobscout24(limit: int = 10, query: str | None = None) -> list[dict[str, Any]]:
    query = (query or os.environ.get("JOBSCOUT24_QUERY", "software engineer")).strip() or "software engineer"
    url = f"https://www.jobscout24.ch/en/jobs/?{urlencode({'ft': query})}"
    soup = BeautifulSoup(_fetch_html(url), "html.parser")
    jobs: list[SourceJob] = []

    for anchor in soup.find_all("a", href=re.compile(r"/en/job/")):
        title = _normalize_text(anchor.get_text(" ", strip=True))
        if not title or not _is_tech_job(title):
            continue

        container = anchor.find_parent("li") or anchor.find_parent("article") or anchor.parent
        container_text = _normalize_text(container.get_text(" ", strip=True) if container else title)
        company = "JobScout24"
        location = "Switzerland"
        paragraphs = container.find_all("p") if container else []
        if paragraphs:
            company, location = _extract_company_location(paragraphs[0].get_text(" ", strip=True))
        created = _today()
        for paragraph in reversed(paragraphs):
            label = _normalize_text(paragraph.get_text(" ", strip=True))
            if re.search(r"\d+\s*[dwmh]", label.lower()) or "yesterday" in label.lower():
                created = _parse_relative_date(label)
                break

        skills = [keyword.title() for keyword in TECH_KEYWORDS if keyword in container_text.lower()][:3]
        jobs.append(_build_job(title, company, location, urljoin("https://www.jobscout24.ch", anchor["href"]), created=created, skills=skills))
        if len(jobs) >= limit:
            break

    return [job.to_dict() for job in _deduplicate_jobs(jobs)]


def fetch_eures(
    limit: int = 10,
    query: str | None = None,
    country_terms: tuple[str, ...] = (),
    location_codes: list[str] | None = None,
) -> list[dict[str, Any]]:
    query = (query or os.environ.get("EURES_QUERY", "software engineer")).strip() or "software engineer"
    language = os.environ.get("EURES_LANG", "en").strip() or "en"
    api_url = os.environ.get("EURES_API_URL", "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search").strip()
    payload = _build_eures_payload(query, language, location_codes)
    response = _fetch_json(api_url, payload)
    jobs: list[SourceJob] = []

    for item in response.get("jvs", []) if isinstance(response, dict) else []:
        title = _normalize_text(str(item.get("title") or ""))
        if not title or not _is_tech_job(title):
            continue

        description = _normalize_text(BeautifulSoup(str(item.get("description") or ""), "html.parser").get_text(" ", strip=True))
        if description and not _is_tech_job(f"{title} {description}"):
            continue

        company = _normalize_text(str((item.get("employer") or {}).get("name") or "EURES"))
        location = _format_eures_location(item.get("locationMap"))
        created = _normalize_eures_created(item.get("creationDate"))

        if country_terms and not _matches_any_term(location, country_terms):
            continue

        normalized_text = _normalize_text(f"{title} {description}")
        skills = [keyword.title() for keyword in TECH_KEYWORDS if keyword in normalized_text.lower()][:3]
        details_language = language if language in {"en", "de", "fr", "es", "it", "nl"} else "en"
        redirect_url = f"https://europa.eu/eures/portal/jv-se/jv-details/{item.get('id')}?jvDisplayLanguage={details_language}"
        jobs.append(_build_job(title, company, location, redirect_url, created=created, skills=skills))
        if len(jobs) >= limit:
            break

    return [job.to_dict() for job in _deduplicate_jobs(jobs)]


def fetch_eures_germany(limit: int = 10) -> list[dict[str, Any]]:
    return fetch_eures(limit=limit, country_terms=("Germany", "Deutschland"), location_codes=["de"])


def fetch_eures_netherlands(limit: int = 10) -> list[dict[str, Any]]:
    return fetch_eures(limit=limit, country_terms=("Netherlands", "Nederland", "The Netherlands", "Holland"), location_codes=["nl"])


def fetch_adzuna(limit: int = 10) -> list[dict[str, Any]]:
    app_id = os.environ.get("ADZUNA_APP_ID", "").strip()
    app_key = os.environ.get("ADZUNA_APP_KEY", "").strip()

    if not app_id or not app_key:
        return []

    query = os.environ.get("ADZUNA_WHAT", "junior developer").strip() or "junior developer"
    where = os.environ.get("ADZUNA_WHERE", "Switzerland").strip() or "Switzerland"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": str(limit),
        "what": query,
        "where": where,
    }
    url = "https://api.adzuna.com/v1/api/jobs/ch/search/1?" + urlencode(params)

    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=20) as response:
            import json

            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError):
        return []

    jobs: list[SourceJob] = []
    for item in payload.get("results", []) if isinstance(payload, dict) else []:
        title = item.get("title") or "Untitled role"
        company = item.get("company", {}).get("display_name") or "Unknown"
        location = item.get("location", {}).get("display_name") or "Switzerland"
        created = item.get("created") or _today()
        redirect_url = item.get("redirect_url") or ""
        skills = [skill.get("label", "") for skill in item.get("skills", []) if skill.get("label")]
        jobs.append(
            _build_job(
                title,
                company,
                location,
                redirect_url,
                created=created,
                skills=skills,
                contract_type=item.get("contract_type") or "",
            )
        )

    return [job.to_dict() for job in _deduplicate_jobs(jobs)]


def fetch_jobs(limit: int = 20) -> list[dict[str, Any]]:
    source_jobs: list[list[dict[str, Any]]] = []
    source_fetchers: list[Callable[[int], list[dict[str, Any]]]] = [
        fetch_adzuna,
        fetch_swissdevjobs,
        fetch_jobs_ch,
        fetch_jobscout24,
        fetch_eures,
        fetch_eures_germany,
        fetch_eures_netherlands,
    ]

    per_source_limit = max(1, (limit + len(source_fetchers) - 1) // len(source_fetchers))

    for fetcher in source_fetchers:
        try:
            source_jobs.append(fetcher(per_source_limit))
        except Exception:
            source_jobs.append([])

    collected: list[dict[str, Any]] = []
    max_length = max((len(items) for items in source_jobs), default=0)
    for index in range(max_length):
        for jobs in source_jobs:
            if index < len(jobs):
                collected.append(jobs[index])

    unique_jobs = _deduplicate_jobs(
        [
            SourceJob(
                title=job["title"],
                company=job["company"],
                location=job["location"],
                created=job["created"],
                redirect_url=job["redirect_url"],
                contract_type=job.get("contract_type", ""),
                salary_min=job.get("salary_min"),
                salary_max=job.get("salary_max"),
                skills=job.get("skills") or [],
            )
            for job in collected
        ]
    )

    if not unique_jobs:
        return [job.to_dict() for job in FALLBACK_JOBS[:limit]]

    return [job.to_dict() for job in unique_jobs[:limit]]
