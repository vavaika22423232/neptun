# PRO: Custom alarm sounds

Add these **WAV** files under `app/src/main/res/raw/`:

- `alarm_sharp.wav` — «Різкий»
- `alarm_siren.wav` — «Сирена»

Requirements:

- Format: **WAV** (16-bit PCM mono recommended), short (about 2–5 seconds)
- Lowercase filenames, no spaces

iOS copies belong in `ios/Runner/` and must be included in the Runner target (bundle resources).

Without these files, PRO users who select custom sounds get a fallback after `show()` fails.
