# Stage 5 — Sound: breakdown

Breakdown of [roadmap.md](roadmap.md) Stage 5. Requirements: [spec.md](spec.md) §14.
Branch: `feat/stage-5-sound`. A piece is ticked when the owner has approved it and it is committed.
Accepted like [stage-4.md](stage-4.md): decisions first, tests and code together, one approval per piece, the sound checked by the owner by ear.
What is already there from [release-0.2.md](release-0.2.md): the sounds of the end of a work interval and of a break, the global switch, the playback by a system command. This stage adds the sound of the end of a scenario and a background sound for work.

## Pieces

- [x] **5.1 The end of a scenario**
  - A third sound, `scenario_end.<ext>`, plays when a scenario ran to its end by time (the last work interval completed). It plays instead of `work_end`. Skip and Stop stay silent, as now.
  - Without a `scenario_end` file the `work_end` sound plays, so the end of a scenario is never silent. The owner puts the file into `src/timer/sounds/`; the README of the folder says so.
  - Tested without audio: which sound an event calls for, the fallback to `work_end`, and the whole way from the engine to the player.

- [x] **5.2 A background sound**
  - A new setting `background_sound` (`off` by default, `ticking`, `white_noise`, `rain`), a drop-down list in Settings that is stored at once, like the theme.
  - The files `ticking`, `white_noise` and `rain` (`wav` or `ogg` loop best) are the owner's, in `src/timer/sounds/`. A missing file means silence.
  - It plays in a loop while a work interval is running, and only then: a pause, a break, waiting for confirmation, Skip, Stop and the end of an interval stop it; resuming after a pause starts it again. The switch "Sound notifications" silences it too, and a change of the choice applies at once.
  - Played by `ffplay` only (it is the one player that loops: `-loop 0`); without it there is no background sound. The process is ended when it is no longer needed and when the window is closed, so none is left running. It runs under `timeout` (coreutils) for the time left in the interval plus five seconds, so that a sound left behind by a crashed application ends by itself (`ffplay -t` does not end a loop); without `timeout` there is no background sound either.
  - Tested without audio with a fake launcher: when it starts and stops, and what is launched.

- [x] **5.3 The mute button**
  - Added at the owner's request while 5.2 was being checked. A button with a speaker in the header of the home screen, to the left of the fullscreen button; on the fullscreen board, which has no header, it is over the top right corner, the one button there. It switches all the sounds off and on: it is the check box "Sound notifications" of Settings, stored at once, so the two always agree. It shows a speaker when the sound is on and a crossed speaker when it is off.
  - The switch is read when a sound is due, so the signals and the background sound follow it at once.
  - Tested without Tk: the toggle and what it stores, that the other settings stay, the texts, and that a muted timer stays silent through the whole chain.

- [x] **5.4 Close-out**
  - `docs/schema.md` (the setting), `docs/spec.md` §4.1, §14 and §19, `AGENTS.md`, the roadmap and `src/timer/sounds/README.md` match the code.
  - Final check by ear by the owner; the version is raised on `master` before a release is cut, as in `AGENTS.md`.
  - After the owner's approval the branch is merged into `master` with `git merge --no-ff`, then deleted locally and on GitHub.

## Decisions made while breaking down — confirmed by the owner

1. The background plays during a running work interval only.
2. One choice for all: `off`, `ticking`, `white_noise` or `rain`; the files are the owner's; no file, no sound.
3. The background is looped by `ffplay`; without it there is none.
4. `scenario_end` plays instead of `work_end` when a scenario ran to its end, and falls back to `work_end` when its file is missing.
