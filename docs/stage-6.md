# Stage 6 — Packaging and CI: breakdown

Breakdown of [roadmap.md](roadmap.md) Stage 6. Requirements: [spec.md](spec.md) §11 (the version and the icon).
Branch: `feat/stage-6-packaging`. A piece is ticked when the owner has approved it and it is committed.
Accepted like [stage-5.md](stage-5.md): decisions first, tests and code together, one approval per piece.
What is already there from [release-0.2.md](release-0.2.md): the PyInstaller build and `scripts/install-local.sh`. This stage adds the version in the program, the choice of the language, the name Fermata with its icon and a CI pipeline.

## Pieces

- [x] **6.1 The version in the program**
  - The version is read from the package metadata (`importlib.metadata`), so `pyproject.toml` stays the only place where the number is written. A test compares what the program reports with `pyproject.toml`.
  - `timer --version` prints `timer 0.5.0` and exits, in a run from source and in the built executable.
  - Settings shows the version right after its title in the header: `Version 0.5.0`, in a smaller font and a less contrasting color than the rest of the screen (a faded text color, readable in all six themes: a test checks the contrast). It is in the header, not in a line of its own, because the screen has no room for another line at the default window size.
  - The build carries the metadata by itself: PyInstaller sees the `version("timer")` call (a build without the `--copy-metadata` flag was tried and reports the version), so no flag is added; verified by running the built executable with `--version`, and guarded by the CI check of 6.5.

- [x] **6.2 Choosing the language**
  - Added at the owner's request, before the icon. The setting `language` and a list in Settings (on the line of the theme); the languages are English (the default), Russian, Spanish, Portuguese (Brazilian), German, Chinese (Simplified) and Japanese. Spec §15 said the language setting appears when a second language does: this is that stage. This piece makes the mechanics and the first two catalogs, English and Russian; each language is added to the list when its catalog is.
  - The list names every language in that language (`English`, `Русский`); the choice is stored and applied at once, like the theme: the screen is drawn again, and what was typed in Settings but not saved yet is kept.
  - One catalog file per language, `locales/<code>.json`, with the keys and the `{placeholders}` of `en.json`; a text a language lacks is shown in English. A test fails when a catalog lacks a key, has an extra one or changes the placeholders.
  - The plural forms of the scenario line are avoided by wording: `Work intervals: 3 · ~1h 15m`, one key per language. The lengths of time (`25m`, `1h 05m`) are catalog texts too.
  - The Yes / No buttons of the questions are named in the language (`ui/dialogs.py`); the line-of-text and color dialogs of ttkbootstrap speak the language through the library's own catalog, to which the Russian texts we use are added (`ui/library_locale.py`).
  - The names of the categories and scenarios are the user's data and are not translated (the system category stays `None`).

- [x] **6.3 The other languages**
  - Spanish, Portuguese (Brazilian), German, Chinese (Simplified) and Japanese catalogs, each with the keys and placeholders of `en.json` (the test of 6.2 holds them to it); the five join the list of Settings, which now has seven languages. The translations are written by the agent and are not checked by native speakers; this is said in the docs. Russian is the owner's to read.
  - The date titles follow each language's order (`2026年11月4日(水)`, `Mi, 4. Nov 2026`), and so do the lengths of time (`3 Std. 05 Min.`, `3時間05分`).
  - The line-of-text and color dialogs of ttkbootstrap speak all seven languages: the library has its own translations for Spanish, Portuguese, German and Japanese, and the Chinese ones it lacks (the color chooser) are added next to the Russian ones.
  - Checked on screens of the owner's laptop kind: every language fits the Settings screen (the tightest one) and the list of the History, and Chinese and Japanese text is drawn by the system's CJK font.

