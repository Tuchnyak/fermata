# Timer — Specification

Pomodoro timer for tracking work intervals, run on a dedicated second laptop.
This document records the agreed requirements and decisions. Stage order lives in [roadmap.md](roadmap.md).

## 1. User and goal

The first user is the author. The timer stays open on a second laptop and shows:

- which interval is running now, of which category (project), and how much time is left;
- how the planned "budget" of work intervals is going: how many are done, skipped, and ahead.

Work intervals are grouped into **Scenarios** that are designed in advance and started in one action, like putting a playlist into a play queue. A plain endless pomodoro (**Flow**) is also available.

## 2. Glossary

| Term | Meaning |
|---|---|
| **Interval** | Any timed span, one circle: a work interval or a break. |
| **Work interval** | An interval of work in one category. |
| **Break** | A short or long rest interval. Breaks are never placed by hand (see §5). |
| **Category** | A user-defined label (project) with a name and a color, e.g. "Work", "Personal". |
| **Scenario** | A saved sequence of work intervals: rows of "category × count", repeated N times, with optional timer overrides. |
| **Session** | One execution from Start to the end, made of intervals: a flow session or a scenario session. |
| **Scenario session** | A session of a scenario, based on a snapshot of the scenario taken at start. |
| **Flow** | Endless mode: work interval → break → work interval … until stopped. One category for the whole flow. |

## 3. Categories

- The user manages the list: create, rename, change color (color picker dialog), archive.
- Names are unique, ignoring case.
- `None` is a system category: always present, cannot be renamed, archived or deleted.
- Categories are **archived, never deleted**. An archived category:
  - is hidden from category selection in the scenario editor and the flow start;
  - keeps its name and color in history.
- A category **cannot be archived while any scenario uses it**. The UI says which scenarios use it.

## 4. Timer settings

### 4.1 Global settings

| Setting | Default |
|---|---|
| Work interval length | 25 min |
| Short break length | 5 min |
| Long break length | 15 min |
| Long break every N-th work interval (N) | 4 |
| Transition mode | Wait for confirmation |
| Blink current circle | On |
| Theme | Dark |
| Sound notifications | On (available from the sound stage) |

Durations are whole minutes.

### 4.2 Scenario overrides

A scenario may override all four timer parameters: work interval length, short break length, long break length, N. Without an override the global values apply. The transition mode is global only.

### 4.3 Transition modes

What happens when an interval ends. Each mode is shown in Settings with a short explanation for the user:

| Mode | User-facing explanation |
|---|---|
| **Auto-start** | "The next interval starts automatically." |
| **Wait for confirmation** | "The timer stops after each interval and waits until you press Next." |
| **Mixed** | "Breaks start automatically. Work intervals wait for you, so time doesn't run while you're away." |

While waiting, the main screen shows what comes next (e.g. "Next: Work · 4/6") and a **Next** button (`Enter`).

## 5. Break rules

The same rules apply to Flow and Scenarios:

- a **short break** follows every work interval;
- a **long break** replaces the short break after every N-th work interval (strictly by N, also inside scenarios — to align long breaks with scenario repetitions, override N in the scenario);
- in a scenario, **no break follows the last work interval**.

## 6. Flow mode

- Endless cycle of work intervals and breaks by the global rules until the user stops it.
- Before start the user picks a category. Preselected: the category of the previous flow, or `None` if there was none.
- Instead of the circle row the screen shows a work interval counter.

## 7. Scenarios

### 7.1 Structure

- A scenario has a name (unique, ignoring case), an ordered list of **rows** (category + number of consecutive work intervals), a **repeat count** for the whole list, and optional timer overrides (§4.2).
- Example: rows `Work × 2`, `Personal × 1`, repeat `× 2` → 6 work intervals.

### 7.2 Scenario editor

