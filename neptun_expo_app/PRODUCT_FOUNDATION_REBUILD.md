# NEPTUN Product Foundation Rebuild

## Executive Direction

NEPTUN should stop behaving like a collection of pages and become a coherent live-awareness platform.

The product should be organized around one core user question:

> "What is happening around me right now, what does it mean, and what should I do next?"

Everything in the app should support one of five jobs:

1. Understand the live situation.
2. Follow developing signals.
3. Configure what matters to me.
4. Communicate with the community.
5. Unlock deeper intelligence and control.

This is the product architecture, not only a visual redesign.

## Core Product Model

### Primary Surfaces

The app should have four primary surfaces:

1. **Live**
   - Default root.
   - Combines map, immediate status, selected regions, and live event context.
   - The user opens the app here because this is the highest-frequency job.

2. **Radar**
   - A structured intelligence feed.
   - Converts raw events into grouped, scannable updates.
   - It is not a second map; it is the live timeline and analysis layer.

3. **Community**
   - Chat and community channels.
   - Moderation, reports, settings, and user safety are secondary layers.

4. **You**
   - Profile, regions, notification rules, PRO, settings, safety tools, support.
   - Everything personal lives here.

This replaces the mental model of "random tabs" with a clear ecosystem:

- **Live** = what is happening.
- **Radar** = how it is developing.
- **Community** = what people are saying.
- **You** = how the app adapts to me.

## Navigation Architecture

### Bottom Navigation

Recommended bottom tabs:

| Tab | Role | Route | Why |
| --- | --- | --- | --- |
| Live | Primary default | `/` | The core live awareness surface. |
| Radar | Intelligence feed | `/radar` | High-frequency feed for developing events. |
| Community | Messenger | `/chat` | Social layer, clearly named by purpose. |
| You | Account/settings hub | `/profile` | Personal configuration and tools. |

Do not create bottom tabs for:

- Regions
- Premium
- Analytics
- Heatmap
- History
- Settings
- Admin
- Complaints
- Safety
- Shelters

Those are secondary or contextual destinations.

### Secondary Navigation

Secondary screens should be opened from cards, sheets, or command rows:

- Region selection -> `You > Regions & notifications`.
- Smart notifications -> `You > Notifications`.
- History -> `Radar > History` and `You > Tools`.
- Analytics/Heatmap -> `Radar > Insights` and PRO gates.
- Premium -> organic entry from locked features, profile card, and persistent PRO chip.
- Chat settings/admin/complaints -> Community contextual menu and You moderator area.
- Safety/shelters -> You safety section and event contextual suggestions.

### Contextual Navigation

Do not make every feature a visible route. Surface features when they are relevant:

- A selected map marker opens a bottom sheet, not a full page.
- A live event can reveal "Open in Radar", "Share", "Mute this source", "Follow".
- A region alert can reveal "Notification settings for this region".
- A locked advanced insight opens the PRO flow in context.
- A chat report opens a focused sheet, not a detached admin-feeling screen.

## App Opening Logic

### First Launch

Onboarding should not be a marketing carousel. It should configure the product:

1. **Promise**
   - "Know what matters, the moment it matters."
   - One calm visual, one CTA.

2. **Regions**
   - Ask for primary region and optional saved places.
   - This is the most important personalization step.

3. **Notifications**
   - Explain categories.
   - Request permission after value is clear.

4. **Community**
   - Optional nickname setup.
   - Explain that community is separate from official alerts.

5. **Finish**
   - Land on Live with the user's region already highlighted.

### Returning User

The app opens to **Live**.

If there is an active relevant event:

- Show Live map.
- Highlight user's selected region.
- Show one concise situation card above bottom nav.

If calm:

- Show Live map with calm state.
- Show last update and quick actions.

If offline:

- Show cached Live state.
- Slim offline banner.
- Do not block the app with a full error screen unless no cached data exists.

## Information Architecture

### Live Surface

Purpose: immediate situational awareness.

Hierarchy:

1. Map / live canvas.
2. Current status capsule.
3. Selected region/state summary.
4. Floating controls: search, layers, location, filters.
5. Contextual bottom sheet for selected objects.

Live should not show long lists. Long lists belong to Radar.

Live modules:

- Map
- Region status
- Marker selection
- Layer filters
- Search places
- Live connectivity state
- Ballistic/critical overlays
- Embedded quick CTA to Radar when needed

### Radar Surface

