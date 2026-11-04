import pytest
from timer import i18n
from timer.logic import format_duration, format_time

def test_format_time_under_a_minute():
    assert format_time(5) == "00:05"


def test_format_time_with_minutes():
    assert format_time(125) == "02:05"


@pytest.mark.parametrize("seconds, expected", [
    (0, "00:00"),
    (5, "00:05"),
    (125, "02:05"),
    (3600, "60:00"),
])
def test_format_time(seconds, expected):
    assert format_time(seconds) == expected


def test_format_time_minus_one():
    assert format_time(-1) == "00:00"




@pytest.mark.parametrize("seconds, expected", [
    (0, "0m"),
    (25 * 60, "25m"),
    (59 * 60, "59m"),
    (60 * 60, "1h 00m"),
    (65 * 60, "1h 05m"),
    (185 * 60, "3h 05m"),
    (10 * 3600, "10h 00m"),
])
def test_format_duration(seconds, expected):
    assert format_duration(seconds) == expected


def test_format_duration_drops_seconds():
    assert format_duration(25 * 60 + 59) == "25m"


def test_format_duration_comes_in_the_language_in_force():
    i18n.set_language("ru")

    assert format_duration(25 * 60) == "25 мин"
    assert format_duration(3 * 3600 + 5 * 60) == "3 ч 05 мин"
