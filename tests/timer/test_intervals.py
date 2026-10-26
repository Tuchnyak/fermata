import pytest
from timer.intervals import IntervalKind, next_kind, planned_seconds
from timer.storage.settings import Settings

WORK = IntervalKind.WORK
SHORT = IntervalKind.SHORT_BREAK
LONG = IntervalKind.LONG_BREAK

DEFAULT_SETTINGS = Settings()


# --- kinds -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "text"),
    [(WORK, "work"), (SHORT, "short_break"), (LONG, "long_break")],
)
def test_kinds_are_the_texts_stored_in_the_database(kind, text):
    assert kind == text


# --- sequencing --------------------------------------------------------------


def test_a_session_starts_with_a_work_interval():
    assert next_kind([], DEFAULT_SETTINGS) == WORK


@pytest.mark.parametrize(
    ("finished", "expected"),
    [
        ([WORK], SHORT),
        ([WORK, SHORT], WORK),
        ([WORK, SHORT, WORK], SHORT),
        ([WORK, SHORT, WORK, SHORT], WORK),
        ([WORK, SHORT, WORK, SHORT, WORK], SHORT),
        ([WORK, SHORT, WORK, SHORT, WORK, SHORT], WORK),
        ([WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK], LONG),
        ([WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK, LONG], WORK),
        ([WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK, LONG, WORK], SHORT),
        ([WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK, LONG, WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK], LONG),
    ],
)  # fmt: skip
def test_with_default_settings_a_long_break_follows_every_fourth_work_interval(
    finished, expected
):
    assert next_kind(finished, DEFAULT_SETTINGS) == expected


@pytest.mark.parametrize(
    ("long_break_every", "finished", "expected"),
    [
        (1, [WORK], LONG),
        (1, [WORK, LONG], WORK),
        (1, [WORK, LONG, WORK], LONG),
        (2, [WORK], SHORT),
        (2, [WORK, SHORT, WORK], LONG),
        (2, [WORK, SHORT, WORK, LONG, WORK], SHORT),
        (2, [WORK, SHORT, WORK, LONG, WORK, SHORT, WORK], LONG),
        (3, [WORK, SHORT, WORK], SHORT),
        (3, [WORK, SHORT, WORK, SHORT, WORK], LONG),
    ],
)
def test_long_break_comes_after_every_nth_work_interval(
    long_break_every, finished, expected
):
    settings = Settings(long_break_every=long_break_every)

    assert next_kind(finished, settings) == expected


@pytest.mark.parametrize(
    "finished",
    [
        [WORK, SHORT],
        [WORK, SHORT, WORK, SHORT, WORK, SHORT, WORK, LONG],
        [WORK, WORK, SHORT],
    ],
)
def test_a_work_interval_follows_any_break(finished):
    assert next_kind(finished, DEFAULT_SETTINGS) == WORK


def test_the_same_history_gives_a_different_break_for_a_different_n():
    finished = [WORK, SHORT, WORK]

    assert next_kind(finished, Settings(long_break_every=4)) == SHORT
    assert next_kind(finished, Settings(long_break_every=2)) == LONG


# --- lengths -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "expected"), [(WORK, 25 * 60), (SHORT, 5 * 60), (LONG, 15 * 60)]
)
def test_default_lengths_are_taken_from_the_default_settings(kind, expected):
    assert planned_seconds(kind, DEFAULT_SETTINGS) == expected


@pytest.mark.parametrize(
    ("kind", "expected"), [(WORK, 30 * 60), (SHORT, 10 * 60), (LONG, 20 * 60)]
)
def test_lengths_are_taken_from_the_given_settings(kind, expected):
    settings = Settings(work_minutes=30, short_break_minutes=10, long_break_minutes=20)

    assert planned_seconds(kind, settings) == expected