Purpose: structured feed and interpretation.

Hierarchy:

1. "Now" summary: active signals, confidence, last update.
2. Quick filters: all, drones, missiles, aviation, regions, saved places.
3. Grouped event feed.
4. New updates pill.
5. History/insights access.

Radar owns:

- Feed
- Threat grouping
- Timeline
- Radar full screen
- History
- Briefing
- Analytics
- Heatmap
- My Radar

Radar should answer:

- What changed?
- How serious is it?
- Where is it moving?
- What should I watch?

### Community Surface

Purpose: social/community communication without polluting official information.

Hierarchy:

1. Room header: Online, current room, rules safety.
2. Optional channel/folder selector.
3. Messages.
4. Composer.
5. Contextual actions via long press/sheets.

Community owns:

- Main chat
- Attachments
- Voice messages
- Search
- Community notice
- Reports/blocking
- Chat settings
- Moderator tools

Future grouping:

- General
- Regional rooms
- Official/announcements read-only
- Moderator queue

### You Surface

Purpose: personal configuration and account.

Hierarchy:

1. Identity card.
2. Status: PRO, notifications, selected regions.
3. Regions & notifications.
4. Appearance & sounds.
5. Safety tools.
6. Insights/tools.
7. Support/about.
8. Moderator/admin area, only when authorized.

You owns:

- Profile
- Region selection
- Smart notifications
- Sleep mode
- Sounds
- Premium/member hub
- Safety center
- Shelters
- Feedback
- Trust
- Admin tools

Premium should not be a tab. It should be:

- A persistent but subtle chip in chrome.
- A contextual unlock flow from locked capabilities.
- A member hub section inside You after subscription.

## Feature Reorganization

| Current feature | New home | Behavior |
| --- | --- | --- |
| Map | Live | Default root. |
| Map marker details | Live sheet | Bottom sheet, not route. |
| Regions | You > Regions & notifications | Also reachable from Live region card. |
| Radar feed | Radar | Primary feed. |
| Radar full | Radar detail | Opens as focused detail route. |
| History | Radar > History | Also under You tools. |
| Analytics | Radar > Insights | PRO-gated contextual unlock. |
| Heatmap | Radar > Insights | PRO-gated contextual unlock. |
| Briefing | Radar / You | Morning summary, modal-style. |
| Chat | Community | Rename route surface concept to Community in UI. |
| Chat settings | Community menu | Not a top-level destination. |
| Chat admin | Community moderator tools | Visible only for moderators. |
| Complaints | Moderator area | Hidden for normal users. |
| Premium | Contextual + You | Not a tab. |
| Sleep mode | You > Notifications | Not standalone primary. |
| Smart notifications | You > Notifications | Integrated with regions. |
| Safety | You > Safety | Clear grouping. |
| Shelters | You > Safety + Live contextual | Available during relevant events. |
| Feedback/trust/about | You > Support | Low priority. |
| Admin | You > Moderator | Hidden. |
| Telegram admin | You > Moderator / MAX | Hidden unless entitled. |

## Interaction System

### Bottom Sheets

Use sheets for:

- Marker detail
- Layer controls
- Filter selection
- Attachment selection
- Report reason
- Region quick settings
- Premium feature preview

Sheet rules:

- One purpose per sheet.
- Always include a clear title.
- Primary action anchored at bottom when needed.
- Avoid full-screen route unless the user is doing a deep task.

### Modals

Use modals only for:

- Confirmation
- Moderator secret
- Destructive actions
- Thank-you / subscription completion

### Floating Actions

Live:

- Search
- Location
- Layers
- Filters
- More

Community:

- Scroll-to-latest
- Attachment sheet

Radar:

- New updates pill
- Filter chips

You:

- No floating controls unless editing profile/settings.

### Search

Search should be contextual first:

- Live search: places, regions, visible objects.
- Radar search: feed text, threat type, place.
- Community search: messages and users.
- You search: settings, eventually.

Global search can come later as a command palette if the product grows.

### Filters

Filters should be contextual and persistent:

- Live: layer and marker filters.
- Radar: feed categories and saved places.
- Community: room/category filters.
- Notifications: region/category toggles.

Do not reuse one generic filter UI everywhere. Reuse tokens and behavior, not exact content.

## User Flow Redesign

### Core Flow

1. Open app.
2. See Live state.
3. Tap a live marker/region.
4. Read concise sheet.
5. Follow deeper in Radar or adjust notifications.

