# Stage 1 — Core and Flow: breakdown

Breakdown of [roadmap.md](roadmap.md) Stage 1 into atomic pieces. Requirements: [spec.md](spec.md).
Branch: `feat/stage-1-core`. A piece is ticked when the owner has approved it and it is committed.

## How a piece is accepted

1. Acceptance tests are written first and shown to the owner; implementation starts after they are approved.
2. Logic pieces are accepted by automated tests (real SQLite in memory, a fake clock for the timer; no mocks).
3. UI pieces have automated tests for their non-visual part (navigation, key mapping, view-model logic) and a short **manual check** that the owner runs: the visual part cannot be tested automatically without a display.
4. Pieces are done in the listed order; each depends on the previous ones unless stated otherwise.

## Pieces

### Foundation

- [x] **1.0 Breakdown** — this document, linked from the roadmap.

- [x] **1.1 Localization helper**
  - `t("key")` returns the English text from one catalog file with flat dotted keys.
  - `t("key", name=value)` substitutes `{name}` placeholders.
  - An unknown key raises `KeyError`, so typos fail loudly.
  - Later pieces add their own keys to the catalog.

- [x] **1.2 Data directory**
  - `data_dir()` returns `$XDG_DATA_HOME/timer` when the variable is set, otherwise `~/.local/share/timer` (for a release build; see 1.24a for development).
  - The directory is created if missing; calling again does not fail.
  - `db_path()` is `<data_dir>/timer.db`.

- [x] **1.3 Db helper: queries**
  - `Db.open(path)` opens a SQLite file or `:memory:`, with foreign keys enforced and rows readable by column name.
  - `execute` returns the number of affected rows; `insert` returns the new id.
  - `query` returns a list of objects built by the given mapper; `query_one` returns one object or `None`.
  - Named parameters (`:name` with a dict) work.
  - Violating a foreign key raises an error.

- [x] **1.4 Db helper: transactions**
  - Changes made inside `with db.transaction():` are committed when the block ends normally.
  - An exception inside the block rolls everything back and is re-raised.
  - A nested transaction raises an error.
  - A statement outside a transaction block is committed immediately.

- [x] **1.5 Migration runner**
  - On a fresh database, applies all `NNN_*.sql` files in order and sets `PRAGMA user_version` to the last number.
  - A second run changes nothing.
  - On an older database applies only the missing files.
  - A database whose version is newer than the known migrations is rejected without changes.
  - A failing migration is rolled back completely and the version stays unchanged.

- [x] **1.6 Schema v1** (migration `001`)
  - The complete schema of spec §16: tables `setting`, `category`, `scenario`, `scenario_row`, `session`, `interval` and the view `interval_details`. Stage 2 adds code for scenarios, not tables.
  - `category`: name unique ignoring case; the system category `None` exists after migration.
  - `scenario`: name unique ignoring case; repeat count at least 1; four optional timer overrides (NULL = use the global value). `scenario_row`: position unique within a scenario, count at least 1; rows are deleted together with their scenario.
  - `session.kind` is `flow` or `scenario`; `session.status` is `running`, `completed`, `stopped` or `interrupted`. A scenario session has a scenario name and a snapshot (JSON text), a flow has neither.
  - `interval.kind` is `work`, `short_break` or `long_break`; a work interval has a category, a break has none; `interval.status` is NULL while the interval runs, then `completed`, `skipped`, `stopped` or `interrupted`; position is unique within a session. Values outside these are rejected.
  - Times are ISO-8601 UTC text; `actual_seconds` is NULL for interrupted intervals.
  - `interval_details` lists intervals with the category name and color, the session kind and the scenario name.
  - `docs/schema.md` documents every table, column and the view, and includes example analysis queries (e.g. worked time per category per week).

### Categories

- [x] **1.7 Categories: create and read**
  - `create(name, color)` returns the new category; the name is trimmed and must not be empty; the color must look like `#rrggbb`; a duplicate name (ignoring case) is rejected.
  - `get(id)` returns any category, archived or not.
  - `list_active()` returns non-archived categories, `None` first, then by name.