- [x] **6.4 The name: Fermata**
  - Worked out with the owner in a brainstorm. The program is called **Fermata**: in music a fermata is a pause held as long as the performer chooses, which is what the mode "Wait for confirmation" does, and its sign (a dot under an arc) is the icon. The line under the name is "Fermata — focus timer with scenarios", translated in every language ("Фермата" is not: the name is the same everywhere; in Russian the line is "фокус-таймер со сценариями"). "Pomodoro" stays out of the name and the line: it is claimed as a trademark.
  - The window title is `Fermata` in every language (`Fermata (dev)` from source). The launcher entry: `Name=Fermata`, `GenericName=Focus timer`, `Comment=Focus timer with scenarios`, with the line in all seven languages (`Comment[ru]=…`). The text of the entry is made by a small module from the catalogs, so it is tested.
  - Everything technical takes the name too: the Python package `timer` becomes `fermata` (`src/fermata`, `tests/fermata`), the project in `pyproject.toml` is `fermata-timer` (`fermata` is taken on PyPI), the command is `fermata`, `--version` prints `fermata 0.5.0`, the data folders are `~/.local/share/fermata` and `fermata-dev` (the file is `fermata.db`, the variable that overrides the folder `FERMATA_DATA_DIR`), the built program is `~/.local/bin/fermata` with `fermata.desktop`.
  - No code moves the data: the owner is the only user. When the new program is installed, the agent shows and, after the owner's yes, runs the commands that move `~/.local/share/timer` and `timer-dev` to the new names and delete the old `~/.local/bin/timer` and `timer.desktop`.
  - The repository is renamed on GitHub with `gh repo rename fermata` (GitHub redirects the old address) and `origin` is changed, after the owner's go-ahead at that moment.

- [x] **6.5 The icon**
  - Chosen with the owner in the brainstorm, from twenty drafts: "Sunset". A tile of warm white `#f7f4ee` with rounded corners; a red sun `#bc002d`, which is the dot of the fermata, setting behind a black horizon `#1b1b1b` that fills the bottom of the tile; above it the musical arc in the same black, thick in the middle and thin at the ends. The colors are the program's sign and do not follow the theme. On a very dark panel the black horizon merges with the panel: seen and accepted by the owner.
  - The exact shape (in a 128-unit square): the tile from 4 to 124 with a corner radius of 26; the sun at (64, 92) with a radius of 24; the horizon from y = 96 down; the arc an outer half circle of radius 38 and an inner half ellipse 33.5 wide and 25 high, both standing on y = 70 around x = 64 (so the middle is 13 thick, the ends 4.5).
  - One script, `scripts/make_icon.py`, holds that shape and writes both files from it: `src/fermata/icons/fermata.svg` and `fermata.png` (256 px, drawn larger and scaled down, as the circles of the program are). Both are committed; the script is run again only if the icon changes. No SVG renderer is needed.
  - The PNG is the window icon (Tk `iconphoto`; Tk 8.6 cannot read SVG). The install script puts the SVG into `~/.local/share/icons/hicolor/scalable/apps/fermata.svg` and the PNG into `…/256x256/apps/fermata.png`; the entry says `Icon=fermata`. The build carries the PNG.
  - Tested: the files exist, the PNG is square and 256 px, the script writes the same files again (so they are not edited by hand); the rest is checked by the owner by eye.

- [ ] **6.6 The CI pipeline**
  - A GitHub Actions workflow runs on a push to `master` and `release/**` and on pull requests: it sets up Python and `uv`, installs from `uv.lock` (`uv sync --frozen`) and runs the tests.
  - A second job builds the executable with the same PyInstaller command as the install script and checks that `./dist/fermata --version` prints the version of `pyproject.toml`: a build that loses the metadata or the data files fails here.
  - To keep one command in one place, the PyInstaller call moves from the install script into `scripts/build.sh`, which both the script and the workflow run.
  - Linux only, on one runner; no artifact is published. It can be seen working only after the branch is pushed, so the owner's go-ahead for the push is asked for.

- [ ] **6.7 Close-out**
  - `README.md`, `docs/spec.md` §11, §15 and §19, `AGENTS.md` (the commands, the layout) and the roadmap match the code.
  - Final check by the owner: the version in Settings and from `--version`, every language on the screens, the icon in the window and in the menu, the CI run on GitHub.
  - After the owner's approval the branch is merged into `master` with `git merge --no-ff`, then deleted locally and on GitHub.

## Decisions made while breaking down — to confirm

1. The version comes from the package metadata of the installed project, not from a second file or a constant; a test guards that it equals `pyproject.toml`.
2. CI is GitHub Actions, Linux only, tests plus a build with a `--version` smoke check, no published artifacts; other systems only if they become needed (roadmap).
3. The icon is drawn by the agent to the owner's choice (6.5); the launcher entry gets it through the `hicolor` icon folder of the user.
4. Order set by the owner: the version, then the languages, then the name and the icon, then CI.
5. The name, the line under it and the icon were chosen by the owner in a brainstorm; the reasons are in 6.4 and 6.5.
