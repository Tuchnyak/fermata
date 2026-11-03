# Timer — Roadmap

Stages are implemented in order. Requirements and decisions: [spec.md](spec.md).
Sound always stays the last functional stage: new intermediate features are inserted before it.

## Stage 0 — Project setup

- Minimal README.
- License: GPL-3.0-only.
- Development workflow rules in `AGENTS.md`.

## Stage 1 — Core and Flow

Breakdown into pieces with progress: [stage-1.md](stage-1.md).

**Status: done.**

- SQLite storage: database location and the complete schema (settings, categories, scenarios, sessions, intervals); schema documented in `docs/schema.md`.
- Localization helper `t(key)` with English strings; all UI text goes through it from the start.
- Categories: manage list and colors, system `None`, archiving.
- Global settings: durations, N, transition mode (three modes with explanations), blink.
- Flow mode with Pause / Skip / Stop and the transition modes.
- Main window with navigation inside one window; hotkeys `Space`, `Enter`, `Esc`.
- Intervals are written to the database (history data accumulates from here on).

Done when: a flow runs by the global rules, survives a restart without data loss, and timer logic is covered by tests.

## Stage 2 — Scenarios

Breakdown into pieces with progress: [stage-2.md](stage-2.md).

**Status: done.**

The scenario tables already exist (schema v1, Stage 1); this stage adds the code and the UI.

- Scenario model: rows (category × count), repeat count, timer overrides.
- Scenarios screen and scenario editor with live preview and total duration; Save & start.
- Scenario sessions from a snapshot; summary at the end.
- Circle progress row with all states and the long-break gaps; blinking current circle.
- Resume an interrupted scenario session on start.
- Archiving a category is blocked while scenarios use it.

Done when: the example scenario `(Work × 2, Personal × 1) × 2` can be built, run, interrupted, resumed and finished with a correct summary.

## Interim release 0.2 — sound and a local build

An out-of-order detour for the owner's own use: a first cut of sound (end of work, end of break, one switch) and a local Linux build, released on the branch `release/v0.2.0`. Breakdown: [release-0.2.md](release-0.2.md). The rest of sound stays in Stage 5, the rest of packaging in Stage 6.

## Stage 3 — Themes and fullscreen

Breakdown into pieces with progress: [stage-3.md](stage-3.md).

**Status: done.**

- Six themes: Light, Dark, Catppuccin Latte / Frappé / Macchiato / Mocha; switching in Settings.
- Layout that scales with the window.
- Fullscreen board (`F11`, `Esc`).
- Window size and position remembered.

## Stage 4 — History screen

Breakdown into pieces with progress: [stage-4.md](stage-4.md).

**Status: done.**

- Day / Week view with navigation and a Today button, work interval list with colors and statuses, totals per category and in all.

## Stage 5 — Sound

- Calm transition sounds with a global on/off switch; choose the playback method for Linux.

## Stage 6 — Packaging and CI

- PyInstaller build for Linux.
- Version in the UI: shown in Settings and printed by `--version`, read from the package metadata (the build has to carry it); no second place where the number is written.
- Application icon: one picture (from the owner) used as the window icon and as the icon of the launcher entry that the local installer writes; the build carries it.
- CI pipeline; builds for other OS only if they become needed.

## Backlog

Not scheduled. Each item needs its own design discussion before work starts.

- **Theme editor** — to be designed separately.
- Deferred ideas from requirements (add only on real need): restart interval, "+5 minutes", per-scenario transition mode, per-category work interval length, history screen with charts and filters, builds for Windows/macOS.