- [x] **1.8 Categories: rename and recolor**
  - `update(id, name=…, color=…)` applies the same validation as create.
  - The system category and unknown ids are rejected.

- [x] **1.9 Categories: archive**
  - `archive(id)` removes the category from `list_active()`; `get(id)` still returns it.
  - `unarchive(id)` brings it back.
  - The system category cannot be archived.
  - The rule "not while a scenario uses it" is added in Stage 2, when the scenario code exists.

### Settings

- [x] **1.10 Settings store**
  - `get_all()` returns typed settings: work interval, short break and long break minutes, long break every N, transition mode, blink flag; defaults are those of spec §4.1 when nothing is stored.
  - `set(key, value)` persists the value; it is still there after reopening the database.
  - Theme and sound settings arrive with their own stages.

- [x] **1.11 Settings validation**
  - Minutes must be 1–180 and N must be 1–20.
  - Transition mode must be one of `auto`, `confirm`, `mixed`.
  - An invalid value or an unknown key raises an error and stores nothing.

### Timer engine (pure logic, no UI, no database)

- [x] **1.12 Interval sequencing**
  - After a work interval comes a short break; after every N-th work interval a long break instead; after a break comes a work interval.
  - Skipped work intervals count toward N.
  - With defaults the order is: work, short, work, short, work, short, work, long, work, …
  - Lengths come from the given timer settings.

- [x] **1.13 Engine: running an interval**
  - Starting a flow with a category begins a work interval of the configured length.
  - The remaining time is computed from an injected clock (no tick counting, so no drift).
  - When the planned time has elapsed the interval completes with actual time equal to planned.
  - Settings are read when an interval starts: a change affects only intervals that start afterwards.

- [x] **1.14 Engine: pause and resume**
  - While paused the remaining time does not change and the paused time is not counted as worked time.
  - Resume continues the countdown; pausing an already paused interval has no effect.

- [x] **1.15 Engine: skip**
  - Skipping a work interval ends it as `skipped` with the time actually elapsed, and the next interval (per 1.12) starts immediately.
  - Skipping a break ends it as `skipped`, and the next work interval starts immediately.
  - Skip starts the next interval immediately in every transition mode.

- [x] **1.16 Engine: stop**
  - Stop ends the current interval as `stopped` with the time actually elapsed and ends the flow; the engine becomes idle.
  - Stop while idle has no effect.

- [x] **1.17 Engine: transition mode "confirm"**
  - When an interval completes, the engine enters a waiting state that exposes the upcoming interval (kind, category, length); no time is counted.
  - `confirm()` starts the upcoming interval.

- [x] **1.18 Engine: transition modes "auto" and "mixed"**
  - `auto`: the next interval starts immediately after a completed interval.
  - `mixed`: a break starts automatically after a work interval; after a break the engine waits for confirmation before the next work interval.

### Recording

- [x] **1.19 Session and interval repository**
  - Create a flow session; start an interval (position, kind, category, planned seconds, start time); finish an interval (status, actual seconds, end time); finish a session (status, end time).
  - Intervals of a session are returned in order.
  - `last_flow_category_id()` returns the category of the most recent flow, or `None` when there was no flow.

- [x] **1.20 Recorder: engine to database**
  - A flow session and every interval it goes through are written to the database with correct status, positions and durations.
  - Verified by simulating a flow with a fake clock: complete a work interval, take a break, skip a work interval, stop.
  - Each step is written in one transaction.

- [x] **1.21 Startup recovery**
  - On startup, a session still marked `running` becomes `interrupted`, and its unfinished interval (status NULL) becomes `interrupted` with no actual duration.
  - Running it again, or on a clean database, changes nothing.

### UI

- [x] **1.22 App shell and navigation**
  - A main window titled "Timer" shows the home screen and a navigation bar (Categories, Settings).
  - Opening a secondary screen shows it inside the same window with a Back button; Back returns home.
  - Navigation state is tested without Tk; manual check: the window opens and navigation works.

