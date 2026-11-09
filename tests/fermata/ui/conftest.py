import tkinter
from dataclasses import dataclass

import pytest
import ttkbootstrap as ttk
from fermata.themes import register_themes, ttk_theme_name
from fermata.ui.fullscreen import Fullscreen
from fermata.ui.hotkeys import HotkeyHandler
from fermata.ui.main_window import MainWindow
from fermata.ui.navigation import Navigation
from fermata.wiring import Components, build_components


@dataclass
class ShownApp:
    root: ttk.Window
    window: MainWindow
    components: Components
    fullscreen: Fullscreen

    @property
    def header(self):
        return self.root.winfo_children()[0]

    @property
    def content(self):
        """The frame under the header, where the home screen or the board is drawn."""
        return self.root.winfo_children()[1]


@pytest.fixture
def app(tmp_path, clock, silent_output):
    """The real main window, hidden, built the way the program builds it."""
    components = build_components(tmp_path / "test.db", clock, audio_output=silent_output)
    register_themes()
    try:
        root = ttk.Window(themename=ttk_theme_name(None))
    except tkinter.TclError:
        pytest.skip("no display to open a window on")
    root.withdraw()
    navigation = Navigation()
    fullscreen = Fullscreen()
    window = MainWindow(
        root,
        navigation,
        HotkeyHandler(
            components.engine,
            navigation,
            start_flow=components.home_view_model.start,
            fullscreen=fullscreen,
        ),
        components.categories_view_model,
        components.settings_view_model,
        components.home_view_model,
        components.running_view_model,
        components.waiting_view_model,
        components.scenarios_view_model,
        components.history_view_model,
        fullscreen,
        components.background_sound,
    )
    yield ShownApp(root, window, components, fullscreen)
    root.destroy()