```
┌ Edit scenario ─────────────────────────────────────┐
│ Name: [ Work day                               ]   │
│                                                    │
│      Category             Intervals                │
│  1   ■ [ Work       ▾ ]   [ 2 ▴▾ ]   [↑] [↓] [✕]  │
│  2   ■ [ Personal   ▾ ]   [ 1 ▴▾ ]   [↑] [↓] [✕]  │
│  [+ Add row]                                       │
│                                                    │
│  Repeat:  [ 2 ▴▾ ] ×                               │
│                                                    │
│  Preview:  ○ ○ ○ ○     ○ ○                         │
│            6 work intervals · ~3h 05m              │
│                                                    │
│  ▸ Timer settings (override global)                │
│                                                    │
│                 [Cancel]  [Save]  [Save & start]   │
└────────────────────────────────────────────────────┘
```

- Each row: color swatch of the category, category selector, work interval count, move up/down, delete.
- **Preview** updates live: the same circle row as in the running timer (§9), with gaps where long breaks fall.
- **Total duration**: all work intervals plus the breaks between them (no break after the last work interval), using the effective timer settings.
- **Timer settings** is a collapsed section with the four overrides; collapsed means "global settings are used".
- **Save & start** saves the scenario and starts a session immediately.

### 7.3 Scenarios screen

List of saved scenarios: create, edit, delete (with confirmation), start.

### 7.4 Running a scenario

- Only **one session** at a time. No queue of scenarios.
- Starting a session takes a **snapshot** of the scenario. Editing the scenario during a session is allowed; changes apply from the next session. The current session, resume (§10) and history use the snapshot.
- When the last work interval ends, the session finishes immediately and shows a summary, e.g. "Scenario complete: 5 done, 1 skipped". Then the timer returns to idle.

## 8. Controls

### 8.1 During an interval

| Control | Behavior |
|---|---|
| **Pause / Resume** | No time limit. Paused time is not counted as worked time. |
| **Skip** | Ends the current interval early and moves to the next one. No confirmation. |
| **Stop** | Ends the whole session (scenario or flow). Asks for confirmation. |

### 8.2 Hotkeys

| Key | Action |
|---|---|
| `Space` | Pause / Resume; Start when idle |
| `Enter` | Next, when waiting for confirmation |
| `F11` | Toggle fullscreen |
| `Esc` | Exit fullscreen; back from a secondary screen |

Skip and Stop have no hotkeys on purpose: an accidental press is too costly.

## 9. Scenario progress visualization

A row of circles, one circle per work interval of the session. Short breaks are not shown.

| State | Look |
|---|---|
| Done | Filled with the category color |
| Skipped | Muted (faded) fill of the category color |
| Current | Edged with the category color, the fill blinks between the full color and a dimmed one (can be turned off in Settings, then the fill stays dimmed) |
| Future | Outline in the category color |

A long break is shown as a gap one empty circle wide, so work intervals are visually grouped between long breaks.

## 10. Resume after interruption

- The session state is saved to the database at every interval transition.
- If the app was closed during a scenario session (crash, reboot, closed window), on next start it asks: "Resume scenario "X" from interval 4 of 6?".
  - **Yes**: the session continues; the interrupted work interval starts again from the beginning. The interrupted interval stays in the history as `interrupted`, the new one is a new row of the same session. If the app was closed in a break or while waiting for confirmation, the next work interval starts at once and the break is not repeated.
  - **No**: the session is ended as stopped (when it ended stays unknown).
  - Only the latest session is offered, and only a scenario session; a question closed without an answer is asked again at the next start. A flow is never resumed.

## 11. Main window

```
┌ Timer ─────────────────────────────────────────────────┐
│ [Scenarios] [Categories] [History] [Settings]   [⛶]    │
│                                                        │
│                       WORK · 3/6                       │
│                                                        │
│                         18:42                          │
│                                                        │
│                  ●  ●  ◉     ○  ○  ○                   │
│                                                        │
│            [⏸ Pause]   [⏭ Skip]   [⏹ Stop]             │
└────────────────────────────────────────────────────────┘
```

Idle state, instead of the controls:

```
   Flow                          Scenario
   ──────────────────────        ──────────────────────
   Category                      Scenario
   [ Work             ▾ ]        [ Work day         ▾ ]

        [ Start ]                     [ Start ]
```

