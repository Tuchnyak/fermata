# Stage 8 — Windows: breakdown

Breakdown of [roadmap.md](roadmap.md) Stage 8. Requirements: [spec.md](spec.md).
Branch: `feat/stage-8-windows`. A piece is ticked when the owner has approved it and it is committed.
Accepted like [stage-7.md](stage-7.md): decisions first, tests and code together, one approval per piece.
Why: the owner wants to share the program and has a Windows machine to check it on.
The agent has no Windows: what cannot be checked on Linux is checked by the owner on the Windows machine from the commands given in each piece. The machine needs `git` and `uv` (`winget install Git.Git`, `winget install astral-sh.uv`); `uv` fetches Python itself.

## Pieces

- [ ] **8.1 The code does not depend on Linux**
  - The data folder is chosen by platform: on Windows `%LOCALAPPDATA%\fermata` for a release and `%LOCALAPPDATA%\fermata-dev` for a run from source; Linux is unchanged. `FERMATA_DATA_DIR` still overrides both.
  - The test that switches the time zone with `time.tzset` is skipped on Windows, which has no `tzset`. `tzdata` is a dev dependency on Windows only (the tests read named zones; the program reads the local time from the system).
  - The tests of the data folder run on both platforms.
  - On Windows: `uv sync`, `uv run pytest`, all green.

- [ ] **8.2 The first run on Windows, from source**
  - `uv run fermata` on the Windows machine. The owner looks at: the window and its fonts, the signs (`⛶`, the mute button), Chinese and Japanese text, the full screen, the size and place of the window, the icon of the window, the display scale.
  - The sound by ear: the three signals, the three backgrounds and their loops, mute.
  - Only what is broken is changed; if the mute emoji do not draw, another sign is used on Windows.

- [ ] **8.3 The Windows build**
  - `scripts/make_icon.py` also draws `fermata.ico` (16, 24, 32, 48 and 256 px); like the PNG it is committed and a test checks it against the script.
  - `scripts/build-windows.ps1` builds one `fermata.exe` with PyInstaller: `--onefile --windowed`, `--icon`, the same data folders (with `;` in `--add-data`) and the same hidden imports as the Linux build.
  - On Windows: the build, `dist\fermata.exe` started by a double click, the data in `%LOCALAPPDATA%\fermata`, the version in Settings, the sound heard from the `.exe`.

- [ ] **8.4 Close-out**
  - `README.md` (requirements and the build on Windows), `AGENTS.md`, `docs/spec.md` and the roadmap match the code.
  - After the owner's approval the branch is merged into `master` with `git merge --no-ff` and deleted; a release (and publishing the `.exe`) only if the owner asks.

## Decisions made while breaking down (confirmed by the owner)

1. The data folder is `%LOCALAPPDATA%` (local, not roaming: the database must not travel between machines), with the same names as on Linux, `fermata` and `fermata-dev`.
2. The program is one `fermata.exe` (onefile), like on Linux. No installer, no Start menu shortcut, no code signing, so SmartScreen warns. Onefile starts in 1–3 s (it unpacks) and Defender may flag it; if it does, the build becomes a folder in a zip. A shortcut and an installer (Inno Setup) are for the backlog.
3. `--version` prints nothing from a window without a console. It is needed only by the check of the build in CI, so it is decided in Stage 9 (e.g. attach to the console of the parent). The version is shown in Settings.
4. Nothing is changed beforehand: the program is looked at on the real machine first, and only what is broken is changed.
