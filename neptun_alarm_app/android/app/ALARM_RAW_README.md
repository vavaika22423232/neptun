# PRO: Custom alarm sounds

Ship these **WAV** files (PCM) in `src/main/res/raw/` for PRO custom alarm sounds:

- `alarm_sharp.wav` — «Різкий»
- `alarm_siren.wav` — «Сирена»

Requirements:

- Format: **WAV** (16-bit PCM mono is fine; keep files small)
- Short clips (about 2–5 seconds)
- Lowercase filenames, no spaces; Android resource name is the basename **without** extension (`alarm_sharp`, `alarm_siren`)

iOS copies live in `ios/Runner/` and must be in the app bundle (Copy Bundle Resources in Xcode / `project.pbxproj`).

Without these files, PRO users who pick custom sounds fall back to the default notification sound after a failed `show()`.
