# Stage 7 — Sound inside the program: breakdown

Breakdown of [roadmap.md](roadmap.md) Stage 7. Requirements: [spec.md](spec.md) §14.
Branch: `feat/stage-7-sound-inside`. A piece is ticked when the owner has approved it and it is committed.
Accepted like [stage-6.md](stage-6.md): decisions first, tests and code together, one approval per piece, the sound checked by the owner by ear.
Why: the owner wants to share the program as one file, so it must not rely on players installed on the machine. Today it starts `paplay`, `pw-play`, `ffplay` or `aplay` for the signals and `timeout` + `ffplay` for the background loop; these are Linux's and are not in a built file.

## Pieces

- [x] **7.1 The sounds play inside the program**
  - A new dependency, `miniaudio` (wheels for Linux, Windows and macOS, 0.3–0.6 MB). `audio.py` holds a small interface the rest of the program talks to (play a file once or in a loop, stop it) and its `miniaudio` implementation. The tests use a fake of the interface, so no sound is played by them.
  - A file is decoded when it is needed and kept for as long as it plays: the longest loop decodes in 0.1 s and takes 21 MB, the signals are under 1 MB. Every playing sound has its own device, so a signal over the background sound, or two signals one after another, do not cut each other, as now.
  - `SoundPlayer` (the signals) and `BackgroundSound` (the loop) use the interface. Gone for good: the table of players and their formats, `which` and `launch`, the `timeout` that bounded the loop and its extra seconds. What stays: which sound an event calls for, the fall back of `scenario_end` to `work_end`, the order wav, ogg, flac, mp3, and the rules of when the background sound plays (the owner's decisions of Stage 5).
  - The loop runs without a gap. A sound can no longer outlive the program: closing the window stops them all, and a program that dies takes its sound with it.
  - A missing file, an unreadable file or no sound system on the machine means silence, never an error.
  - Two things found while building it, both now covered: the built program crashed at start for want of `_cffi_backend` (the library's helper), so the installer adds `--hidden-import _cffi_backend`; and a playing device left open kept a program that ended without closing it from ending at all, so the output closes itself at exit (`atexit`) and the program closes it in a `finally` after the window.
  - The frames of a sound, and so the loop without a gap, are a pure function (`sample_stream`) and tested alone; the output is tested against the null device of the library, which plays into nothing.
  - Verified: the tests with the fake and with the null device; a PyInstaller build that starts and carries `miniaudio`; one second of silence through the owner's real sound system (PulseAudio), to see that the device opens without any sound; the real sound by the owner by ear (the agent says before it plays anything).

- [ ] **7.2 Close-out**
  - `docs/spec.md` §14 and §19, `AGENTS.md`, `README.md` (no players are required any more), `src/fermata/sounds/README.md` and the roadmap match the code.
  - Final check by the owner by ear: the signals, the scenario end, the three backgrounds and their loops, the mute button.
  - After the owner's approval the branch is merged into `master` with `git merge --no-ff` and deleted; a release is made if the owner asks.

## Decisions made while breaking down — to confirm

1. The system players are given up altogether (the owner's choice), not kept as a fallback: one way to play sound, and a machine without a sound system is silent.
2. A file is decoded at each start, without a cache: it costs 0.1 s at most and frees the memory when the sound ends.
3. No volume setting and no per-sound gain are added: the equalization of loudness stays postponed (roadmap backlog). The interface could take a gain later.
4. The dependency is `miniaudio>=1.71`.
