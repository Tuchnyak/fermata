# Sounds

Put the sound files of the application here:

- `work_end.<ext>` — the end of a work interval;
- `break_end.<ext>` — the end of a break;
- `scenario_end.<ext>` — a scenario run to its end (plays instead of `work_end`; without this file `work_end` plays).

The background sound of a work interval, chosen in Settings, is a file that is played in a loop without a gap:

- `ticking.<ext>` — a ticking clock;
- `white_noise.<ext>` — white noise;
- `rain.<ext>` — rain.

`<ext>` is `wav`, `ogg`, `flac` or `mp3`; when several exist the first of that order is played. The program plays them itself, no player is needed. Without a file there is no sound.
Names are lower case, with an underscore.

## Sources
1. [work_end.mp3](https://pixabay.com/sound-effects/film-special-effects-clear-bell-notification-sound-351709/)
2. [break_end.mp3](https://pixabay.com/sound-effects/film-special-effects-church-bell-toll-156464/)
3. [scenario_end.mp3](https://pixabay.com/sound-effects/musical-marimba-win-b-1-209678/)
4. [ticking.ogg](https://pixabay.com/sound-effects/film-special-effects-ticking-clock-1-wav-edition-264449/)
5. [white_noise.ogg](https://pixabay.com/sound-effects/film-special-effects-soft-soothing-deep-white-noise-378857/)
6. [rain.ogg](https://pixabay.com/sound-effects/nature-rain-sound-307165/)

The background sounds are two-minute pieces re-encoded to `ogg` from longer originals (`ticking` is whole, only re-encoded). The ends of `white_noise` and `rain` are cross-faded into their beginnings, so that they loop without a gap or a click.

The files are not covered by the GPL of the project: they come from Pixabay and are used under the [Pixabay Content License](https://pixabay.com/service/license-summary/).
