from flask import Blueprint, render_template

from config import SUPPORTED_LANGUAGES
import core

home_bp = Blueprint("home", __name__)


@home_bp.get("/")
def index() -> str:
    lang = core.get_locale()
    sort = core.get_sort()
    query = core.get_search_query()
    translations = core.get_translations(lang)
    jobs = core.load_jobs(sort=sort, query=query)
    jobs_count_label = translations["offers_count"].format(count=len(jobs))
    return render_template(
        "index.html",
        jobs=jobs,
        lang=lang,
        sort=sort,
        query=query,
        t=translations,
        languages=SUPPORTED_LANGUAGES,
        jobs_count_label=jobs_count_label,
    )
