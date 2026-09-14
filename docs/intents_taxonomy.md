# Spotify Customer Support — Intent Taxonomy

> **Source**: First 100 customer-initiated messages from `spotify_sample.jsonl`
> **Date**: 2026-09-12
> **Purpose**: Mutually exclusive classification schema for first-contact customer intents

---

## Taxonomy Overview

| # | Intent | Frequency (of 100) | Default Escalation |
|---|--------|--------------------|--------------------|
| 1 | Audio Playback Failure | ~28 | Auto-resolve |
| 2 | Account & Login Access | ~14 | Escalate |
| 3 | Billing & Subscription | ~12 | Escalate |
| 4 | App Bug & Performance | ~18 | Auto-resolve |
| 5 | Playlist & Library Sync | ~13 | Auto-resolve |
| 6 | Content Availability | ~9 | Auto-resolve |
| 7 | Feature Request & Feedback | ~6 | Auto-resolve |

---

## 1. Audio Playback Failure

**Definition**: The customer reports that music will not start, stops mid-track, skips unexpectedly, plays wrong/random tracks, or produces no sound — i.e., the core listening experience is broken. This excludes UI freezes (→ App Bug) and missing content (→ Content Availability).

**Real Examples**:
- `[39]` *"@SpotifyCares why is my music skipping like a cd"*
- `[56]` *"Anyone else's @USER suck recently? Stops after nearly every song and won't start playing again 😏"*

**Default Escalation Rule**: **Auto-resolve**. Most playback issues are resolved via standard troubleshooting steps (restart, reinstall, clear cache). Escalate only if the issue persists after two troubleshooting rounds.

---

## 2. Account & Login Access

**Definition**: The customer cannot sign in, has been locked out, reports unauthorized access, needs to recover credentials, or has questions about merging/transferring accounts. This does **not** cover billing changes on a working account (→ Billing & Subscription).

**Real Examples**:
- `[33]` *"@USER I upgraded from premium to family account (this morning) but cannot invite members as the activation screens is white"*
- `[71]` *"@USER @SpotifyCares hey Spotify, how do I access your live chat? Used it last month for help and it was amazing. Need their help again."*

**Default Escalation Rule**: **Escalate to human agent**. Account access issues often require backend verification of identity and may involve security-sensitive operations (password resets, unauthorized access).

---

## 3. Billing & Subscription

**Definition**: The customer has questions or complaints about charges, subscription tier changes (free ↔ premium ↔ family ↔ student), refunds, promotional pricing, payment method issues, or partner bundle redemption (e.g., carrier deals). This does **not** cover feature-level questions about what premium includes (→ Feature Request).

**Real Examples**:
- `[48]` *"@SpotifyCares Hi guys I already have a Premium acc but as a Vodafone customer have premium included in my phone package, how can I redeem this?"*
- `[82]` *"@SpotifyCares since i graduated in may. helpppppp please i NEED spotify in my life"* *(student discount expiration)*

**Default Escalation Rule**: **Escalate to human agent**. Billing disputes, refund requests, and subscription changes involve financial transactions and require authorized agent action. Incorrect automated handling carries high reputational and legal risk.

---

## 4. App Bug & Performance

**Definition**: The customer reports crashes, freezes, excessive CPU/battery usage, UI elements missing or broken (toolbar, lock screen controls, share button), slow loading, or other technical malfunctions that are **not** about audio playback specifically. If music stops because the entire app crashes, classify here. If music stops but the app remains responsive, classify under Audio Playback Failure.

**Real Examples**:
- `[46]` *"@SpotifyCares Why does spotify keep taking 100% of my CPU? I've restarted, reinstalled, tried the private session thingy, nothing..."*
- `[42]` *"@USER @SpotifyCares hey, guys. Share is not working on my 6P, Android Oreo! The app is updated! When I try to share the app closes :("*

**Default Escalation Rule**: **Auto-resolve**. Standard troubleshooting (update app, reinstall, check OS compatibility) resolves most issues. Escalate if the bug is confirmed as a known platform-wide issue or persists after standard steps.

---

