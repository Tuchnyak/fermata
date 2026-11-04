"""The one-line description of a scenario: how many work intervals and how long."""

from fermata.i18n import t
from fermata.logic import format_duration


def describe(work_count: int, total_seconds: int) -> str:
    return t("scenarios.summary", count=work_count, duration=format_duration(total_seconds))
