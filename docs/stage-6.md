# Stage 6 — Packaging and CI: breakdown

Breakdown of [roadmap.md](roadmap.md) Stage 6. Requirements: [spec.md](spec.md) §11 (the version and the icon).
Branch: `feat/stage-6-packaging`. A piece is ticked when the owner has approved it and it is committed.
Accepted like [stage-5.md](stage-5.md): decisions first, tests and code together, one approval per piece.
What is already there from [release-0.2.md](release-0.2.md): the PyInstaller build and `scripts/install-local.sh`. This stage adds the version in the program, the choice of the language, the icon and a CI pipeline.

## Pieces

- [x] **6.1 The version in the program**
  - The version is read from the package metadata (`importlib.metadata`), so `pyproject.toml` stays the only place where the number is written. A test compares what the program reports with `pyproject.toml`.
  - `timer --version` prints `timer 0.5.0` and exits, in a run from source and in the built executable.
  - Settings shows the version right after its title in the header: `Version 0.5.0`, in a smaller font and a less contrasting color than the rest of the screen (a faded text color, readable in all six themes: a test checks the contrast). It is in the header, not in a line of its own, because the screen has no room for another line at the default window size.
  - The build carries the metadata by itself: PyInstaller sees the `version("timer")` call (a build without the `--copy-metadata` flag was tried and reports the version), so no flag is added; verified by running the built executable with `--version`, and guarded by the CI check of 6.5.

- [ ] **6.2 Choosing the language**
  - Added at the owner's request, before the icon. The setting `language` and a list in Settings; the languages are English (the default), Russian, Spanish, Portuguese, German, Chinese and Japanese. Spec §15 said the language setting appears when a second language does: this is that stage.
  - The mechanics: one catalog file per language with the same keys as `en.json`, the text in the chosen language and English where a key is missing; a test fails when a catalog lacks a key or has an extra one. The decisions (the names in the list, when the choice applies) are stated when the piece starts.
  - Russian is the first translation, so the owner can check the mechanics by reading it.

- [ ] **6.3 The other languages**
  - Spanish, Portuguese, German, Chinese and Japanese catalogs. The translations are written by the agent and are not checked by native speakers; this is said in the docs. The window must show Chinese and Japanese text: checked on the owner's laptop.

- [ ] **6.4 The icon**
  - One square PNG chosen by the owner (at least 256 × 256, a transparent background) in `src/timer/icons/timer.png`.
  - It is the window icon (Tk `iconphoto`) and the icon of the launcher entry: the install script copies it to `~/.local/share/icons/hicolor/256x256/apps/timer.png` and the entry says `Icon=timer`. The build carries the file.
  - Tested: the file exists, is square and is large enough; the rest is checked by the owner by eye.

- [ ] **6.5 The CI pipeline**
  - A GitHub Actions workflow runs on a push to `master` and `release/**` and on pull requests: it sets up Python and `uv`, installs from `uv.lock` (`uv sync --frozen`) and runs the tests.
  - A second job builds the executable with the same PyInstaller command as the install script and checks that `./dist/timer --version` prints the version of `pyproject.toml`: a build that loses the metadata or the data files fails here.
  - To keep one command in one place, the PyInstaller call moves from the install script into `scripts/build.sh`, which both the script and the workflow run.
  - Linux only, on one runner; no artifact is published. It can be seen working only after the branch is pushed, so the owner's go-ahead for the push is asked for.

- [ ] **6.6 Close-out**
  - `README.md`, `docs/spec.md` §11, §15 and §19, `AGENTS.md` (the commands, the layout) and the roadmap match the code.
  - Final check by the owner: the version in Settings and from `--version`, every language on the screens, the icon in the window and in the menu, the CI run on GitHub.
  - After the owner's approval the branch is merged into `master` with `git merge --no-ff`, then deleted locally and on GitHub.

## Decisions made while breaking down — to confirm

1. The version comes from the package metadata of the installed project, not from a second file or a constant; a test guards that it equals `pyproject.toml`.
2. CI is GitHub Actions, Linux only, tests plus a build with a `--version` smoke check, no published artifacts; other systems only if they become needed (roadmap).
3. The icon is one PNG from the owner; the launcher entry gets it through the `hicolor` icon folder of the user. Until the owner gives the picture, 6.4 waits and the other pieces go first.
4. Order set by the owner: the version, then the languages, then the icon, then CI.
