import os
import hmac
import secrets
import sqlite3
import psycopg2
import subprocess
import sys
import time
import re
from flask import Flask, render_template, redirect, url_for, flash, request, session

app = Flask(__name__)

_secret_key = os.environ.get("FLASK_SECRET_KEY")
_is_production = os.environ.get("FLASK_ENV", "").lower() == "production"
if not _secret_key:
    if not _is_production:
        # Permite arrancar en desarrollo local sin definir la clave.
        _secret_key = "dev_secret_key"
    else:
        raise RuntimeError(
            "FLASK_SECRET_KEY no está definida. Establece esta variable de entorno "
            "antes de arrancar la app en producción."
        )
app.secret_key = _secret_key

ROOT_DIR = os.environ.get("PROJECT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(ROOT_DIR, "swiss_tech_radar.db")
INGEST_SCRIPT = os.path.join(ROOT_DIR, "ingest.py")
REFRESH_TIMEOUT_SECONDS = 120  # evita que un ingest colgado bloquee la app para siempre
REFRESH_MIN_INTERVAL_SECONDS = 60  # evita refrescos repetidos que agoten la cuota de Adzuna

_last_refresh_at = 0.0

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "fr": "Français",
}
DEFAULT_LANG = "es"
SUPPORTED_SORTS = {"date", "location", "company", "skills"}
DEFAULT_SORT = "date"

