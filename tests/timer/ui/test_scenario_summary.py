import pytest
from timer import i18n
from timer.ui.scenario_summary import describe


def test_the_count_and_the_length_of_the_scenario_are_told():
    assert describe(6, 185 * 60) == "Work intervals: 6 · ~3h 05m"


@pytest.mark.parametrize("count", [0, 1, 2, 5, 11, 21])
def test_every_count_is_told_in_the_same_form(count):
    assert describe(count, 60 * 60) == f"Work intervals: {count} · ~1h 00m"


def test_the_summary_comes_in_the_language_in_force():
    i18n.set_language("ru")

    assert describe(6, 185 * 60) == "Рабочих интервалов: 6 · ~3 ч 05 мин"
