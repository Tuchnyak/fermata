# Stage 2 — Scenarios: breakdown

Breakdown of [roadmap.md](roadmap.md) Stage 2. Requirements: [spec.md](spec.md) §4.2, §5, §7, §9, §10.
Branch: `feat/stage-2-scenarios`. A piece is ticked when the owner has approved it and it is committed.

## How a piece is accepted

Larger pieces than in Stage 1, one owner approval per piece:

1. **Decisions first.** At the start of a piece the agent lists the decisions the owner is likely to have an opinion on (names, formats, behavior). The owner answers "ok" or corrects; then the agent works without stopping.
2. **Tests and code together.** The agent writes the acceptance tests first and sees them fail (stub, then red run) for itself, then implements. The owner gets one report: the tests, the code, the green run and the manual check list. The owner reviews the tests as acceptance tests.
3. **Several commits per piece** (storage, view model, widgets…) are fine; the owner approves the piece as a whole, and the `[x]` below is ticked in the last commit of the piece.
4. UI pieces end with one **manual check list** that the owner runs in a single pass.
5. Logic is tested on real SQLite in memory and a fake clock, no mocks; view models are tested without Tk (see [stage-1.md](stage-1.md)).

## Pieces

- [x] **2.1 Scenario storage and rules**
  - `Scenario` (name, rows of category × count, repeat count, four optional timer overrides) and `ScenarioRepository`: create, update, get, list, delete.
  - Validation: the name is trimmed, not empty, unique with Unicode case folding; at least one row; row count and repeat count 1–20; every category exists and is not archived; an override has the range of the matching global setting (spec §19.5).
  - Pure helpers: the flat list of work categories (rows × repeat), the effective settings (global with the overrides applied), the total duration (all work intervals plus the breaks between them, no break after the last one), the snapshot as JSON text and back.
  - `CategoryRepository.archive` is refused while a scenario row uses the category (the rule left open in 1.9).
  - Deleting a scenario deletes its rows; sessions in history keep their snapshot.

- [x] **2.2 Scenario session in the engine and the recorder**
  - `Engine.start_scenario(scenario)` runs the work intervals of the scenario in order, with the effective settings of the snapshot; breaks follow the global rules (§5), long breaks strictly by N.
  - No break after the last work interval: when it ends, completed or skipped, the session finishes at once. The engine exposes what the summary needs (done and skipped counts).
  - Pause, skip, stop and the three transition modes work as in a flow.
  - The recorder writes a scenario session (kind, scenario name, snapshot) with its intervals, and `completed` as the session status when the scenario ran to the end.
  - A flow behaves exactly as before.

- [x] **2.3 Progress circles, scenarios screen and editor**
  - A pure model of the circle row (§9): one circle per work interval with the states done, skipped, current and future, the category color, and a gap one circle wide where a long break falls (never after the last circle); the lines wrap to the width of the window. The `Canvas` widget draws it; the blinking of the current circle comes with the running screen in 2.4.
  - The scenarios screen: the list of scenarios with their size (`6 work intervals · ~3h 05m`), create, edit, delete (with confirmation) and start (disabled while a session runs). A new "Scenarios" button in the navigation bar.
  - The editor (§7.2): name, rows with category selector, count, move up/down and delete, repeat count, live preview (the circle row, the number of work intervals and the total duration), the collapsed section with the four overrides (each one switched on by its own check box, a field with arrow buttons; switched off means the global value), and Cancel, Save and Save & start in the window header next to Back. Validation errors are shown in the form.

- [x] **2.4 Running a scenario in the window**
  - The idle screen offers Flow or Scenario (§11): a category selector for Flow, a scenario selector for Scenario; Start and `Space` start the chosen one.
  - The running screen of a scenario shows `WORK · 3/6` and the circle row (the current circle blinks unless turned off in Settings) where a flow shows the work interval counter; the waiting screen names the next interval as `Next: Work · 4/6`.
  - When the session finishes, a summary is shown (e.g. "Scenario complete: 5 done, 1 skipped"), then the timer returns to idle.
  - Editing or deleting a scenario during its session is allowed and changes nothing for the running session.

- [x] **2.5 Resume after interruption**
  - On start, after startup recovery, a scenario session that was interrupted asks "Resume scenario "X" from interval 4 of 6?" (§10).
  - Yes: the same session continues from the snapshot; the interrupted work interval starts again from the beginning and is recorded as a new interval, the interrupted one stays `interrupted`. No: the session ends as `stopped`. A flow is never resumed.
  - Verified by simulating a crash in the middle of a work interval and of a break, then starting again.

- [x] **2.6 Close-out**
  - `docs/schema.md`, `docs/spec.md` §19 and `AGENTS.md` match the code; the roadmap marks Stage 2 done.
  - Final manual check by the owner: the example scenario `(Work × 2, Personal × 1) × 2` is built, run, interrupted, resumed and finished with a correct summary.
  - After the owner's approval the branch is merged into `master` with `git merge --no-ff`.

## Decisions made while breaking down — to confirm

1. Limits: row count (the number of intervals in one row) 1–20, repeat count 1–20 as in spec §19.5. The number of rows in a scenario is not limited beyond "at least one" (2.1).
2. The snapshot contains the scenario's own overrides; the values that are not overridden are read from the global settings when an interval starts, as in a flow (2.2).
3. Skipping the last work interval ends the session: it is counted as skipped in the summary and no break follows (2.2).
4. The summary is shown only when the scenario ran to the end; Stop shows no summary (2.4).
5. Resume continues the same session row. If a break was interrupted, the session resumes with the next work interval; breaks are not repeated (2.5).
6. Names are compared with Unicode case folding in code, as `docs/schema.md` already says; the database only knows ASCII case (2.1).
7. Fullscreen and `F11` stay in Stage 3 (roadmap), not here.