TRANSLATIONS = {
    "en": {
        "page_title": "Swiss Tech Radar",
        "hero_title": "Junior tech jobs in Switzerland",
        "hero_subtitle": "View and refresh saved offers from Adzuna with one click. This interface shows the most relevant data clearly and simply.",
        "refresh_button": "Refresh offers",
        "refresh_note": "Press refresh to reimport the latest junior positions. The button uses POST to prevent accidental reloads.",
        "summary_title": "Quick summary",
        "summary_item1": "Shows up to 200 recent offers",
        "summary_item2": "See title, company, location and skills",
        "summary_item3": "Open each offer directly on Adzuna",
        "show_offers_title": "Offer list",
        "show_offers_note": "Click \"View\" to go to the original posting.",
        "offers_count": "{count} offers",
        "no_jobs_message": "No offers available. Press \"Refresh offers\" to load the latest jobs.",
        "skills_none": "No skills",
        "view_label": "View",
        "translate_label": "Translate",
        "no_link": "No link",
        "language_label": "Language",
        "alert_refresh_success": "Offers updated successfully.",
        "alert_refresh_error": "Error updating offers: {message}",
        "alert_refresh_rate_limited": "Please wait a moment before refreshing again ({seconds}s left).",
        "title_label": "Title",
        "company_label": "Company",
        "location_label": "Location",
        "skills_label": "Skills",
        "published_label": "Posted",
        "actions_label": "Actions",
        "sort_label": "Sort by",
        "sort_date_label": "Published",
        "sort_location_label": "Location",
        "sort_company_label": "Company",
        "sort_skills_label": "Shared skills",
    },
    "es": {
        "page_title": "Radar Tecnológico Suiza",
        "hero_title": "Ofertas junior de tecnología en Suiza",
        "hero_subtitle": "Visualiza y actualiza las ofertas guardadas desde Adzuna con un clic. Esta interfaz está pensada para mostrar los datos más relevantes de forma clara y sencilla.",
        "refresh_button": "Actualizar ofertas",
        "refresh_note": "Pulsa actualizar para reimportar los últimos puestos junior. El botón utiliza POST para evitar recargas accidentales.",
        "summary_title": "Resumen rápido",
        "summary_item1": "Muestra hasta 200 ofertas recientes",
        "summary_item2": "Consulta títulos, empresa, ubicación y habilidades",
        "summary_item3": "Abre cada oferta directamente en Adzuna",
        "show_offers_title": "Listado de ofertas",
        "show_offers_note": "Haz clic en \"Ver\" para ir al anuncio original.",
        "offers_count": "{count} ofertas",
        "no_jobs_message": "No hay ofertas disponibles. Pulsa \"Actualizar ofertas\" para cargar los últimos puestos.",
        "skills_none": "Sin skills",
        "view_label": "Ver",
        "translate_label": "Traducir",
        "no_link": "Sin enlace",
        "language_label": "Idioma",
        "alert_refresh_success": "Ofertas actualizadas correctamente.",
        "alert_refresh_error": "Error al actualizar ofertas: {message}",
        "alert_refresh_rate_limited": "Espera un momento antes de actualizar de nuevo ({seconds}s restantes).",
        "title_label": "Título",
        "company_label": "Empresa",
        "location_label": "Ubicación",
        "skills_label": "Habilidades",
        "published_label": "Publicada",
        "actions_label": "Acciones",
        "sort_label": "Ordenar por",
        "sort_date_label": "Publicación",
        "sort_location_label": "Ubicación",
        "sort_company_label": "Empresa",
        "sort_skills_label": "Skills en común",
    },
    "de": {
        "page_title": "Swiss Tech Radar",
        "hero_title": "Junior-Tech-Jobs in der Schweiz",
        "hero_subtitle": "Zeige und aktualisiere gespeicherte Angebote von Adzuna mit einem Klick. Diese Oberfläche zeigt die wichtigsten Daten klar und einfach.",
        "refresh_button": "Angebote aktualisieren",
        "refresh_note": "Drücke Aktualisieren, um die neuesten Junior-Positionen erneut zu importieren. Der Button verwendet POST, um versehentliche Neuladungen zu vermeiden.",
        "summary_title": "Kurzüberblick",
        "summary_item1": "Zeigt bis zu 200 aktuelle Angebote",
        "summary_item2": "Sieh Titel, Firma, Ort und Fähigkeiten",
        "summary_item3": "Öffne jedes Angebot direkt auf Adzuna",
        "show_offers_title": "Angebotsliste",
        "show_offers_note": "Klicke auf \"Ansehen\" um zur Originalanzeige zu gelangen.",
        "offers_count": "{count} Angebote",
        "no_jobs_message": "Keine Angebote verfügbar. Drücke \"Angebote aktualisieren\" um die neuesten Positionen zu laden.",
        "skills_none": "Keine Skills",
        "view_label": "Ansehen",
        "translate_label": "Übersetzen",
        "no_link": "Kein Link",
        "language_label": "Sprache",
        "alert_refresh_success": "Angebote erfolgreich aktualisiert.",
        "alert_refresh_error": "Fehler beim Aktualisieren der Angebote: {message}",
        "alert_refresh_rate_limited": "Bitte warte einen Moment, bevor du erneut aktualisierst ({seconds}s verbleibend).",
        "title_label": "Titel",
        "company_label": "Firma",
        "location_label": "Ort",
        "skills_label": "Fähigkeiten",
        "published_label": "Veröffentlicht",
        "actions_label": "Aktion",
        "sort_label": "Sortieren nach",
        "sort_date_label": "Veröffentlicht",
        "sort_location_label": "Ort",
        "sort_company_label": "Firma",
        "sort_skills_label": "Gemeinsame Skills",
    },
    "fr": {
        "page_title": "Swiss Tech Radar",
        "hero_title": "Offres junior tech en Suisse",
        "hero_subtitle": "Affichez et actualisez les offres enregistrées depuis Adzuna en un clic. Cette interface présente les données les plus importantes de façon claire et simple.",
        "refresh_button": "Actualiser les offres",
        "refresh_note": "Cliquez sur actualiser pour réimporter les dernières offres junior. Le bouton utilise POST pour éviter les rechargements accidentels.",
        "summary_title": "Résumé rapide",
        "summary_item1": "Affiche jusqu'à 200 offres récentes",
        "summary_item2": "Consultez le titre, l'entreprise, le lieu et les compétences",
        "summary_item3": "Ouvrez chaque offre directement sur Adzuna",
        "show_offers_title": "Liste des offres",
        "show_offers_note": "Cliquez sur \"Voir\" pour accéder à l'annonce originale.",
        "offers_count": "{count} offres",
        "no_jobs_message": "Aucune offre disponible. Cliquez sur \"Actualiser les offres\" pour charger les dernières positions.",
        "skills_none": "Pas de compétences",
        "view_label": "Voir",
        "translate_label": "Traduire",
        "no_link": "Pas de lien",
        "language_label": "Langue",
        "alert_refresh_success": "Offres mises à jour avec succès.",
        "alert_refresh_error": "Erreur lors de la mise à jour des offres : {message}",
        "alert_refresh_rate_limited": "Veuillez patienter avant d'actualiser à nouveau ({seconds}s restantes).",
        "title_label": "Titre",
        "company_label": "Entreprise",
        "location_label": "Localisation",
        "skills_label": "Compétences",
        "published_label": "Publié",
        "actions_label": "Actions",
        "sort_label": "Trier par",
        "sort_date_label": "Publication",
        "sort_location_label": "Lieu",
        "sort_company_label": "Entreprise",
        "sort_skills_label": "Compétences partagées",
    },
}