### Community Flow

1. User sees live situation.
2. Moves to Community for discussion.
3. Reads pinned community notice.
4. Sends message/media/voice.
5. Uses safe moderation affordances when needed.

### Premium Flow

1. User encounters a valuable locked insight.
2. App explains the value in context.
3. User opens premium sheet/page.
4. Purchase/restore.
5. Returns to the same feature unlocked.

### Retention Flow

- Morning briefing notification.
- Event-relevant push.
- Calm-state daily summary.
- Changelog only when meaningful.
- Widgets/live activity for ongoing events.

## Screen Relationship Map

```mermaid
flowchart LR
  "Onboarding" --> "Live"
  "Live" --> "Marker Sheet"
  "Live" --> "Layer Sheet"
  "Live" --> "Region Quick Settings"
  "Live" --> "Radar"
  "Radar" --> "History"
  "Radar" --> "Briefing"
  "Radar" --> "Insights"
  "Insights" --> "Analytics"
  "Insights" --> "Heatmap"
  "Community" --> "Chat Settings"
  "Community" --> "Report Sheet"
  "Community" --> "Moderator Tools"
  "You" --> "Regions & Notifications"
  "You" --> "Appearance & Sound"
  "You" --> "Safety"
  "You" --> "Premium"
  "You" --> "Support"
```

## Proposed Expo Router Structure

```text
app/
  _layout.tsx
  onboarding.tsx
  (tabs)/
    _layout.tsx
    index.tsx          # Live
    radar.tsx          # Radar
    chat.tsx           # Community
    profile.tsx        # You
  live/
    marker/[id].tsx    # optional deep link only, normal UI uses sheet
  radar/
    history.tsx
    briefing.tsx
    insights.tsx
    full.tsx
  community/
    settings.tsx
    admin.tsx
    complaints.tsx
  you/
    regions.tsx
    notifications.tsx
    sleep-mode.tsx
    appearance.tsx
    safety.tsx
    shelters.tsx
    feedback.tsx
    trust.tsx
  premium.tsx
```

Current routes can be kept as compatibility aliases while the structure migrates.

## Product Strategy Improvements

### Reduce Clutter

- Remove secondary features from bottom navigation.
- Collapse admin/moderator screens behind authorization.
- Merge notification-related screens into one coherent settings flow.
- Move analytics/heatmap/history under Radar insights.

### Improve Focus

- Each tab gets one job.
- Each sheet gets one decision.
- Each card gets one action.
- Premium is contextual, not constantly shouting.

### Improve Emotional Feel

- Live opens calm and clear, even during active events.
- Community feels safe and moderated.
- Premium feels like power and confidence, not paywall pressure.
- You feels personal and controlled.

### Improve Retention

- Morning briefing.
- Saved places.
- Personalized regions.
- Community identity.
- Widgets/live activity.
- Smart push categories.

## Implementation Roadmap

### Phase 1: Foundation

- Rename UI concepts: `Map` -> `Live`, `Chat` -> `Community`, `Profile` -> `You`.
- Keep routes stable initially, update labels and grouping.
- Build route alias helpers for old paths.
- Create shared bottom sheet primitives and contextual action system.

### Phase 2: Live Surface

- Move region status into a Live summary card.
- Make marker/layer/filter UI contextual sheets.
- Add place search overlay.
- Add event-to-Radar CTA.

### Phase 3: Radar as Intelligence

- Add Now summary.
- Group feed into meaningful sections.
- Move history, analytics, heatmap behind Insights.
- Use PRO gates contextually.

### Phase 4: Community

- Rename shell label to Community.
- Add room/channel architecture.
- Keep main chat as default room.
- Put settings/admin/reports behind contextual menus.

### Phase 5: You

- Reorganize profile into sections:
  - Identity
  - Regions & notifications
  - Appearance & sound
  - Safety
  - Insights/tools
  - Support/about
  - Moderator

### Phase 6: Monetization

- Premium chip remains global.
- Feature gates route back to originating feature.
- Member hub lives in You.
- Pricing flow is contextual and calm.

## Success Criteria

The app succeeds when a new user can answer these immediately:

- Where am I? Live, Radar, Community, or You.
- What matters right now?
- How do I change what I receive?
- Where do I talk to others?
- What does PRO unlock and why would I care?

The final product should feel like a single premium platform, not a bundle of screens.
