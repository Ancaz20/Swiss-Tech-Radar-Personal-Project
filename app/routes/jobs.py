from flask import Blueprint, jsonify

import core

jobs_bp = Blueprint("jobs", __name__)


@jobs_bp.get("/jobs")
def jobs() -> object:
    sort = core.get_sort()
    query = core.get_search_query()
    jobs_list = core.load_jobs(sort=sort, query=query)
    return jsonify({"count": len(jobs_list), "sort": sort, "query": query, "jobs": jobs_list})
