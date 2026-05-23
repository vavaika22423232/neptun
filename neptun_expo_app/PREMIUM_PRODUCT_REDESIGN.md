# NEPTUN Premium Product Redesign

## Product Feeling

NEPTUN should feel like a calm premium live-information product: fast, elegant, emotionally reassuring, and precise. The experience should avoid tactical, military, gaming, cyberpunk, or noisy dashboard aesthetics. The new direction is a refined glassy dark product language inspired by Apple-level restraint, Telegram interaction smoothness, Linear clarity, Arc layering, and fintech-grade hierarchy.

The emotional target is: "This is serious, polished, trustworthy, and worth keeping open."

## Design System

### Color

- Background: deep ink, not pure black. Primary dark token: `#07080D`.
- Surfaces: translucent graphite layers with slight sapphire temperature.
- Primary accent: soft sapphire `#8AB4FF`, used sparingly for focus, active states, links, and live affordances.
- Premium: muted champagne `#E8C978`, never loud gold.
- Success: soft mint `#6EE7B7`.
- Warning: soft amber `#F2C46D`.
- Danger: softened coral `#FF7B7B`, never harsh emergency red unless the content truly requires it.
- Borders: hairline translucent white between 8-16% opacity.
- Glass: `surfaceGlass` and `surfaceGlassStrong` are the default for chrome, sheets, floating controls, and important cards.

### Typography

- Font: Plus Jakarta Sans across the product for consistency.
- Display: 34/40, bold, no negative tracking.
- Screen title: 27/33, bold, no negative tracking.
- Section title: 18/24 semibold.
- Body: 15/22 regular or medium.
- Captions and map metadata: 11-12px, semibold, high contrast only when actionable.
- Chat messages: 16/23 for readability.

### Layout

- 8pt spacing rhythm.
- Screen horizontal padding: 20.
- Cards: 20-26 radius, 16-20 inner padding.
- Bottom sheets: 34 radius, clear drag handle, generous top spacing.
- Floating controls: compact 44-52 touch targets, glass surface, no dense clusters unless required.
- Avoid nested cards. Use glass sections, rows, and floating panels instead.

### Depth and Glass

- Primary chrome uses `expo-blur` with translucent gradient sheen.
- Cards use subtle gradient sheen and hairline borders.
- Shadows are soft and low opacity, never heavy Android-style elevation.
- Glow is reserved for live state, premium state, or selected objects.

### Motion

- Micro interactions: 80-160ms press feedback.
- Element reveal: 180-260ms fade/slide.
- Sheets: 320-420ms spring, damped and non-bouncy.
- Map marker updates: interpolation, not jump cuts.
- Chat insertion: small fade/translate, no flashy bounce.
- Premium hero: slow ambient shimmer, optional, never distracting.

## Component Library

- `AppShellChrome`: glass top chrome with brand, current context, live count, Telegram, PRO, and mode controls.
- `NeptunTabBar`: floating glass bottom nav with animated active pill.
- `AppCard` / `NeptunSurface`: glass cards with subtle sheen.
- `AppButton`: primary sapphire, secondary glass, ghost text.
- `AppBadge`: small semantic pills for live, PRO, offline, limited.
- `AppListItem`: settings/profile rows with consistent icon wells and dividers.
- `AppBottomSheet`: glass modal sheet with drag handle and safe-area padding.
- `AppEmptyState`: calm illustration/icon, concise title, one clear action.
- `AppLoadingState`: skeleton shimmer, not spinners everywhere.
- `MapControlButton`: circular glass controls with icon-only labels and tooltips where supported.
- `MessengerBubble`: readable rounded bubble with reply/media/reaction variants.
- `Composer`: glass input pill, attachment, text, send/mic, reply/edit preview.

## Screen Redesign

### Splash

- Deep ink background.
- Small centered NEPTUN mark.
- One soft sapphire glow behind logo.
- No busy loading text. If boot takes longer, show understated status copy.

### Onboarding

- Three focused screens: live awareness, smart notifications, personal regions.
- Visual language: full-bleed abstract map texture or soft live cards, not generic illustrations.
- Primary CTA anchored at bottom.
- Permission prompts are contextual and explain the value.

### App Shell

- Persistent glass top chrome.
- Four primary tabs: Map, Radar, Chat, Profile.
- Bottom nav floats above safe area with active pill animation.
- Offline banner integrates beneath chrome as a slim glass alert.
- Moderator affordance remains hidden behind deliberate interaction.

### Map

