# Stage 3 — Themes and fullscreen: breakdown

Breakdown of [roadmap.md](roadmap.md) Stage 3. Requirements: [spec.md](spec.md) §11 and §12.
Branch: `feat/stage-3-themes-fullscreen`. A piece is ticked when the owner has approved it and it is committed.
Accepted like [stage-2.md](stage-2.md): decisions first, tests and code together, one approval per piece, the visual part checked by the owner in one pass.

## Pieces

- [ ] **3.1 Themes**
  - Six themes defined by the application itself (`ThemeDefinition`s registered at startup): Light, Dark, Catppuccin Latte, Frappé, Macchiato and Mocha. The window no longer asks ttkbootstrap for the legacy name `darkly` (it warns that the name goes away in ttkbootstrap 3.0).
  - The setting `theme` (default Dark, spec §4.1) with a selector in Settings. Choosing a theme applies it at once and stores it at once, apart from the Save button of the other settings, so the owner sees the result while choosing. What is typed in Settings but not saved yet (sliders, mode, flags) survives the change of theme. The stored theme is used from the next start.
  - Storage: the table `setting` gets a row `theme` whose value is the id of the theme (`light`, `dark`, `catppuccin-latte`, `catppuccin-frappe`, `catppuccin-macchiato`, `catppuccin-mocha`); the palettes themselves are in the code, not in the database. A missing or unknown value means Dark. No migration is needed.
  - Everything that is drawn by hand follows the theme: the circle row, the category swatches, the number slider ticks, the hint texts.
  - Tested without Tk: the six themes are all defined and listed, an unknown stored theme falls back to Dark, and the text colors of every theme keep a readable contrast against its backgrounds (a computed check, so a hard-to-read palette cannot slip in).

- [ ] **3.2 Layout that scales**
  - The running, waiting and start screens grow with the window: the sizes of the fonts, of the circles and of the gaps follow the size of the window between a minimum and a maximum.
  - The rule (window size to sizes) is a pure function and is tested; the window gets a minimum size.

- [ ] **3.3 Fullscreen board**
  - `F11` and a button in the header toggle the fullscreen window; `Esc` leaves it first and only then goes back from a secondary screen.
  - In fullscreen the home screen is a board: only the interval, the countdown and the progress (the circle row, or the work interval counter in a flow), at the sizes of 3.2; the header and the buttons are hidden, `Space` and `Enter` keep working. A secondary screen opened in fullscreen looks as usual.
  - The key handling (`F11`, `Esc` order) is tested without Tk.

- [ ] **3.4 Window size and position remembered**
  - The size and position of the normal window are stored in the database (the setting `window_geometry`, not shown in Settings) when the window is closed, and restored at the next start. Fullscreen is never remembered: the application always starts in a normal window on the home screen. A window closed in fullscreen stores the size and position it had before, not the size of the screen.
  - A stored position that would put the window off the screen (another monitor, another resolution) is corrected to the screen.
  - The stored text is validated and an invalid or missing value means the default size; tested without Tk.

- [ ] **3.5 Close-out**
  - `docs/schema.md` (the settings `theme` and `window_geometry`), `docs/spec.md` §11, §12 and §19, `AGENTS.md` and the roadmap match the code.
  - Final manual check by the owner: all six themes on every screen, resizing, fullscreen and the restored window; the release build is refreshed by the owner's command (`./scripts/install-local.sh` from the release branch after it takes this stage).
  - After the owner's approval the branch is merged into `master` with `git merge --no-ff`.

## Decisions made while breaking down — to confirm

1. The Catppuccin palettes (Latte light; Frappé, Macchiato, Mocha dark) are taken from the official Catppuccin colors, Light and Dark are our own neutral palettes; the accent of every theme is its blue. The values are checked against the official palette when the piece is done.
2. The theme applies and is stored at once on selection (spec §12), while the other settings keep their Save button.
3. Fullscreen is a property of the window and is never stored; the board layout (header and buttons hidden) is for the home screen only, and an idle home screen in fullscreen shows the usual start screen without the header.
4. The window position is saved on close only, so a crash loses only the last move.
5. The font and circle sizes scale with the smaller of the window's width and height relative to the default window (720×680), with a lower and an upper limit.
6. Stage 3 is on `master` first; the installed release gets it only when the release branch takes it (the owner's choice).
