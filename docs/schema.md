# Timer — Database schema

The application keeps everything in one SQLite file: `$XDG_DATA_HOME/timer/timer.db`, by default `~/.local/share/timer/timer.db`.
A run from source (development) uses `timer-dev` instead of `timer`; `TIMER_DATA_DIR` replaces the directory in either build (see [spec.md](spec.md) §16).
The schema is created by the migrations in `src/timer/storage/migrations/`; the current version is stored in `PRAGMA user_version`.
Terms are defined in [spec.md](spec.md) §2.

Open the file read-only for your own analysis, e.g. `sqlite3 -readonly ~/.local/share/timer/timer.db` (`timer-dev` for the development database).
The application enforces foreign keys per connection (`PRAGMA foreign_keys = ON`); do the same if you write.

## Conventions

- Times are ISO-8601 UTC text, e.g. `2026-10-19T09:00:00Z`. They sort as text and work with SQLite's `date()` and `strftime()`.
- Durations are whole seconds (`*_seconds`) or whole minutes (`*_minutes`).
- Flags are `INTEGER` 0 or 1 (`is_*`).
- `NULL` means "not set / not finished / use the global value", as described per column below.

## Relations

```
category 1 ──< interval >── 1 session
    1
    └──< scenario_row >── 1 scenario        (a session keeps a copy of its scenario, not a reference)

setting                                      (standalone)
```

## Tables

### `setting`

Key → value store for global settings. Values are text: numbers in decimal (`30`), flags as `1` / `0`, modes as words (`mixed`).
Only settings the user has changed are stored; a missing key means the application's default applies.

| Key | Value | Default |
|---|---|---|
| `work_minutes` | work interval length, 1–120 | 25 |
| `short_break_minutes` | short break length, 1–30 | 5 |
| `long_break_minutes` | long break length, 1–60 | 15 |
| `long_break_every` | N: long break after every N-th work interval, 1–10 | 4 |
| `transition_mode` | `auto`, `confirm` or `mixed` | `confirm` |
| `blink` | blink the current circle, `1` / `0` | 1 |

The limits are enforced by the application when a setting is written, not by the schema.

Columns:

| Column | Type | Notes |
|---|---|---|
| `key` | TEXT | primary key |
| `value` | TEXT | not null |

### `category`

A user-defined label with a color. Categories are archived, never deleted.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | primary key |
| `name` | TEXT | not null; unique ignoring ASCII case in the database, the application compares names with Unicode case folding |
| `color` | TEXT | not null; `#rrggbb` |
| `is_system` | INTEGER | 1 only for the built-in `None` category (`id = 1`) |
| `is_archived` | INTEGER | 1 = hidden from selection, still referenced by history |

### `scenario`

A saved sequence of work intervals.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | primary key |
| `name` | TEXT | not null; unique ignoring ASCII case in the database, the application compares names with Unicode case folding |
| `repeat_count` | INTEGER | not null, at least 1: how many times the whole list of rows is repeated |
| `work_minutes` | INTEGER | override of the work interval length; NULL = use the global value |
| `short_break_minutes` | INTEGER | override; NULL = global |
| `long_break_minutes` | INTEGER | override; NULL = global |
| `long_break_every` | INTEGER | override of N (long break after every N-th work interval); NULL = global |

### `scenario_row`

One row of a scenario: a category and how many work intervals in a row.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | primary key |
| `scenario_id` | INTEGER | not null; references `scenario`; rows are deleted with their scenario |
| `position` | INTEGER | not null; order within the scenario, unique per scenario |
| `category_id` | INTEGER | not null; references `category` |
| `count` | INTEGER | not null, at least 1 |

### `session`

One execution from Start to the end: a flow or a scenario.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | primary key |
| `kind` | TEXT | `flow` or `scenario` |
| `status` | TEXT | `running`, `completed` (a scenario ran to its end), `stopped` or `interrupted` (app closed); an interrupted scenario session that is resumed becomes `running` again |
| `started_at` | TEXT | not null |
| `ended_at` | TEXT | NULL while running or when the app was closed; also NULL for an interrupted session the user then declined to resume (`stopped`, end unknown) |
| `scenario_name` | TEXT | name of the scenario at the start; NULL for a flow |
| `scenario_snapshot` | TEXT | copy of the scenario at the start, JSON; NULL for a flow |

`scenario_snapshot` is JSON, e.g. `{"name": "Work day", "rows": [{"category_id": 2, "count": 2}, {"category_id": 3, "count": 1}], "repeat_count": 2, "work_minutes": null, "short_break_minutes": null, "long_break_minutes": null, "long_break_every": null}`; the four timer values are `null` when the scenario does not override them. Categories are referenced by id (they are archived, never deleted).

A scenario session has both `scenario_name` and `scenario_snapshot`, a flow has neither. A session does not reference the scenario, so deleting or editing a scenario never changes history.

### `interval`

One circle: a work interval or a break. Together they are the history.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | primary key |
| `session_id` | INTEGER | not null; references `session` |
| `position` | INTEGER | not null; order within the session, unique per session |
| `kind` | TEXT | `work`, `short_break` or `long_break` |
| `category_id` | INTEGER | references `category`; set for `work`, NULL for breaks |
| `planned_seconds` | INTEGER | not null |
| `actual_seconds` | INTEGER | worked time without pauses; NULL while running and for `interrupted` |
| `started_at` | TEXT | not null |
| `ended_at` | TEXT | NULL while running |
| `status` | TEXT | NULL while running, then `completed`, `skipped`, `stopped` (session stopped during it) or `interrupted` (app closed during it; a resumed session starts a new row for the work interval, the interrupted one stays) |

## View

### `interval_details`

Every column of `interval` plus the related data, so queries need no joins:

| Column | Source |
|---|---|
| `category_name`, `category_color` | the interval's category; NULL for breaks |
| `session_kind` | `session.kind` |
| `scenario_name` | `session.scenario_name`; NULL for flows |

## Example queries

Worked time per category per week (weeks start on Monday):

```sql
SELECT date(started_at, 'weekday 0', '-6 days') AS week_start,
       category_name,
       SUM(actual_seconds) / 60 AS minutes
FROM interval_details
WHERE kind = 'work'
GROUP BY week_start, category_name
ORDER BY week_start, category_name;
```

Work intervals of one day with their outcome:

```sql
SELECT started_at, category_name, actual_seconds / 60 AS minutes, status
FROM interval_details
WHERE kind = 'work' AND date(started_at) = '2026-10-19'
ORDER BY started_at;
```

How many work intervals each scenario got through, by status:

```sql
SELECT scenario_name, status, COUNT(*) AS intervals
FROM interval_details
WHERE kind = 'work' AND session_kind = 'scenario'
GROUP BY scenario_name, status
ORDER BY scenario_name, status;
```