- The map is the core product surface.
- Floating live status capsule: connection, active regions, marker count.
- Search is a glass overlay, not a separate heavy screen.
- Layer controls open a compact bottom sheet.
- Marker detail is a bottom sheet with title, confidence, route, last update, related messages, and actions.
- Clusters use calm count bubbles, not warning-heavy colors.
- Trajectories use thin elegant lines with fading tails.
- Alarm regions use subtle fills and refined borders.
- No military labels, reticles, or noisy HUD language.

### Radar

- Feed should feel like a premium live timeline.
- Header summary: active items, last update, confidence.
- Cards group by threat/source/time.
- Quick filters are small glass chips.
- High-priority rows get semantic accent strips, not giant red panels.
- Empty state explains "No active signals" calmly.

### Chat

- Premium messenger experience.
- Bubbles are softer, more readable, and less tactical.
- Reactions live in compact floating pills.
- Voice messages use elegant waveform bars and clear play state.
- Attachment flow uses bottom sheet: Gallery, Camera, File where supported.
- Long press menu is a Telegram-like glass overlay with preview and actions.
- Search uses an inline glass search header.
- Date dividers are quiet capsules.

### Profile

- Hero identity card with avatar, status, and subscription state.
- Sections: Regions and notifications, Appearance, Sound, Tools, Support, About.
- Rows use consistent icon wells, subtitle hierarchy, and badges.
- PRO is visible but not pushy.

### Premium / PRO

- Hero: one clear promise, premium visual preview, price card.
- Benefits are concrete and scannable.
- Comparison strip highlights practical value.
- Restore is visible but secondary.
- Existing members see a member hub, not a sales page.
- Conversion tone: confident, calm, not aggressive.

### History / Timeline

- Chronological grouped timeline.
- Date headers, compact event rows, semantic dots.
- Filters as chips, search as glass field.
- Empty state tells users when data begins collecting.

### Analytics / Statistics

- Executive summary at top.
- Large primary metric, secondary stat cards, trend sections.
- Use calm chart surfaces and simple labels.
- PRO gates should preview value without feeling broken.

### Notifications / Settings

- Group by user task, not implementation detail.
- Toggle rows with immediate feedback.
- Quiet hours and region selection should feel guided.
- Dangerous actions are isolated and confirmed.

### Modals / Sheets / Dialogs

- Prefer bottom sheets for choices.
- Dialogs only for confirmation, destructive actions, or secrets.
- Sheets use blur, grabber, clear title, one primary action.

## Map Experience

- Live map should be smooth at 60fps.
- Marker rendering stays MapLibre source/layer based.
- React views should only be used for overlays, sheets, and controls.
- Marker movement should interpolate positions and heading.
- Prediction trails fade with time.
- Culling and clustering happen before rendering high-volume layers.
- Controls: location, layers, filters, search, reset bearing.
- Overlay hierarchy: live capsule, search, controls, selected object sheet.

## Chat Experience

- Chat must feel like a polished messenger, not a web comments widget.
- Composer is always reachable and one-hand friendly.
- Swipe reply, long press menu, reactions, edit/delete/report/block remain.
- Media previews open into full-screen gallery.
- Voice playback is inline with waveform and duration.
- Search should highlight matching text.
- Moderator tools stay present only when authorized.

## Premium Experience

- Premium should feel like unlocking power, not removing annoyance.
- Use champagne accents sparingly.
- Pricing cards must be highly legible.
- Feature comparison should use real product benefits:
  - advanced radar views
  - richer history
  - analytics
  - quiet hours and customization
  - priority visual modes
  - no ads where applicable
- Thank-you modal should reinforce status and point to customization.

## Implementation Rules

- Prefer themed tokens from `src/theme/*`.
- Avoid hard-coded colors except one-off transparent overlays.
- Use `AppCard`, `NeptunSurface`, `AppListItem`, `AppButton`, and `NeptunPressable`.
- Use Reanimated for press, reveal, and nav interactions.
- Keep map markers in MapLibre layers, not React views.
- Avoid large blur trees in lists. Blur only chrome, nav, sheets, and a small number of floating surfaces.
- Keep text readable first; visual flourish is secondary.

## Migration Priority

1. Foundation: tokens, chrome, nav, card/button/list primitives.
2. Map: live overlays, controls, sheets, marker visuals.
3. Chat: bubbles, composer, menus, media, search.
4. Radar: premium feed and filter system.
5. Profile/settings: complete settings architecture and visual consistency.
6. Premium: conversion-quality paywall and member hub.
7. States: loading, empty, offline, errors, permission prompts.
8. Motion polish and accessibility pass.
