# Timer — Roadmap

Stages are implemented in order. Requirements and decisions: [spec.md](spec.md).
Sound always stays the last functional stage: new intermediate features are inserted before it.

## Stage 0 — Project setup

- Minimal README.
- License: GPL-3.0-only.
- Development workflow rules in `AGENTS.md`.

## Stage 1 — Core and Flow

Breakdown into pieces with progress: [stage-1.md](stage-1.md).

- SQLite storage: database location, schema for settings, session types, runs and stages; schema documented in `docs/`.
- Localization helper `t(key)` with English strings; all UI text goes through it from the start.
- Session types: manage list and colors, system `None`, archiving.
- Global settings: durations, interval N, transition mode (three modes with explanations), blink.
- Flow mode with Pause / Skip / Stop and the transition modes.
- Main window with navigation inside one window; hotkeys `Space`, `Enter`, `Esc`.
- Stages are written to the database (history data accumulates from here on).

Done when: a flow runs by the global rules, survives a restart without data loss, and timer logic is covered by tests.

## Stage 2 — Plans

- Plan model: rows (type × count), repeat count, timer overrides.
- Plans screen and plan editor with live preview and total duration; Save & start.
- Plan runs from a snapshot; summary at the end.
- Circle progress row with all states and the long-break gaps; blinking current circle.
- Resume an interrupted plan run on start.
- Archiving a type is blocked while plans use it.

Done when: the example plan `(Work × 2, Personal × 1) × 2` can be built, run, interrupted, resumed and finished with a correct summary.

## Stage 3 — Themes and fullscreen

- Six themes: Light, Dark, Catppuccin Latte / Frappé / Macchiato / Mocha; switching in Settings.
- Layout that scales with the window.
- Fullscreen board (`F11`, `Esc`).
- Window size and position remembered.

## Stage 4 — History screen

- Day / Week view with navigation, session list with colors and statuses, totals per type.

## Stage 5 — Sound

- Calm transition sounds with a global on/off switch; choose the playback method for Linux.

## Stage 6 — Packaging and CI

- PyInstaller build for Linux.
- CI pipeline; builds for other OS only if they become needed.

## Backlog

Not scheduled. Each item needs its own design discussion before work starts.

- **Theme editor** — to be designed separately.
- Deferred ideas from requirements (add only on real need): restart stage, "+5 minutes", per-plan transition mode, per-type session length, history screen with charts and filters, builds for Windows/macOS.
