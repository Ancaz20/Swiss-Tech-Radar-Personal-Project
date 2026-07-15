import time

from flask import Blueprint, current_app, flash, redirect, url_for

import core

refresh_bp = Blueprint("refresh", __name__)
_last_refresh_at = 0.0


@refresh_bp.post("/refresh")
def refresh() -> object:
    global _last_refresh_at

    lang = core.get_locale()
    sort = core.get_sort()
    translations = core.get_translations(lang)

    min_interval = current_app.config.get("REFRESH_MIN_INTERVAL_SECONDS", 60)
    elapsed = time.monotonic() - _last_refresh_at
    if elapsed < min_interval:
        remaining = int(min_interval - elapsed)
        flash(translations["alert_refresh_rate_limited"].format(seconds=remaining), "warning")
        return redirect(url_for("home.index", lang=lang, sort=sort))

    _last_refresh_at = time.monotonic()
    success, message = core.run_refresh()
    if success:
        flash(translations["alert_refresh_success"], "success")
    else:
        flash(translations["alert_refresh_error"].format(message=message[:300]), "danger")
    return redirect(url_for("home.index", lang=lang, sort=sort))
