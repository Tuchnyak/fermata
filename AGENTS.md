# AGENTS.md

Pomodoro timer with Scenarios (pre-designed queues of work intervals) and Flow mode. Desktop app for Linux.

- Requirements and decisions: [docs/spec.md](docs/spec.md)
- Stage order and backlog: [docs/roadmap.md](docs/roadmap.md)

## Stack

Python 3.12 · Tkinter + ttkbootstrap · SQLite (`sqlite3`) · uv · pytest · PyInstaller (last stage).

## Commands

```
uv sync            # set up .venv from uv.lock
uv run timer       # run the app; from source its clock goes 2x faster (see --real-time)
uv run timer --real-time   # run from source at the normal speed
uv run pytest      # run tests
uv add <pkg>       # add a dependency (--dev for tooling)
```

## Layout

- `src/timer/` — application package; entry point `timer.app:main`.
  - `engine.py`, `intervals.py`, `scenarios.py` — timer logic with no UI and no database: the engine, the interval rules, the scenario value types.
  - `recorder.py`, `resume.py` — the recorder writes the engine's events to the database; `resume.py` offers a scenario session left behind by a closed app and carries out the answer.
  - `storage/` — SQLite: the `Db` helper, migrations (`storage/migrations/NNN_*.sql`), repositories, the data directory.
  - `ui/` — Tkinter. `*_view_model.py` (and the pure `progress.py`, `scenario_summary.py`) hold the logic of a screen without Tk and are tested; `*_screen.py`, `*_panel.py`, `scenario_editor.py`, `progress_row.py` and `main_window.py` are the Tk widgets.
  - `wiring.py` — builds everything except Tk (database, engine, view models); `i18n.py` with `locales/en.json` is `t(key)`.
- `tests/` — pytest tests, mirroring `src/` (e.g. `tests/timer/ui/test_hotkeys.py`).
- `docs/` — project documentation, in English.

## Rules

- Implement only what `docs/spec.md` describes, stage by stage per the roadmap. No extra features, options or abstractions; propose them instead.
- Keep timer logic out of UI code and cover it with tests.
- Use ttk widgets; classic `tk` widgets only where ttk has none (e.g. `Canvas`).
- Every UI string goes through the `t(key)` localization helper.
- All data lives in the one SQLite database described in the spec.
- Code, comments and docs in English.
- When the owner says they are learning something, explain and give commands for them to run; do not make the changes yourself.
- No license headers in source files; the license is in `LICENSE`.

## Workflow

The agent develops, the owner acts as product manager and reviewer.

- Each roadmap stage gets its own branch: `<type>/stage-<N>-<topic>`, e.g. `feat/stage-1-core`.
- A stage is split into pieces, each one a runnable slice (a few per stage), listed with checkboxes in `docs/stage-<N>.md`. For each piece (ATDD):
  1. State the decisions the owner is likely to have an opinion on (names, formats, behavior) and wait for "ok" or corrections.
  2. Write the acceptance tests and see them fail first: for new code a stub with the names the tests use, `raise NotImplementedError` bodies and deliberately wrong values (e.g. enum members), so every test fails on the missing behavior, not on an import error. The stub is not committed on its own.
  3. Implement until the tests pass.
  4. Present one report: the tests, what changed, the green run and a manual check list. The owner reviews the tests as acceptance tests and approves the piece as a whole.
  5. Commit only after the owner's explicit approval; several commits per piece are fine, and the checkbox is ticked in the last one.
- Commit messages use Conventional Commits prefixes: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`.
- A finished stage is merged into `master` with a merge commit (`git merge --no-ff`) so the commits of its pieces stay in history.
