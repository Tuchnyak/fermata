import json

import pytest
from fermata.scenarios import (
    Scenario,
    ScenarioRow,
    from_snapshot,
    to_snapshot,
)
from fermata.storage.settings import Settings

EXAMPLE_ROWS = (ScenarioRow(category_id=2, count=2), ScenarioRow(category_id=3, count=1))


@pytest.fixture
def example():
    """The example of the spec: (Work × 2, Personal × 1) × 2."""
    return Scenario(name="Work day", rows=EXAMPLE_ROWS, repeat_count=2)


# --- the work intervals --------------------------------------------------------


def test_the_rows_are_repeated_as_a_whole(example):
    assert example.work_category_ids() == [2, 2, 3, 2, 2, 3]


def test_one_row_once_is_a_single_work_interval():
    scenario = Scenario(name="One", rows=(ScenarioRow(5, 1),))

    assert scenario.work_category_ids() == [5]


# --- the effective settings ----------------------------------------------------


def test_without_overrides_the_global_settings_apply(example):
    settings = Settings(work_minutes=40, transition_mode="auto", blink=False)

    assert example.effective_settings(settings) == settings


def test_overrides_replace_the_global_values():
    scenario = Scenario(
        name="Short",
        rows=EXAMPLE_ROWS,
        work_minutes=10,
        short_break_minutes=2,
        long_break_minutes=7,
        long_break_every=3,
    )

    effective = scenario.effective_settings(Settings())

    assert (
        effective.work_minutes,
        effective.short_break_minutes,
        effective.long_break_minutes,
        effective.long_break_every,
    ) == (10, 2, 7, 3)


def test_the_transition_mode_and_blink_are_always_global():
    scenario = Scenario(name="Short", rows=EXAMPLE_ROWS, work_minutes=10)

    effective = scenario.effective_settings(Settings(transition_mode="mixed", blink=False))

    assert (effective.transition_mode, effective.blink) == ("mixed", False)


def test_an_override_replaces_only_its_own_value():
    scenario = Scenario(name="Short", rows=EXAMPLE_ROWS, short_break_minutes=2)

    effective = scenario.effective_settings(Settings(work_minutes=40))

    assert (effective.work_minutes, effective.short_break_minutes) == (40, 2)


# --- the total duration --------------------------------------------------------


def test_the_total_of_the_example_is_three_hours_five_minutes(example):
    # Six work intervals of 25 minutes; between them four short breaks of 5 minutes and one
    # long break of 15 (after the fourth), none after the last: 150 + 20 + 15 = 185 minutes.
    assert example.total_seconds(Settings()) == 185 * 60


def test_a_single_work_interval_has_no_break():
    scenario = Scenario(name="One", rows=(ScenarioRow(5, 1),))

    assert scenario.total_seconds(Settings()) == 25 * 60


def test_the_total_uses_the_overrides():
    scenario = Scenario(
        name="Short",
        rows=(ScenarioRow(5, 4),),
        work_minutes=10,
        short_break_minutes=1,
        long_break_minutes=3,
        long_break_every=3,
    )

    # Four work intervals of 10; breaks after the first two (short) and the third (long).
    assert scenario.total_seconds(Settings()) == (40 + 1 + 1 + 3) * 60


# --- the snapshot --------------------------------------------------------------


def test_the_snapshot_is_json_text(example):
    assert isinstance(json.loads(to_snapshot(example)), dict)


def test_a_snapshot_restores_the_scenario(example):
    assert from_snapshot(to_snapshot(example)) == example


def test_a_snapshot_keeps_the_overrides():
    scenario = Scenario(
        name="Short",
        rows=EXAMPLE_ROWS,
        repeat_count=3,
        work_minutes=10,
        short_break_minutes=2,
        long_break_minutes=7,
        long_break_every=3,
    )

    assert from_snapshot(to_snapshot(scenario)) == scenario