def get_locale():
    lang = request.values.get("lang", DEFAULT_LANG)
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANG


def get_sort():
    sort = request.values.get("sort", DEFAULT_SORT)
    return sort if sort in SUPPORTED_SORTS else DEFAULT_SORT


def get_translations(lang):
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])


APPLICATION_STATUSES = {
    "saved": "Guardada",
    "applied": "Solicitada",
    "interview": "Entrevista",
    "offer": "Oferta recibida",
    "rejected": "Descartada",
    "archived": "Archivada",
}
DEFAULT_PROFILE_SKILLS = "java,spring,python,sql,postgresql,docker,aws,azure,typescript,react,git"


def get_profile_skills():
    configured = os.environ.get("PROFILE_SKILLS", DEFAULT_PROFILE_SKILLS)
    return {skill.strip().lower() for skill in configured.split(",") if skill.strip()}


def calculate_match_score(job_skills, profile_skills=None):
    """Backward-compatible skill-only score helper."""
    if isinstance(job_skills, str):
        skills = {item.strip().lower() for item in job_skills.split(",") if item.strip()}
    else:
        skills = {str(item).strip().lower() for item in (job_skills or []) if str(item).strip()}
    profile = profile_skills if profile_skills is not None else get_profile_skills()
    profile = {str(item).strip().lower() for item in profile if str(item).strip()}
    matched = sorted(skills & profile)
    if not skills or not profile:
        return 0, matched
    denominator = max(3, min(6, len(skills)))
    return min(100, round(len(matched) * 100 / denominator)), matched


LEVEL_RANK = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6, "NATIVE": 7}
LANGUAGE_ALIASES = {
    "english": ("english", "anglais", "englisch"),
    "french": ("french", "français", "francais", "französisch", "franzosisch"),
    "german": ("german", "deutsch", "allemand"),
    "spanish": ("spanish", "español", "espanol", "spanisch"),
    "italian": ("italian", "italien", "italienisch"),
}
DEFAULT_PROFILE_LANGUAGES = "spanish:native,english:C1,french:B1,german:A1"
DEFAULT_TARGET_CONTRACTS = {"internship", "permanent", "temporary", "part-time"}


def get_profile_languages():
    configured = os.environ.get("PROFILE_LANGUAGES", DEFAULT_PROFILE_LANGUAGES)
    result = {}
    for item in configured.split(","):
        if ":" not in item:
            continue
        language, level = item.split(":", 1)
        language = language.strip().lower()
        level = level.strip().upper()
        if language and level in LEVEL_RANK:
            result[language] = level
    return result


def get_profile_experience_years():
    try:
        return max(0, float(os.environ.get("PROFILE_EXPERIENCE_YEARS", "0")))
    except ValueError:
        return 0.0


