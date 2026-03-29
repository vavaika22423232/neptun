# Response to App Store Review (Guideline 2.1)

Copy the text below when replying in App Store Connect.

---

## 1. App Tracking Transparency (ATT)

**Where to find the ATT permission request:**

The App Tracking Transparency permission request now appears **immediately at app launch**, before any other content or ads are shown. It is the first user-facing dialog after the app starts.

**Implementation (as of this update):**
- The ATT request runs in `main()` before `runApp()` is called
- It executes before any ad SDK initialization (MobileAds.initialize)
- No tracking data is collected before the user responds to the ATT prompt
- Flow: App launch → ATT dialog (if status is notDetermined) → User responds → App UI loads → Ad service initializes

**How to test:**
1. Install the app on a fresh device or after resetting advertising identifier (Settings → Privacy & Security → Tracking → Reset)
2. Launch the app
3. The ATT dialog should appear as the first system prompt, before the main map screen

---

## 2. Background Audio

**What features require background audio:**

1. **Air raid alarm notifications** — When an air raid alert is received (via push notification), the app plays an alarm sound and speaks the alert via text-to-speech (TTS) even when the app is in the background or the screen is locked. This ensures users are warned immediately during emergencies.

2. **Voice messages in chat** — Users can send and receive voice messages in the in-app community chat. Background audio allows playback to continue when the user switches to another app or locks the device.

---

## Ukrainian version (for reference)

**1. ATT:** Діалог дозволу на трекінг тепер з’являється одразу після запуску застосунку, до будь-якої реклами чи контенту.

**2. Background audio:** (а) Сповіщення про повітряні тривоги — звук і TTS навіть у фоні; (б) Голосові повідомлення в чаті — відтворення у фоні.