- Two columns, each with its own Start button: the Flow column chooses a category, the Scenario column a saved scenario (disabled while there is none). `Space` starts the kind touched last, a flow at first.
- After a scenario that ran to its end, a summary line stands above the columns (§7.4) until the next session starts.

- The center shows the interval (for work intervals — the category name; for breaks `SHORT BREAK` or `LONG BREAK`), the work interval number, a large countdown and the circle row (scenario) or work interval counter (flow).
- Scenarios, Categories, History and Settings open **inside the main window** with a Back button. No secondary windows.
- One layout that **scales with the window**: the countdown and fonts grow with the window size.
- **Fullscreen board** (`[⛶]` / `F11`): only the interval, the countdown and the progress; controls are hidden, hotkeys keep working. `Esc` exits. The board is the home screen only: a secondary screen opened in fullscreen looks as usual, and `F11` works there too, also while a text field has the focus.
- The window remembers its size and position between launches (the setting `window_geometry`, written when the window is closed). Fullscreen is never remembered: the application always starts in a normal window on the home screen, and a window closed in fullscreen stores the size and position it had before. A stored position off the screen (another monitor, another resolution) is moved onto the screen.
- The application shows its **version** in the UI (in Settings) and prints it for `--version`; it is the version of `pyproject.toml`.
- The application has an **icon**: the window icon and the icon of its launcher entry. The picture is chosen by the owner.

## 12. Themes

- Six built-in themes: Light, Dark, Catppuccin Latte, Catppuccin Frappé, Catppuccin Macchiato, Catppuccin Mocha.
- Selected in Settings, applied and stored immediately, without the Save button of the other settings (what is typed there but not saved survives the change). The OS theme is not followed. Dark is the default.
- The Catppuccin palettes are the official ones; Light and Dark are the application's own neutral palettes. The accent of every theme is its blue.
- The theme provides the accent color (current circle) and neutral colors; category colors are the user's own.
- A theme editor is in the backlog (see roadmap).

## 13. History

### 13.1 What is recorded

Every interval — work intervals **and** breaks — of every session:

- kind (work / short break / long break), category;
- start and end time;
- planned duration, actual duration (pauses excluded);
- status: `completed`, `skipped`, `stopped` (session stopped during the interval), `interrupted` (app closed during the interval; actual duration unknown);
- the session it belongs to: a scenario session (with the scenario name from the snapshot) or a flow.

### 13.2 History screen

- Toggle Day / Week (week starts on Monday), previous/next navigation.
- List of **work intervals** with category color, category name, start time, actual duration and status.
- Totals of actual time per category for the selected period.
- Breaks are stored in the database but not shown on this screen.

### 13.3 Own analysis

The database schema is documented so the user can query history directly (`sqlite3`, DBeaver, Python).

## 14. Sound

- A calm, unobtrusive sound on every interval transition.
- One global on/off switch.
- Tkinter has no cross-platform audio; the playback method (library or a system command such as `paplay`) is chosen at that stage.
- First cut (interim release 0.2): one sound for the end of a work interval and one for the end of a break, played when the time runs out; Skip and Stop are silent. The files are chosen by the owner and kept in `src/timer/sounds/`. On Linux a system command plays them in the background: the first of `paplay`, `pw-play`, `ffplay`, `aplay` that is installed and knows the format. No file or no player means no sound. The Settings check box "Sound notifications" is the global switch.

## 15. Localization

- All UI strings go through one lookup function, e.g. `t("scenario.start")`.
- English only for now, stored as one dictionary/file of keys. Adding a language = adding a file with the same keys.
- No OS locale detection, plural rules or `gettext` until a second language exists. The language setting appears only then.

## 16. Data storage

Everything is stored in one SQLite database (`sqlite3` from the standard library):
`$XDG_DATA_HOME/timer/timer.db`, by default `~/.local/share/timer/timer.db`.

That is the database of a release. A run from source (development) uses `timer-dev` instead of `timer`, so development never touches the data of an installed release. The environment variable `TIMER_DATA_DIR`, when set to an absolute path, replaces the whole directory in either build.

A run from source also runs its clock twice as fast, so that intervals can be tested quickly; the window title says "(dev, ×2)". `uv run timer --real-time` restores the normal speed. A release has neither the speed-up nor the option. The times stored in a development database are the sped-up ones, so which session is the latest is decided by the order of creation, not by the time.

