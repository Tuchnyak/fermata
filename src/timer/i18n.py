import json
from importlib import resources

CATALOG: dict[str, str] = json.loads(
    (resources.files("timer") / "locales" / "en.json").read_text(encoding="utf-8")
)


def t(key: str, **values) -> str:
    return CATALOG[key].format(**values)
