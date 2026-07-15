import os
import sqlite3
import psycopg2
import subprocess
import sys
import time
from flask import Flask, render_template, redirect, url_for, flash, request

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

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
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

    if database_url:
        try:
            conn = psycopg2.connect(database_url)
        except Exception:
            return []

        try:
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
                COALESCE(STRING_AGG(skills.name, ', '), '') AS skills
            FROM jobs
            LEFT JOIN job_skills ON job_skills.job_id = jobs.id
            LEFT JOIN skills ON skills.id = job_skills.skill_id
            GROUP BY jobs.id
            ORDER BY {order_clause}
            LIMIT %s
            """
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            result = [dict(zip(cols, r)) for r in rows]
            return result
        finally:
            conn.close()

    # Fallback a SQLite si no hay DATABASE_URL
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
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
                COALESCE(GROUP_CONCAT(skills.name, ', '), '') AS skills
            FROM jobs
            LEFT JOIN job_skills ON job_skills.job_id = jobs.id
            LEFT JOIN skills ON skills.id = job_skills.skill_id
            GROUP BY jobs.id
            ORDER BY {order_clause}
            LIMIT ?
            """,
            (limit,)
        )
        return cursor.fetchall()
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
        error_detail = (result.stderr or result.stdout or "Error desconocido.").strip()
        return False, error_detail

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
    )


@app.route("/refresh", methods=["POST"])
def refresh():
    global _last_refresh_at
    lang = get_locale()
    sort = get_sort()
    t = get_translations(lang)

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
    