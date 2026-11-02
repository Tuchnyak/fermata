# Timer

A pomodoro timer for tracking work intervals. Design a **Scenario** — a queue of work intervals of different categories, each with its own color — and start it in one go, or run a simple endless **Flow**.

Status: early development. See the [specification](docs/spec.md) and the [roadmap](docs/roadmap.md).

## Requirements

- Linux
- Python 3.12+ with Tkinter
- [uv](https://docs.astral.sh/uv/)

## Run

```
uv run timer               # from source: the clock goes twice as fast, to test quickly
uv run timer --real-time   # from source, at the normal speed
```

A run from source keeps its data apart from an installed release and shows "(dev, ×2)" in the window title while the clock is sped up.

## Test

```
uv run pytest
```

## License

Copyright (C) 2026 George Shchennikov (https://github.com/Tuchnyak)

Licensed under the [GNU General Public License v3.0](LICENSE).
