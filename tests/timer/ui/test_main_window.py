import sys

import pytest
from timer.i18n import t
from timer.ui.main_window import window_title


def test_a_release_window_is_titled_timer(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    assert window_title() == "Timer"


def test_a_window_run_from_source_is_marked_as_dev(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert window_title() == "Timer (dev)"


@pytest.mark.parametrize("key", ["app.title", "app.title_dev"])
def test_the_titles_exist_in_the_catalog(key):
    assert t(key)
