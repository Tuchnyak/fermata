# AGENTS.md

Pomodoro timer with Scenarios (pre-designed queues of work intervals) and Flow mode. Desktop app for Linux.

- Requirements and decisions: [docs/spec.md](docs/spec.md)
- Stage order and backlog: [docs/roadmap.md](docs/roadmap.md)

## Stack

Python 3.12 · Tkinter + ttkbootstrap · SQLite (`sqlite3`) · uv · pytest · PyInstaller (last stage).

## Commands

```
uv sync            # set up .venv from uv.lock
uv run timer       # run the app
uv run pytest      # run tests
uv add <pkg>       # add a dependency (--dev for tooling)
```

## Layout

- `src/timer/` — application package; entry point `timer.app:main`.
  - `engine.py`, `intervals.py`, `recorder.py` — timer logic; the engine has no UI and no database, the recorder writes its events to the database.
  - `storage/` — SQLite: the `Db` helper, migrations (`storage/migrations/NNN_*.sql`), repositories, the data directory.
  - `ui/` — Tkinter. `*_view_model.py` hold the logic of a screen without Tk and are tested; `*_screen.py`, `*_panel.py` and `main_window.py` are the Tk widgets.
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
- A stage is split into atomic pieces. For each piece (ATDD):
  1. Write the acceptance tests and present them together with their red run; the owner approves them before implementation. For new code the tests come with a stub: the names the tests use, with `raise NotImplementedError` bodies and deliberately wrong values (e.g. enum members), so every test fails on the missing behavior, not on an import error. The stub is not committed on its own; the implementation replaces it.
  2. Implement until the tests pass.
  3. Present the result: what changed, how it was verified, how to check it.
  4. Commit only after the owner's explicit approval.
- Commit messages use Conventional Commits prefixes: `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`.
- A finished stage is merged into `master` with a merge commit (`git merge --no-ff`) so the commits of its pieces stay in history.
