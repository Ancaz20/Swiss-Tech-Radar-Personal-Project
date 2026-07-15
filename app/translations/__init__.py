import json
from functools import lru_cache
from pathlib import Path


TRANSLATIONS_DIR = Path(__file__).resolve().parent
DEFAULT_LANG = "es"


@lru_cache(maxsize=None)
def load_translations(lang: str) -> dict[str, str]:
    translation_path = TRANSLATIONS_DIR / f"{lang}.json"
    if not translation_path.exists():
        translation_path = TRANSLATIONS_DIR / f"{DEFAULT_LANG}.json"

    with translation_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
