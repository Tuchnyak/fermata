import pytest
from timer.ui.scenario_summary import describe


def test_several_work_intervals_are_counted_in_the_plural():
    assert describe(6, 185 * 60) == "6 work intervals · ~3h 05m"


def test_one_work_interval_is_counted_in_the_singular():
    assert describe(1, 25 * 60) == "1 work interval · ~25m"


@pytest.mark.parametrize("count", [0, 2, 5, 11])
def test_other_counts_use_the_plural(count):
    assert describe(count, 60 * 60).startswith(f"{count} work intervals")
