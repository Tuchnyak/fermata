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
  - `data_dir()` returns `$XDG_DATA_HOME/timer` when the variable is set, otherwise `~/.local/share/timer`.
  - The directory is created if missing; calling again does not fail.
  - `db_path()` is `<data_dir>/timer.db`.

- [x] **1.3 Db helper: queries**
  - `Db.open(path)` opens a SQLite file or `:memory:`, with foreign keys enforced and rows readable by column name.
  - `execute` returns the number of affected rows; `insert` returns the new id.
  - `query` returns a list of objects built by the given mapper; `query_one` returns one object or `None`.
  - Named parameters (`:name` with a dict) work.
  - Violating a foreign key raises an error.

- [ ] **1.4 Db helper: transactions**
  - Changes made inside `with db.transaction():` are committed when the block ends normally.
  - An exception inside the block rolls everything back and is re-raised.
  - A nested transaction raises an error.
  - A statement outside a transaction block is committed immediately.

- [ ] **1.5 Migration runner**
  - On a fresh database, applies all `NNN_*.sql` files in order and sets `PRAGMA user_version` to the last number.
  - A second run changes nothing.
  - On an older database applies only the missing files.
  - A database whose version is newer than the known migrations is rejected without changes.
  - A failing migration is rolled back completely and the version stays unchanged.

- [ ] **1.6 Schema v1** (migration `001`)
  - Tables `setting`, `session_type`, `run`, `stage` (the Stage 1 part of spec §16; plan tables come with Stage 2).
  - `session_type`: name unique ignoring case; the system type `None` exists after migration.
  - `run.kind` is `flow` or `plan`; `run.status` is `running`, `stopped` or `interrupted` (`completed` is added with plans); `stage.kind` is `session`, `short_break` or `long_break`; `stage.status` is `completed`, `skipped`, `stopped` or `interrupted`. Values outside these are rejected.
  - Times are ISO-8601 UTC text. `stage.session_type_id` is NULL for breaks; `actual_seconds` is NULL for interrupted stages.
  - `docs/schema.md` documents every table and column and includes example analysis queries (e.g. worked time per type per week).

### Session types

- [ ] **1.7 Session types: create and read**
  - `create(name, color)` returns the new type; the name is trimmed and must not be empty; the color must look like `#rrggbb`; a duplicate name (ignoring case) is rejected.
  - `get(id)` returns any type, archived or not.
  - `list_active()` returns non-archived types, `None` first, then by name.

- [ ] **1.8 Session types: rename and recolor**
  - `update(id, name=…, color=…)` applies the same validation as create.
  - The system type and unknown ids are rejected.

- [ ] **1.9 Session types: archive**
  - `archive(id)` removes the type from `list_active()`; `get(id)` still returns it.
  - `unarchive(id)` brings it back.
  - The system type cannot be archived.
  - The rule "not while a plan uses it" is added in Stage 2, when plans exist.

### Settings

- [ ] **1.10 Settings store**
  - `get_all()` returns typed settings: session, short break and long break minutes, long break interval N, transition mode, blink flag; defaults are those of spec §4.1 when nothing is stored.
  - `set(key, value)` persists the value; it is still there after reopening the database.
  - Theme and sound settings arrive with their own stages.

- [ ] **1.11 Settings validation**
  - Minutes must be 1–180 and N must be 1–20.
  - Transition mode must be one of `auto`, `confirm`, `mixed`.
  - An invalid value or an unknown key raises an error and stores nothing.

### Timer engine (pure logic, no UI, no database)

- [ ] **1.12 Stage sequencing**
  - After a session comes a short break; after every N-th session a long break instead; after a break comes a session.
  - Skipped sessions count toward N.
  - With defaults the order is: session, short, session, short, session, short, session, long, session, …
  - Lengths come from the given timer settings.

- [ ] **1.13 Engine: running a stage**
  - Starting a flow with a session type begins a session of the configured length.
  - The remaining time is computed from an injected clock (no tick counting, so no drift).
  - When the planned time has elapsed the stage completes with actual time equal to planned.
  - Settings are read when a stage starts: a change affects only stages that start afterwards.

- [ ] **1.14 Engine: pause and resume**
  - While paused the remaining time does not change and the paused time is not counted as worked time.
  - Resume continues the countdown; pausing an already paused stage has no effect.

- [ ] **1.15 Engine: skip**
  - Skipping a session ends it as `skipped` with the time actually elapsed, and the next stage (per 1.12) starts immediately.
  - Skipping a break ends it as `skipped`, and the next session starts immediately.
  - Skip starts the next stage immediately in every transition mode.

