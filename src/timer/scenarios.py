"""Scenarios: the value types and the pure rules that need no database.

A scenario is an ordered list of rows (a category and how many work intervals in a row), a
repeat count for the whole list and optional overrides of the four timer settings. The
snapshot is the JSON text a session keeps as a copy of its scenario (see docs/schema.md).
"""

import json
from dataclasses import dataclass, replace

from timer.storage.settings import Settings

ROW_COUNT_RANGE = (1, 20)  # work intervals in one row
REPEAT_COUNT_RANGE = (1, 20)
OVERRIDE_FIELDS = (
    "work_minutes",
    "short_break_minutes",
    "long_break_minutes",
    "long_break_every",
)


@dataclass(frozen=True)
class ScenarioRow:
    category_id: int
    count: int


@dataclass(frozen=True)
class Scenario:
    name: str
    rows: tuple[ScenarioRow, ...]
    repeat_count: int = 1
    work_minutes: int | None = None
    short_break_minutes: int | None = None
    long_break_minutes: int | None = None
    long_break_every: int | None = None

    def work_category_ids(self) -> list[int]:
        """The category of every work interval of the scenario, in order."""
        category_ids = []
        for _ in range(self.repeat_count):
            for row in self.rows:
                category_ids.extend([row.category_id] * row.count)
        return category_ids

    def effective_settings(self, global_settings: Settings) -> Settings:
        """The global settings with the overrides of this scenario applied."""
        overrides = {}
        for field_name in OVERRIDE_FIELDS:
            value = getattr(self, field_name)
            if value is not None:
                overrides[field_name] = value
        return replace(global_settings, **overrides)

    def total_seconds(self, global_settings: Settings) -> int:
        """All work intervals plus the breaks between them; no break after the last one."""
        settings = self.effective_settings(global_settings)
        work_count = len(self.work_category_ids())
        minutes = work_count * settings.work_minutes
        for finished_work_count in range(1, work_count):
            if finished_work_count % settings.long_break_every == 0:
                minutes += settings.long_break_minutes
            else:
                minutes += settings.short_break_minutes
        return minutes * 60


@dataclass(frozen=True, kw_only=True)
class ScenarioEntity(Scenario):
    """A scenario as stored in the database."""

    id: int


def to_snapshot(scenario: Scenario) -> str:
    return json.dumps(
        {
            "name": scenario.name,
            "rows": [
                {"category_id": row.category_id, "count": row.count}
                for row in scenario.rows
            ],
            "repeat_count": scenario.repeat_count,
            **{field_name: getattr(scenario, field_name) for field_name in OVERRIDE_FIELDS},
        }
    )


def from_snapshot(text: str) -> Scenario:
    data = json.loads(text)
    rows = []
    for row in data["rows"]:
        rows.append(ScenarioRow(row["category_id"], row["count"]))
    overrides = {field_name: data[field_name] for field_name in OVERRIDE_FIELDS}
    return Scenario(
        name=data["name"],
        rows=tuple(rows),
        repeat_count=data["repeat_count"],
        **overrides,
    )
