"""Storage of scenarios: the `scenario` and `scenario_row` tables.

A scenario is validated as a whole before anything is written, and written together with its
rows in one transaction, so a rejected scenario leaves no trace.
"""

import sqlite3

from fermata.scenarios import (
    OVERRIDE_FIELDS,
    REPEAT_COUNT_RANGE,
    ROW_COUNT_RANGE,
    Scenario,
    ScenarioEntity,
    ScenarioRow,
)
from fermata.storage.db import Db
from fermata.storage.settings_rules import RULES
from fermata.validation import ValidationError


def _is_within(value: int, limits: tuple[int, int]) -> bool:
    lowest, highest = limits
    return lowest <= value <= highest


class ScenarioRepository:
    def __init__(self, db: Db):
        self._db = db

    def create(self, scenario: Scenario) -> ScenarioEntity:
        name = self._validate(scenario)
        with self._db.transaction():
            scenario_id = self._db.insert(
                "INSERT INTO scenario (name, repeat_count, work_minutes,"
                " short_break_minutes, long_break_minutes, long_break_every)"
                " VALUES (:name, :repeat_count, :work_minutes, :short_break_minutes,"
                " :long_break_minutes, :long_break_every)",
                self._scenario_parameters(scenario, name),
            )
            assert scenario_id is not None
            self._insert_rows(scenario_id, scenario.rows)
        return self._entity(scenario_id, scenario, name)

    def update(self, scenario_id: int, scenario: Scenario) -> ScenarioEntity:
        if self.get_by_id(scenario_id) is None:
            raise LookupError(f"No scenario with id {scenario_id}")
        name = self._validate(scenario, own_id=scenario_id)
        with self._db.transaction():
            self._db.execute(
                "UPDATE scenario SET name = :name, repeat_count = :repeat_count,"
                " work_minutes = :work_minutes, short_break_minutes = :short_break_minutes,"
                " long_break_minutes = :long_break_minutes,"
                " long_break_every = :long_break_every WHERE id = :id",
                {**self._scenario_parameters(scenario, name), "id": scenario_id},
            )
            self._db.execute(
                "DELETE FROM scenario_row WHERE scenario_id = ?", (scenario_id,)
            )
            self._insert_rows(scenario_id, scenario.rows)
        return self._entity(scenario_id, scenario, name)

    def delete(self, scenario_id: int) -> None:
        # The rows go with the scenario (ON DELETE CASCADE).
        deleted_count = self._db.execute(
            "DELETE FROM scenario WHERE id = ?", (scenario_id,)
        )
        if deleted_count == 0:
            raise LookupError(f"No scenario with id {scenario_id}")

    def get_by_id(self, scenario_id: int) -> ScenarioEntity | None:
        return self._db.query_one(
            "SELECT * FROM scenario WHERE id = ?",
            (scenario_id,),
            mapper=self._to_entity,
        )

    def list_all(self) -> list[ScenarioEntity]:
        scenarios = self._db.query("SELECT * FROM scenario", mapper=self._to_entity)
        scenarios.sort(key=lambda scenario: scenario.name.casefold())
        return scenarios

    def _to_entity(self, row: sqlite3.Row) -> ScenarioEntity:
        rows = self._db.query(
            "SELECT category_id, count FROM scenario_row"
            " WHERE scenario_id = ? ORDER BY position",
            (row["id"],),
            mapper=lambda r: ScenarioRow(r["category_id"], r["count"]),
        )
        return ScenarioEntity(
            id=row["id"],
            name=row["name"],
            rows=tuple(rows),
            repeat_count=row["repeat_count"],
            work_minutes=row["work_minutes"],
            short_break_minutes=row["short_break_minutes"],
            long_break_minutes=row["long_break_minutes"],
            long_break_every=row["long_break_every"],
        )

    def _entity(self, scenario_id: int, scenario: Scenario, name: str) -> ScenarioEntity:
        return ScenarioEntity(
            id=scenario_id,
            name=name,
            rows=scenario.rows,
            repeat_count=scenario.repeat_count,
            work_minutes=scenario.work_minutes,
            short_break_minutes=scenario.short_break_minutes,
            long_break_minutes=scenario.long_break_minutes,
            long_break_every=scenario.long_break_every,
        )

    def _scenario_parameters(self, scenario: Scenario, name: str) -> dict:
        return {
            "name": name,
            "repeat_count": scenario.repeat_count,
            "work_minutes": scenario.work_minutes,
            "short_break_minutes": scenario.short_break_minutes,
            "long_break_minutes": scenario.long_break_minutes,
            "long_break_every": scenario.long_break_every,
        }

    def _insert_rows(self, scenario_id: int, rows: tuple[ScenarioRow, ...]) -> None:
        for position, row in enumerate(rows, start=1):
            self._db.insert(
                "INSERT INTO scenario_row (scenario_id, position, category_id, count)"
                " VALUES (?, ?, ?, ?)",
                (scenario_id, position, row.category_id, row.count),
            )

    def _validate(self, scenario: Scenario, own_id: int | None = None) -> str:
        """Check the whole scenario; return the trimmed name."""
        name = scenario.name.strip()
        if not name:
            raise ValidationError("scenario.name_empty")
        if self._name_is_taken(name, own_id):
            raise ValidationError("scenario.name_taken")
        if not scenario.rows:
            raise ValidationError("scenario.rows_empty")
        for row in scenario.rows:
            if not _is_within(row.count, ROW_COUNT_RANGE):
                raise ValidationError("scenario.row_count_invalid")
        if not _is_within(scenario.repeat_count, REPEAT_COUNT_RANGE):
            raise ValidationError("scenario.repeat_invalid")
        available_category_ids = self._available_category_ids()
        for row in scenario.rows:
            if row.category_id not in available_category_ids:
                raise ValidationError("scenario.category_unavailable")
        for field_name in OVERRIDE_FIELDS:
            value = getattr(scenario, field_name)
            rule = RULES[field_name]
            if value is not None and not rule.is_valid(value):
                raise ValidationError(rule.error_key)
        return name

    def _name_is_taken(self, name: str, own_id: int | None) -> bool:
        # SQLite's NOCASE folds only ASCII, so names are compared here instead.
        others = self._db.query(
            "SELECT id, name FROM scenario",
            mapper=lambda row: (row["id"], row["name"]),
        )
        return any(
            existing_id != own_id and existing.casefold() == name.casefold()
            for existing_id, existing in others
        )

    def _available_category_ids(self) -> set[int]:
        return set(
            self._db.query(
                "SELECT id FROM category WHERE is_archived = 0",
                mapper=lambda row: row["id"],
            )
        )
