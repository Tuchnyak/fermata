# Stage 4 — History screen: breakdown

Breakdown of [roadmap.md](roadmap.md) Stage 4. Requirements: [spec.md](spec.md) §13.
Branch: `feat/stage-4-history`. A piece is ticked when the owner has approved it and it is committed.
Accepted like [stage-3.md](stage-3.md): decisions first, tests and code together, one approval per piece, the visual part checked by the owner in one pass.
The data is already recorded and the schema (with the view `interval_details`) is ready: no migration is needed.

## Pieces

- [x] **4.1 The period and the query**
  - A pure model of the period: a day or a week (starting on Monday), the previous and the next one, today. The bounds are computed in the local time and converted to UTC, in which the database stores the times; tested with a given time zone.
  - `HistoryRepository`, read only: the finished work intervals that started in a period, from `interval_details`, in the order they started. A running interval (no status yet) and the breaks are left out.
  - `HistoryViewModel`: the rows to show (category color and name, start time, actual duration, status), the totals of actual time per category (longest first) and the total of the period, the title of the period, the texts of the buttons. Tested on a real SQLite in memory, without Tk.

- [x] **4.2 The History screen**
  - A History button in the navigation bar (`Screen.HISTORY`); `Esc` and Back lead home as from the other screens.
  - A Day / Week switch, the arrows to the previous and the next period, a Today button, the title of the period.
  - The list of work intervals (`ttk.Treeview` with a scroll bar): a smooth circle in the color of the category, the category name, the start time, the actual duration and the status. The totals under it: one line per category with its color, then the total of the period. An empty period says so.

- [ ] **4.3 Close-out**
  - `docs/schema.md` (the query behind the screen, if useful), `docs/spec.md` §13 and §19, `AGENTS.md` and the roadmap match the code.
  - Final manual check by the owner on real data; the development clock runs twice as fast, so its times are the sped-up ones.
  - After the owner's approval the branch is merged into `master` with `git merge --no-ff`, then deleted locally and on GitHub.

## Decisions made while breaking down — to confirm

1. An interval belongs to the day (or week) in which it started; one that runs past midnight is counted whole in the day it started.
2. Only finished work intervals are listed; the one running now appears when it ends.
3. `completed`, `skipped` and `stopped` intervals show their actual duration (pauses excluded) and count in the totals. An `interrupted` interval has no known duration: it is shown with a dash and is not in the totals.
4. The totals are per category, longest first, followed by one line with the total of the period (added to the spec by the owner's choice).
5. A Today button besides the arrows (added to the spec by the owner's choice).
6. The category in the list is the interval's category as it is named now (a renamed category shows its new name); an archived one is still shown.
7. The week is one flat list: the start of an interval is shown with its weekday (`Mon 12:30`), a day shows the time only. No grouping by day.
8. English texts: `Tue, 3 Nov 2026` for a day, `2 Nov – 8 Nov 2026` for a week (with both years when a week crosses New Year); durations as on the scenarios screen, `25m` and `1h 05m` (a length under a minute reads `0m`).
9. The category color in the list is the smooth circle of the progress row (`ui/circle_image.py`).
10. No index is added to `interval`: the amount of data does not need one; if it ever does, a migration adds it.
