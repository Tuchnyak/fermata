# Release 0.2 (interim) — sound and a local build: breakdown

An interim release, out of the roadmap order: [roadmap.md](roadmap.md) places sound in Stage 5 and packaging in Stage 6, but the owner wants to use the timer for real on their own laptop now. Only a first cut of each is done here; the rest stays in its stage.
Branch: `feat/stage-2a-sound-and-packaging`; the release itself is the branch `release/v0.2.0` (no git tags).
Accepted like the pieces of [stage-2.md](stage-2.md): decisions first, tests and code together, one approval per piece.

## Scope

- **In:** a sound at the end of a work interval and another at the end of a break; one on/off switch in Settings; a local Linux build that runs as a release (its own data directory, the normal clock) and is easy to start; the version `0.2.0` on a release branch.
- **Out, still in their stages:** choice of sounds, volume, a sound for the end of a scenario (Stage 5); themes, fullscreen (Stage 3); history (Stage 4); CI, builds for other machines or systems, publishing (Stage 6). The build is made for this laptop only: no portability across distributions.

## Pieces

- [x] **R.1 Sound**
  - The sound files are chosen by the owner and put into `src/timer/sounds/` as `work_end.<ext>` and `break_end.<ext>` (`wav`, `ogg`, `flac` or `mp3`). A missing file means no sound, not an error.
  - A sound plays when an interval ends by time: a completed work interval plays the work sound (also the last one of a scenario), a completed break the break sound. Skip and Stop are silent. In `auto` mode the sound of the ending interval plays as the next one starts.
  - A system command plays the file in the background, no new dependency: the first of `paplay`, `pw-play`, `ffplay`, `aplay` that is installed and knows the format (`mp3` only `ffplay`). No player, or a failing one, means no sound; the timer is not affected.
  - The setting `sound` (default on, spec §4.1) has a check box in Settings; it is read when a sound is due, so a change applies at once.

- [ ] **R.2 Local build**
  - `scripts/install-local.sh` builds the application with PyInstaller (already a dev dependency) into one executable, with the translations, the migrations and the sounds inside, and installs it as `~/.local/bin/timer` with a launcher entry in the application menu.
  - The executable is a release for the program: data in `~/.local/share/timer` (apart from the development data), the normal clock, no `--real-time` option. The database is the one every later release uses: migrations are only ever added, and an older program refuses a newer database without touching it.
  - Verified by starting the built executable on an empty data directory and by the owner starting it from the menu.

- [ ] **R.3 Release 0.2.0**
  - The branch `release/v0.2.0` is made from `master` after R.1 and R.2 are merged; its first commit sets the version `0.2.0` in `pyproject.toml` (`chore: release 0.2.0`). The installed build is made from that branch. Later fixes of this release go on the same branch.
  - Nothing is published or pushed.

## Decisions made while breaking down — to confirm

1. The sounds are the owner's; the repository gets no generated placeholders. Until files are put into `src/timer/sounds/` the timer is silent.
2. Only completed intervals sound, so a user action (Skip, Stop) never beeps.
3. The version lives in `pyproject.toml` only and is raised by a commit on the release branch, not on `master`.
4. A sped-up development clock never reaches the built executable (it is a release): testing with it is done from source, as before.