- [ ] **1.16 Engine: stop**
  - Stop ends the current stage as `stopped` with the time actually elapsed and ends the flow; the engine becomes idle.
  - Stop while idle has no effect.

- [ ] **1.17 Engine: transition mode "confirm"**
  - When a stage completes, the engine enters a waiting state that exposes the upcoming stage (kind, type, length); no time is counted.
  - `confirm()` starts the upcoming stage.

- [ ] **1.18 Engine: transition modes "auto" and "mixed"**
  - `auto`: the next stage starts immediately after a completed stage.
  - `mixed`: a break starts automatically after a session; after a break the engine waits for confirmation before the next session.

### Recording

- [ ] **1.19 Run and stage repository**
  - Create a flow run; start a stage (position, kind, type, planned seconds, start time); finish a stage (status, actual seconds, end time); finish a run (status, end time).
  - Stages of a run are returned in order.
  - `last_flow_type_id()` returns the session type of the most recent flow, or `None` when there was no flow.

- [ ] **1.20 Recorder: engine to database**
  - A flow run and every stage it goes through are written to the database with correct status, positions and durations.
  - Verified by simulating a flow with a fake clock: complete a session, take a break, skip a session, stop.
  - Each step is written in one transaction.

- [ ] **1.21 Startup recovery**
  - On startup, a run still marked `running` becomes `interrupted`, and its unfinished stage becomes `interrupted` with no actual duration.
  - Running it again, or on a clean database, changes nothing.

### UI

- [ ] **1.22 App shell and navigation**
  - A main window titled "Timer" shows the home screen and a navigation bar (Types, Settings).
  - Opening a secondary screen shows it inside the same window with a Back button; Back returns home.
  - Navigation state is tested without Tk; manual check: the window opens and navigation works.

- [ ] **1.23 Hotkeys**
  - `Space` toggles pause (starts the flow when idle), `Enter` confirms the next stage, `Esc` goes back.
  - Hotkeys are ignored while a text field has focus, so typing a space in a name does not pause the timer.
  - The key mapping is tested without Tk; manual check: the keys work in the window.

- [ ] **1.24 Types screen: list and add**
  - Lists active types with their color; `None` is shown too.
  - A form adds a type with a name and a color chosen in a color dialog; validation errors are shown next to the form.

- [ ] **1.25 Types screen: edit and archive**
  - A type can be renamed, recolored and archived from the list.
  - The `None` type has these controls disabled.

- [ ] **1.26 Settings screen**
  - Fields for the four timer values with their limits, the transition mode as three options each with the explanation from spec §4.3, and the blink checkbox.
  - Values are stored with an explicit Save button; invalid input is rejected with a message.

- [ ] **1.27 Home screen: start a flow**
  - A session type selector shows active types, preselected with the type of the previous flow if it is still active, otherwise `None`.
  - A Start button (and `Space`) starts the flow.
  - The preselection logic is tested without Tk.

- [ ] **1.28 Running screen**
  - Shows the stage name (the session type name, `SHORT BREAK` or `LONG BREAK`), the session number, the countdown as `mm:ss`, and Pause/Resume, Skip and Stop buttons.
  - The countdown is refreshed several times per second from the engine's clock; Stop asks for confirmation.

- [ ] **1.29 Waiting-for-confirmation screen**
  - While the engine waits, the screen shows what comes next (e.g. "Next: Work session 4") and a Next button (`Enter`).

- [ ] **1.30 Wire up the app**
  - `uv run timer` opens the main window using the real database in the data directory: creates it, applies migrations and runs startup recovery first.
  - Closing the window during a stage and starting again leaves that stage marked `interrupted`.

- [ ] **1.31 Close-out**
  - `docs/schema.md` matches the final schema; spec §19 is updated with the confirmed decisions; `AGENTS.md` layout section matches the code; the roadmap marks Stage 1 done.
  - Final manual check by the owner: a flow runs by the global rules in all three transition modes, history rows are written, and a restart loses no data.

## Decisions made while breaking down — to confirm

1. The assumptions 1–5 of spec §19 apply as written (they affect pieces 1.11, 1.12, 1.16, 1.21, 1.28).
2. Skip starts the next stage immediately in every transition mode (1.15).
3. Session type names are unique ignoring case; `None` is listed first (1.6, 1.7).
4. An unknown localization key raises `KeyError` (1.1).
5. Changed settings apply to stages that start afterwards; the Settings screen has an explicit Save button (1.13, 1.26).
6. Breaks have no session type in history; an interrupted stage has no actual duration (1.6).
7. Visual UI behavior is accepted manually by the owner (see "How a piece is accepted").