## 5. Playlist & Library Sync

**Definition**: The customer reports missing songs, albums, or playlists; downloaded content disappearing; sync discrepancies between devices (e.g., desktop vs. mobile show different libraries); inability to add/remove/reorder songs in playlists; or offline download failures. This does **not** cover content that was never on Spotify (→ Content Availability).

**Real Examples**:
- `[35]` *"@SpotifyCares Just moved lots of music from Groove. Can see all albums/artists/songs in app, but no artists/albums in web player. Why?"*
- `[87]` *"@SpotifyCares The ones I downloaded, this is the second time this week and third time this month, kinda annoying ngl, plz help"*

**Default Escalation Rule**: **Auto-resolve**. Sync issues typically resolve with logout/login, toggling offline mode, or re-downloading. Escalate if data loss is confirmed (permanently deleted playlists) — those require backend recovery.

---

## 6. Content Availability

**Definition**: The customer asks why a specific artist, album, or song is not on Spotify, requests that specific content be added, or reports content that was previously available but has been removed from the catalogue. This is about **catalogue gaps**, not about content the user owns that is not syncing (→ Playlist & Library Sync).

**Real Examples**:
- `[36]` *"Why are there no Bob Seger songs on Spotify? This is a disgrace omgggg. @USER @USER"*
- `[92]` *".@SpotifyCares please return @USER 's album 'Tracy's Manga' to your libraries. your app is insufficient without it"*

**Default Escalation Rule**: **Auto-resolve**. Content availability is determined by licensing agreements and cannot be changed by support agents. Respond with a standard explanation and suggest the "request music" feature. No escalation needed.

---

## 7. Feature Request & Feedback

**Definition**: The customer suggests a new feature, requests a UX change (e.g., alphabetize playlists, parental controls, playlist management improvements), provides general positive/negative feedback about the product direction, or asks about future roadmap items. This is **not** a bug report (→ App Bug) or a request for content (→ Content Availability).

**Real Examples**:
- `[43]` *"Dear @USER is there no way to alphabetize my playlists? Teach me this hack and also how to #dougie."*
- `[75]` *"@USER surely you should have parental controls on your app? A company like yours should be able to introduce this? #disappointed"*

**Default Escalation Rule**: **Auto-resolve**. Acknowledge the feedback, direct the user to the Spotify Community Ideas board where feature requests are tracked and voted on. No escalation unless the request reveals an accessibility/compliance gap.

---

## Classification Decision Tree

```
Customer message arrives
│
├─ Is the core issue about music not playing / skipping / wrong track?
│   └─ YES → 1. Audio Playback Failure
│
├─ Is the issue about inability to sign in, account locked, or account management?
│   └─ YES → 2. Account & Login Access
│
├─ Is the issue about charges, subscription plan, refund, or payment?
│   └─ YES → 3. Billing & Subscription
│
├─ Is the issue about the app crashing, freezing, UI broken, or performance?
│   └─ YES → 4. App Bug & Performance
│
├─ Is the issue about missing/disappeared playlists, downloads, or cross-device sync?
│   └─ YES → 5. Playlist & Library Sync
│
├─ Is the customer asking about content (artist/album/song) not being on Spotify?
│   └─ YES → 6. Content Availability
│
└─ Is the customer suggesting a feature or providing general feedback?
    └─ YES → 7. Feature Request & Feedback
```

---

## Edge Cases & Disambiguation Notes

| Scenario | Correct Intent | Rationale |
|----------|---------------|-----------|
| "App crashes when I try to play a song" | App Bug & Performance | The root cause is a crash, not a playback algorithm issue |
| "My downloaded songs are gone" | Playlist & Library Sync | Content was previously in the user's library |
| "Why can't I find Taylor Swift?" | Content Availability | Catalogue-level absence, not a sync issue |
| "I was charged twice" | Billing & Subscription | Financial, even if account-related |
| "Student discount expired, can't log in" | Account & Login Access | Primary blocker is access, not billing |
| "Shuffle sucks, fix the algorithm" | Feature Request & Feedback | Complaint about feature design, not a bug |