- [x] **1.23 Hotkeys**
  - `Space` toggles pause (starts the flow when idle), `Enter` confirms the next interval, `Esc` goes back.
  - Hotkeys are ignored while a text field has focus, so typing a space in a name does not pause the timer.
  - The key mapping is tested without Tk; manual check: the keys work in the window.

- [x] **1.24a Data directory for development**
  - A release (frozen executable) keeps its data in `<base>/timer`; running from source keeps it in `<base>/timer-dev`, where `<base>` is `$XDG_DATA_HOME` or `~/.local/share`. The two never share a database, so a release can be used while the application is being developed.
  - `TIMER_DATA_DIR`, when set to an absolute path, is the data directory as it is, in either build (for one-off experiments with a clean database).
  - The window of a run from source is titled "Timer (dev)", a release's "Timer".
  - `docs/spec.md` and `docs/schema.md` describe the two directories.

- [x] **1.24 Categories screen: list and add**
  - Lists active categories with their color; `None` is shown too.
  - A form adds a category with a name and a color chosen in a color dialog; validation errors are shown next to the form.

- [x] **1.25 Categories screen: edit and archive**
  - A category can be renamed, recolored and archived from the list.
  - The `None` category has these controls disabled.

- [ ] **1.26 Settings screen**
  - Fields for the four timer values with their limits, the transition mode as three options each with the explanation from spec §4.3, and the blink checkbox.
  - Values are stored with an explicit Save button; invalid input is rejected with a message.

- [ ] **1.27 Home screen: start a flow**
  - A category selector shows active categories, preselected with the category of the previous flow if it is still active, otherwise `None`.
  - A Start button (and `Space`) starts the flow.
  - The preselection logic is tested without Tk.

- [ ] **1.28 Running screen**
  - Shows the interval name (the category name for a work interval, `SHORT BREAK` or `LONG BREAK`), the work interval number, the countdown as `mm:ss`, and Pause/Resume, Skip and Stop buttons.
  - The countdown is refreshed several times per second from the engine's clock; Stop asks for confirmation.

- [ ] **1.29 Waiting-for-confirmation screen**
  - While the engine waits, the screen shows what comes next (e.g. "Next: Work · 4") and a Next button (`Enter`).

- [ ] **1.30 Wire up the app**
  - `uv run timer` opens the main window using the real database in the data directory: creates it, applies migrations and runs startup recovery first.
  - Closing the window during an interval and starting again leaves that interval marked `interrupted`.

- [ ] **1.31 Close-out**
  - `docs/schema.md` matches the final schema; spec §19 is updated with the confirmed decisions; `AGENTS.md` layout section matches the code; the roadmap marks Stage 1 done.
  - Final manual check by the owner: a flow runs by the global rules in all three transition modes, history rows are written, and a restart loses no data.

## Decisions made while breaking down — to confirm

1. The assumptions 1–5 of spec §19 apply as written (they affect pieces 1.11, 1.12, 1.16, 1.21, 1.28).
2. Skip starts the next interval immediately in every transition mode (1.15).
3. Category names are unique ignoring case; `None` is listed first (1.6, 1.7).
4. An unknown localization key raises `KeyError` (1.1).
5. Changed settings apply to intervals that start afterwards; the Settings screen has an explicit Save button (1.13, 1.26).
6. Breaks have no category in history; an interrupted interval has no actual duration (1.6).
7. Visual UI behavior is accepted manually by the owner (see "How a piece is accepted").
8. The scenario tables are created in schema v1, so the schema is complete from the start; Stage 2 adds only code (1.6).
9. A scenario session keeps a copy of its scenario as JSON text plus the scenario name; it has no reference to the scenario, so deleting a scenario never breaks history (1.6).
10. An interval that is still running has status NULL (1.6, 1.21).
11. Value limits (spec §19.5) are enforced in code, not in the schema (1.11, Stage 2).