def detect_language_requirements(text):
    lowered = (text or "").lower()
    requirements = {}
    for language, aliases in LANGUAGE_ALIASES.items():
        for alias in aliases:
            escaped = re.escape(alias)
            patterns = (
                rf"\b{escaped}\b[^.;\n]{{0,35}}\b(a[12]|b[12]|c[12]|native)\b",
                rf"\b(a[12]|b[12]|c[12]|native)\b[^.;\n]{{0,25}}\b{escaped}\b",
            )
            for pattern in patterns:
                match = re.search(pattern, lowered, re.IGNORECASE)
                if match:
                    level = match.group(1).upper()
                    requirements[language] = level
                    break
            if language in requirements:
                break
    return requirements


def calculate_language_score(text):
    requirements = detect_language_requirements(text)
    profile = get_profile_languages()
    if not requirements:
        return 75, [], False
    details = []
    scores = []
    for language, required_level in requirements.items():
        actual = profile.get(language)
        if actual is None:
            score = 0
            detail = f"{language}: no indicado en tu perfil (se exige {required_level})"
        else:
            gap = LEVEL_RANK[required_level] - LEVEL_RANK[actual]
            score = 100 if gap <= 0 else max(0, 100 - gap * 35)
            detail = f"{language}: tu nivel {actual}, requisito {required_level}"
        scores.append(score)
        details.append(detail)
    return round(sum(scores) / len(scores)), details, True


def calculate_experience_score(job):
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    profile_years = get_profile_experience_years()
    years = [float(value) for value in re.findall(
        r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b", text
    )]
    if years:
        required = min(years)
        score = 100 if required <= profile_years else max(0, 100 - (required - profile_years) * 30)
        return round(score), f"Experiencia solicitada: {required:g} años; perfil configurado: {profile_years:g}", True
    title = (job.get("title") or "").lower()
    if re.search(r"\b(senior|principal|staff engineer|lead engineer|head of)\b", title):
        return 10, "El título parece orientado a un perfil senior", True
    if re.search(r"\b(intern|internship|praktikum|stage|trainee|graduate|junior|entry.level|apprentice)\b", text):
        return 100, "El anuncio menciona prácticas o nivel inicial", True
    if re.search(r"\b(mid.level|intermediate)\b", text):
        return 45, "El anuncio parece de nivel intermedio", True
    return 75, "El anuncio no especifica claramente la experiencia", False


def calculate_contract_score(job):
    contract = (job.get("contract_type") or "").lower()
    text = f"{job.get('title', '')} {job.get('description', '')} {contract}".lower()
    if re.search(r"\b(internship|intern|praktikum|stage|trainee|apprenticeship|apprentice)\b", text):
        return 100, "Prácticas o formación remunerada identificadas", True
    if re.search(r"\b(freelance|self.employed|independent contractor)\b", text):
        return 35, "Modalidad freelance: menor prioridad en el perfil actual", True
    if re.search(r"\b(part.time|part time|temps partiel|teilzeit)\b", text):
        return 90, "Jornada parcial identificada", True
    if re.search(r"\b(temporary|fixed.term|fixed term|temporaire|befristet)\b", text):
        return 80, "Contrato temporal identificado", True
    if re.search(r"\b(permanent|full.time|full time|cdi|unbefristet)\b", text):
        return 85, "Contrato estable o jornada completa identificados", True
    return 75, "El anuncio no especifica claramente el tipo de contrato", False


def calculate_job_match(job):
    """Weighted fit estimate: skills 45%, languages 25%, experience 20%, contract 10%."""
    skills_score, matched = calculate_match_score(job.get("skills", ""))
    text = f"{job.get('title', '')} {job.get('description', '')}"
    language_score, language_notes, language_known = calculate_language_score(text)
    experience_score, experience_note, experience_known = calculate_experience_score(job)
    contract_score, contract_note, contract_known = calculate_contract_score(job)
    weighted = (
        skills_score * 0.45
        + language_score * 0.25
        + experience_score * 0.20
        + contract_score * 0.10
    )
    known = sum((bool(job.get("skills")), language_known, experience_known, contract_known))
    return {
        "score": round(weighted),
        "matched_skills": matched,
        "breakdown": {
            "skills": skills_score,
            "languages": language_score,
            "experience": experience_score,
            "contract": contract_score,
        },
        "details": {
            "skills": ", ".join(matched) if matched else "No se detectan coincidencias tecnológicas",
            "languages": "; ".join(language_notes) if language_notes else "No se detecta un nivel lingüístico exigido",
            "experience": experience_note,
            "contract": contract_note,
        },
        "confidence": round(known / 4 * 100),
    }


