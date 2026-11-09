import ttkbootstrap as ttk


def button_texts(parent):
    """The texts of all the buttons under `parent`."""
    found = []
    for child in parent.winfo_children():
        if isinstance(child, ttk.Button):
            found.append(str(child.cget("text")))
        found.extend(button_texts(child))
    return found


def wait_for_confirmation(app, clock):
    """A flow whose work interval has run out, with the engine waiting for the next step."""
    app.components.home_view_model.start()
    clock.advance(2 * 60 * 60)
    app.window._on_tick()
    assert app.components.engine.upcoming_interval is not None


def test_the_waiting_screen_of_a_normal_window_has_the_buttons(app, clock):
    wait_for_confirmation(app, clock)

    assert button_texts(app.content) == ["Next", "Stop"]


def test_the_waiting_screen_of_the_board_has_no_buttons_but_the_corner_ones(app, clock):
    app.fullscreen.toggle()
    app.window._show_current_screen()
    wait_for_confirmation(app, clock)

    assert "Next" not in button_texts(app.content)
    assert app.content.winfo_children() != []
