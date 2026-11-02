import sys

from timer.build import is_release


def test_running_from_source_is_not_a_release(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert is_release() is False


def test_a_frozen_executable_is_a_release(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    assert is_release() is True