def ensure_applications_table(conn, is_postgres):
    sql = """
        CREATE TABLE IF NOT EXISTS applications (
            job_id INTEGER PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK (
                status IN ('saved', 'applied', 'interview', 'offer', 'rejected', 'archived')
            ),
            notes TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            applied_at TIMESTAMP NULL
        )
    """
    if is_postgres:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        cur.close()
    else:
        conn.execute(sql)
        conn.commit()


def get_app_database():
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        conn = psycopg2.connect(database_url)
        ensure_applications_table(conn, True)
        return conn, True
    if not os.path.exists(DB_PATH):
        return None, False
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_applications_table(conn, False)
    return conn, False


def save_application(job_id, status="saved", notes=""):
    if status not in APPLICATION_STATUSES:
        raise ValueError("Estado de candidatura no válido.")
    notes = (notes or "").strip()
    if len(notes) > 4000:
        raise ValueError("Las notas no pueden superar los 4000 caracteres.")
    conn, is_postgres = get_app_database()
    if conn is None:
        raise LookupError("No existe todavía una base de datos con ofertas.")
    try:
        if is_postgres:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO applications (job_id, status, notes, applied_at)
                SELECT id, %s, %s, CASE WHEN %s = 'applied' THEN CURRENT_TIMESTAMP ELSE NULL END
                FROM jobs WHERE id = %s
                ON CONFLICT (job_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    notes = EXCLUDED.notes,
                    updated_at = CURRENT_TIMESTAMP,
                    applied_at = COALESCE(
                        applications.applied_at,
                        CASE WHEN EXCLUDED.status = 'applied' THEN CURRENT_TIMESTAMP ELSE NULL END
                    )
                RETURNING job_id
            """, (status, notes, status, job_id))
            result = cur.fetchone()
            conn.commit()
            cur.close()
        else:
            cur = conn.execute("""
                INSERT INTO applications (job_id, status, notes, applied_at)
                SELECT id, ?, ?, CASE WHEN ? = 'applied' THEN CURRENT_TIMESTAMP ELSE NULL END
                FROM jobs WHERE id = ?
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP,
                    applied_at = COALESCE(
                        applications.applied_at,
                        CASE WHEN excluded.status = 'applied' THEN CURRENT_TIMESTAMP ELSE NULL END
                    )
            """, (status, notes, status, job_id))
            result = cur.rowcount
            conn.commit()
        if not result:
            raise LookupError("La oferta ya no existe.")
    finally:
        conn.close()


def load_applications(status_filter=None):
    conn, is_postgres = get_app_database()
    if conn is None:
        return []
    try:
        placeholder = "%s" if is_postgres else "?"
        aggregate = "STRING_AGG(skills.name, ', ')" if is_postgres else "GROUP_CONCAT(skills.name, ', ')"
        sql = f"""
            SELECT jobs.id AS job_id, jobs.title, jobs.company, jobs.location,
                   jobs.redirect_url, jobs.created, jobs.contract_type, jobs.description, applications.status,
                   applications.notes, applications.created_at,
                   applications.updated_at, applications.applied_at,
                   COALESCE({aggregate}, '') AS skills
            FROM applications
            JOIN jobs ON jobs.id = applications.job_id
            LEFT JOIN job_skills ON job_skills.job_id = jobs.id
            LEFT JOIN skills ON skills.id = job_skills.skill_id
        """
        params = ()
        if status_filter in APPLICATION_STATUSES:
            sql += f" WHERE applications.status = {placeholder}"
            params = (status_filter,)
        sql += """
            GROUP BY jobs.id, applications.status, applications.notes,
                     applications.created_at, applications.updated_at,
                     applications.applied_at
            ORDER BY applications.updated_at DESC
        """
        if is_postgres:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = [dict(zip([col[0] for col in cur.description], row)) for row in cur.fetchall()]
            cur.close()
        else:
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
        for row in rows:
            match = calculate_job_match(row)
            row["match_score"] = match["score"]
            row["matched_skills"] = match["matched_skills"]
            row["match_breakdown"] = match["breakdown"]
            row["match_details"] = match["details"]
            row["match_confidence"] = match["confidence"]
        return rows
    finally:
        conn.close()


def delete_application(job_id):
    conn, is_postgres = get_app_database()
    if conn is None:
        return
    try:
        if is_postgres:
            cur = conn.cursor()
            cur.execute("DELETE FROM applications WHERE job_id = %s", (job_id,))
            conn.commit()
            cur.close()
        else:
            conn.execute("DELETE FROM applications WHERE job_id = ?", (job_id,))
            conn.commit()
    finally:
        conn.close()


def validate_csrf():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    return bool(expected and hmac.compare_digest(submitted, expected))


def enrich_jobs(rows):
    enriched = []
    for row in rows:
        item = dict(row)
        match = calculate_job_match(item)
        item["match_score"] = match["score"]
        item["matched_skills"] = match["matched_skills"]
        item["match_breakdown"] = match["breakdown"]
        item["match_details"] = match["details"]
        item["match_confidence"] = match["confidence"]
        item["application_status"] = item.get("application_status") or ""
        enriched.append(item)
    return enriched


def load_jobs(limit=200, sort=DEFAULT_SORT):
    """Devuelve hasta `limit` ofertas, más recientes primero, con sus skills."""
    # Si se proporciona DATABASE_URL, usamos PostgreSQL
    database_url = os.environ.get("DATABASE_URL", "").strip()
    order_clause = {
        "date": "jobs.created DESC",
        "location": "jobs.location COLLATE NOCASE ASC, jobs.created DESC",
        "company": "jobs.company COLLATE NOCASE ASC, jobs.created DESC",
        "skills": "skill_count DESC, jobs.created DESC",
    }.get(sort, "jobs.created DESC")
    postgres_order_clause = {
        "date": "jobs.created DESC",
        "location": "LOWER(jobs.location) ASC, jobs.created DESC",
        "company": "LOWER(jobs.company) ASC, jobs.created DESC",
        "skills": "skill_count DESC, jobs.created DESC",
    }.get(sort, "jobs.created DESC")

    if database_url:
        try:
            conn = psycopg2.connect(database_url)
        except Exception:
            return []

        try:
            ensure_applications_table(conn, True)
            cur = conn.cursor()
            sql = f"""
            SELECT
                jobs.id,
                jobs.title,
                jobs.company,
                jobs.location,
                jobs.salary_min,
                jobs.salary_max,
                jobs.contract_type,
                jobs.created,
                jobs.redirect_url,
                COUNT(skills.id) AS skill_count,
                COALESCE(STRING_AGG(skills.name, ', '), '') AS skills,
                COALESCE(MAX(applications.status), '') AS application_status
            FROM jobs
            LEFT JOIN job_skills ON job_skills.job_id = jobs.id
            LEFT JOIN skills ON skills.id = job_skills.skill_id
            LEFT JOIN applications ON applications.job_id = jobs.id
            GROUP BY jobs.id
            ORDER BY {postgres_order_clause}
            LIMIT %s
            """
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            result = [dict(zip(cols, r)) for r in rows]
            return enrich_jobs(result)
        finally:
            conn.close()

    # Fallback a SQLite si no hay DATABASE_URL
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        ensure_applications_table(conn, False)
        cursor = conn.execute(
            f"""
            SELECT
                jobs.id,
                jobs.title,
                jobs.company,
                jobs.location,
                jobs.salary_min,
                jobs.salary_max,
                jobs.contract_type,
                jobs.created,
                jobs.redirect_url,
                COUNT(skills.id) AS skill_count,
                COALESCE(GROUP_CONCAT(skills.name, ', '), '') AS skills,
                COALESCE(MAX(applications.status), '') AS application_status
            FROM jobs
            LEFT JOIN job_skills ON job_skills.job_id = jobs.id
            LEFT JOIN skills ON skills.id = job_skills.skill_id
            LEFT JOIN applications ON applications.job_id = jobs.id
            GROUP BY jobs.id
            ORDER BY {order_clause}
            LIMIT ?
            """,
            (limit,)
        )
        return enrich_jobs(cursor.fetchall())
    finally:
        conn.close()


def run_refresh():
    """Ejecuta ingest.py como subproceso. Devuelve (success, mensaje)."""
    if not os.path.exists(INGEST_SCRIPT):
        return False, "No se encuentra ingest.py en el directorio raíz."

    if not os.environ.get("ADZUNA_APP_ID") or not os.environ.get("ADZUNA_APP_KEY"):
        return False, "Faltan las variables de entorno ADZUNA_APP_ID y/o ADZUNA_APP_KEY."

    try:
        result = subprocess.run(
            [sys.executable, INGEST_SCRIPT],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=REFRESH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, "ingest.py tardó demasiado y se canceló."

    if result.returncode != 0:
        app.logger.error("ingest.py failed (exit %s): %s", result.returncode, (result.stderr or result.stdout or "Unknown error").strip())
        return False, "No se pudieron actualizar las ofertas. Revisa los registros del servidor."

    return True, result.stdout.strip()


@app.route("/")
def index():
    lang = get_locale()
    sort = get_sort()
    t = get_translations(lang)
    jobs = load_jobs(sort=sort)
    jobs_count_label = t["offers_count"].format(count=len(jobs))
    return render_template(
        "index.html",
        jobs=jobs,
        lang=lang,
        sort=sort,
        t=t,
        languages=SUPPORTED_LANGUAGES,
        jobs_count_label=jobs_count_label,
        csrf_token=session.setdefault("csrf_token", secrets.token_urlsafe(32)),
    )


@app.route("/applications")
def applications():
    status_filter = request.args.get("status", "")
    if status_filter not in APPLICATION_STATUSES:
        status_filter = None
    items = load_applications(status_filter)
    return render_template(
        "applications.html",
        applications=items,
        statuses=APPLICATION_STATUSES,
        selected_status=status_filter or "",
        csrf_token=session.setdefault("csrf_token", secrets.token_urlsafe(32)),
    )


@app.route("/applications/<int:job_id>", methods=["POST"])
def update_application(job_id):
    if not validate_csrf():
        return "Solicitud no válida. Recarga la página e inténtalo de nuevo.", 400
    status = request.form.get("status", "saved")
    notes = request.form.get("notes", "")
    try:
        save_application(job_id, status, notes)
        flash("Candidatura actualizada correctamente.", "success")
    except (ValueError, LookupError) as exc:
        flash(str(exc), "danger")
    return redirect(url_for("applications"))


@app.route("/applications/<int:job_id>/delete", methods=["POST"])
def remove_application(job_id):
    if not validate_csrf():
        return "Solicitud no válida. Recarga la página e inténtalo de nuevo.", 400
    delete_application(job_id)
    flash("Oferta retirada de tu seguimiento.", "success")
    return redirect(url_for("applications"))


@app.route("/refresh", methods=["POST"])
def refresh():
    global _last_refresh_at
    lang = get_locale()
    sort = get_sort()
    t = get_translations(lang)

    if not validate_csrf():
        return "Solicitud no válida. Recarga la página e inténtalo de nuevo.", 400

    elapsed = time.monotonic() - _last_refresh_at
    if elapsed < REFRESH_MIN_INTERVAL_SECONDS:
        remaining = int(REFRESH_MIN_INTERVAL_SECONDS - elapsed)
        flash(t["alert_refresh_rate_limited"].format(seconds=remaining), "warning")
        return redirect(url_for("index", lang=lang, sort=sort))

    _last_refresh_at = time.monotonic()
    success, message = run_refresh()
    if success:
        flash(t["alert_refresh_success"], "success")
    else:
        flash(t["alert_refresh_error"].format(message=message[:300]), "danger")
    return redirect(url_for("index", lang=lang, sort=sort))


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, port=5000)
    