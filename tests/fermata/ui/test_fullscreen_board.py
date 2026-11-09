import pytest
import ttkbootstrap as ttk

FULLSCREEN_SIGN = "⛶"


@pytest.fixture
def window(app):
    return app.root, app.fullscreen


def fullscreen_buttons(parent):
    """The buttons under `parent` that carry the fullscreen sign."""
    found = []
    for child in parent.winfo_children():
        if isinstance(child, ttk.Button) and str(child.cget("text")) == FULLSCREEN_SIGN:
            found.append(child)
        found.extend(fullscreen_buttons(child))
    return found


def content_of(root):
    """The frame under the header, where the board is drawn."""
    return root.winfo_children()[1]


def header_of(root):
    return root.winfo_children()[0]


def test_the_header_button_enters_fullscreen(window):
    root, fullscreen = window

    fullscreen_buttons(header_of(root))[0].invoke()

    assert fullscreen.is_on


def test_the_board_has_a_button_that_leaves_fullscreen(window):
    root, fullscreen = window
    fullscreen_buttons(header_of(root))[0].invoke()

    (leave,) = fullscreen_buttons(content_of(root))
    leave.invoke()

    assert not fullscreen.is_on


def test_after_leaving_the_board_the_header_buttons_are_back(window):
    root, fullscreen = window
    fullscreen_buttons(header_of(root))[0].invoke()
    fullscreen_buttons(content_of(root))[0].invoke()

    assert len(fullscreen_buttons(header_of(root))) == 1
    assert fullscreen_buttons(content_of(root)) == []


def test_the_normal_window_has_no_leave_button_in_its_content(window):
    root, fullscreen = window

    assert fullscreen_buttons(content_of(root)) == []
