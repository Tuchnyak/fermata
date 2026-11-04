from datetime import timedelta

import pytest
from fermata.clock import DEV_SPEED, make_clock, real_clock, sped_up_clock, speed_of


def test_the_sped_up_clock_starts_from_the_time_of_its_source(clock):
    sped_up = sped_up_clock(2, clock)

    assert sped_up() == clock()


def test_the_sped_up_clock_runs_faster_than_its_source(clock):
    started = clock()
    sped_up = sped_up_clock(2, clock)

    clock.advance(10)

    assert sped_up() == started + timedelta(seconds=20)


@pytest.mark.parametrize("speed", [1, 2, 5])
def test_the_speed_is_the_ratio_of_elapsed_times(clock, speed):
    started = clock()
    sped_up = sped_up_clock(speed, clock)

    clock.advance(30)
    clock.advance(0.5)

    assert sped_up() - started == timedelta(seconds=30.5 * speed)


def test_the_sped_up_clock_keeps_the_timezone(clock):
    assert sped_up_clock(2, clock)().tzinfo is clock().tzinfo


def test_the_real_clock_is_in_utc():
    assert real_clock().utcoffset() == timedelta(0)


def test_a_release_uses_the_clock_as_it_is(clock):
    assert make_clock(release=True, real_time=False, source=clock) is clock


def test_a_run_from_source_is_sped_up_by_default(clock):
    started = clock()
    made = make_clock(release=False, real_time=False, source=clock)

    clock.advance(10)

    assert made() == started + timedelta(seconds=10 * DEV_SPEED)


def test_the_development_speed_is_twice_the_normal_one():
    assert DEV_SPEED == 2


def test_real_time_asks_a_run_from_source_for_the_normal_speed(clock):
    assert make_clock(release=False, real_time=True, source=clock) is clock


def test_a_release_ignores_real_time(clock):
    assert make_clock(release=True, real_time=True, source=clock) is clock


@pytest.mark.parametrize(
    ("release", "real_time", "speed"),
    [(False, False, 2), (False, True, 1), (True, False, 1), (True, True, 1)],
)
def test_only_a_run_from_source_without_real_time_is_sped_up(release, real_time, speed):
    assert speed_of(release=release, real_time=real_time) == speed
