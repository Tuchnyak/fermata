# Fermata

Focus timer with scenarios.

A focus timer for tracking work intervals; in music a fermata is a pause held as long as the performer chooses. Design a **Scenario** — a queue of work intervals of different categories, each with its own color — and start it in one go, or run a simple endless **Flow**.

Status: early development. See the [specification](docs/spec.md) and the [roadmap](docs/roadmap.md).

## Requirements

- Linux
- Python 3.12+ with Tkinter
- [uv](https://docs.astral.sh/uv/)

## Run

```
uv run fermata               # from source: the clock goes twice as fast, to test quickly
uv run fermata --real-time   # from source, at the normal speed
```

A run from source keeps its data apart from an installed release and shows "(dev, ×2)" in the window title while the clock is sped up.

## Install for local use

```
./scripts/install-local.sh
```

Builds a single executable with PyInstaller and installs it as `~/.local/bin/fermata` with an entry in the application menu. It is built for the machine it is built on. The installed program is a release: its data is in `~/.local/share/fermata` (separate from the data of a run from source), its clock is the real one, and sounds come from `src/fermata/sounds/`. Run the script again after changing the code to update it. To remove the program, delete `~/.local/bin/fermata`, `~/.local/share/applications/fermata.desktop` and the two `fermata` icons in `~/.local/share/icons/hicolor/`; the data stays until you delete `~/.local/share/fermata`.

## Test

```
uv run pytest
```

## License

Copyright (C) 2026 George Shchennikov (https://github.com/Tuchnyak)

Licensed under the [GNU General Public License v3.0](LICENSE).