It holds settings, categories, scenarios, the state of the current session and history. The complete schema is created in stage 1 (stage 2 adds code for scenarios, not tables) and documented in `docs/schema.md`.

| Entity | Content |
|---|---|
| `setting` | key → value |
| `category` | name, color, system flag, archived flag |
| `scenario`, `scenario_row` | name, repeat count, overrides; rows: position, category, count |
| `session` | flow or scenario, scenario name and snapshot, start/end, status |
| `interval` | session, position, kind, category, planned/actual duration, start/end, status |
| `interval_details` (view) | intervals with category name and color, session kind and scenario name |

## 17. Technical constraints

- Linux only. Other OS builds are out of scope for now.
- Python 3.12, Tkinter + ttkbootstrap, ttk widgets only (classic `tk` widgets only where ttk has no equivalent, e.g. `Canvas`).
- uv for dependencies and running; `src/` layout; entry point `timer = "timer.app:main"`.
- Timer logic is kept separate from the UI and covered by pytest tests.
- Packaging (PyInstaller) and CI come last.

## 18. Explicitly not doing

Not part of the product unless a real need appears (see roadmap backlog for the deferred ones):

- restart the current interval, "+5 minutes";
- a queue of scenarios;
- per-scenario transition mode; per-category work interval length;
- nested groups in scenarios; breaks placed by hand;
- always-on-top window, tray icon, desktop notifications;
- following the OS theme.

## 19. Assumptions to confirm

Decided while writing. All of them are confirmed and implemented: items 1–5 and 7–9 in Stage 1, items 6 and 10–13 in Stage 2, items 14–17 in Stage 3:

1. Skipped work intervals count toward N for long breaks (the break pattern stays as previewed).
2. Skipping a break moves straight to the next work interval.
3. Stop asks for confirmation in Flow too, not only in scenarios.
4. Flow is not resumed after an interruption; the interrupted interval is recorded as `interrupted`.
5. Value limits: work interval 1–120 min, short break 1–30 min, long break 1–60 min, N 1–10, row count 1–20, repeat 1–20. Enforced in application code, not in the schema. The settings screen offers time values in steps of 5 minutes (from 5), N in steps of 1.
6. Deleting a scenario keeps its sessions in history (the scenario name comes from the snapshot; sessions do not reference the scenario).
7. The timer settings are read when an interval starts, so a change applies to the intervals that start afterwards; the transition mode is read when an interval ends.
8. Stop asks for confirmation also while the app waits for the next interval, where it ends the flow.
9. The timer counts by the system (wall) clock, not a monotonic one: the remaining time is computed from the clock, so it does not drift, and an interval keeps running while the computer sleeps. A manual change of the system time shifts the countdown.
10. A scenario row holds 1–20 work intervals and a scenario repeats 1–20 times; the number of rows is not limited beyond at least one. The overrides have the ranges of the matching global settings; the editor lets each one be switched on separately.
11. Skipping the last work interval of a scenario ends the session like completing it: no break follows, and the interval counts as skipped in the summary.
12. The summary of a scenario is shown on the home screen only when it ran to its end, and stays there until the next session starts; Stop shows no summary.
13. A scenario can be started only while the timer is idle. Editing or deleting it while its session runs is allowed and changes nothing for that session, which uses its snapshot: the overrides in the snapshot are fixed, the values that are not overridden are read from the global settings when an interval starts.
14. The theme is applied and stored when it is chosen, not on Save; the palettes are in the code and the database holds only the id of the theme.
15. Fullscreen is a property of the window and is never stored. The board layout is for the home screen only; a window that is left fullscreen by the window manager, not by our keys, is not noticed.
16. The fonts and circles scale with the smaller of the window's width and height relative to the default window (720×680), between 0.7 and 4 times.
17. The window geometry is written on close only, so a crash loses only the last move. The window manager puts the frame at the position asked for while Tk reports the position below the title bar; the application measures the difference after the window is shown and takes it off when storing, so the window does not creep down at every start.
