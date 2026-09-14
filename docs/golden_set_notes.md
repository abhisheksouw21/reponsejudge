# Golden Set — Sampling & Labeling Methodology

> **Dataset**: Kaggle Twitter Customer Support (TWCS) — `twcs.csv`
> **Brand**: @SpotifyCares
> **Golden Set Size**: 200 labeled threads
> **Created**: 2026-09-12
> **Author**: Abhishek Choudhary

---

## 1. Sampling Strategy

**Method**: Random uniform sampling with fixed seed (`seed=42`) for full reproducibility.

**Population**: 2,000 multi-turn @SpotifyCares conversation threads extracted from the TWCS dataset (2,811,774 total tweets). Each thread follows a verified 4-turn structure:

```
Customer → SpotifyCares → Customer → SpotifyCares
```

**Exclusions applied before sampling**:

| Exclusion Rule | Rationale |
|----------------|-----------|
| Single-turn orphan tweets (no brand reply) | No agent response available for comparison; cannot evaluate response quality |
| Threads where @SpotifyCares is not the responding brand | Ensures domain consistency — taxonomy is Spotify-specific |
| Threads shorter than 4 turns | A complete turn pair (User→Brand→User→Brand) is required to observe both the initial problem and whether the first response resolved it or required follow-up |

**Extraction pipeline** (`extract_spotify.py`):
1. Loaded full TWCS dataset via pandas
2. Identified all tweets authored by `SpotifyCares` and the user tweets they replied to
3. Walked reply chains forward to build complete threads
4. Verified the User→Brand→User→Brand turn pattern
5. Cleaned text: stripped URLs, replaced non-brand @handles with `@USER`
6. Output 2,000 qualifying threads → `spotify_sample.jsonl`

**Sampling** (`build_golden_candidates.py`):
- Drew 200 threads from the 2,000-thread pool using `random.sample(threads, 200)` with `random.seed(42)`
- Exported to `golden_set_draft.csv` with blank annotation columns

---

## 2. Labeling Taxonomy

Labels are drawn from [`intents_taxonomy.md`](./intents_taxonomy.md) — a 7-class mutually exclusive intent schema:

| # | Intent Label | Short Definition |
|---|-------------|------------------|
| 1 | Audio Playback Failure | Music won't play, skips, stops, plays wrong track |
| 2 | Account & Login Access | Can't sign in, locked out, account recovery |
| 3 | Billing & Subscription | Charges, plan changes, refunds, promo redemption |
| 4 | App Bug & Performance | Crashes, freezes, high CPU/battery, broken UI |
| 5 | Playlist & Library Sync | Missing downloads, cross-device sync issues |
| 6 | Content Availability | Artist/album/song not in Spotify catalogue |
| 7 | Feature Request & Feedback | Suggestions, UX wishes, general product feedback |

### 2.1 Boundary Rules for Ambiguous Cases

Intent overlap is the primary source of labeling inconsistency. The following rules lock boundaries:

| Ambiguous Scenario | Assign To | Reasoning |
|--------------------|-----------|-----------|
| Playback stops because premium expired | **Billing & Subscription** | Root cause is subscription status, not a playback engine fault |
| App crashes specifically when playing music | **App Bug & Performance** | The failure is a crash (technical), not a playback algorithm issue |
| "My downloaded songs disappeared" | **Playlist & Library Sync** | Content was previously in the user's library — this is a sync/storage issue |
| "Why isn't [Artist] on Spotify?" | **Content Availability** | Catalogue-level absence, not a personal library sync problem |
| "I was charged twice and now I can't log in" | **Billing & Subscription** | When multiple intents co-occur, label by the **financially consequential** one |
| "Student discount expired, can't access premium" | **Account & Login Access** | Primary blocker is loss of access, even though billing triggered it |
| "Shuffle algorithm is terrible, fix it" | **Feature Request & Feedback** | Dissatisfaction with feature design, not a malfunction |
| User provides version info with no clear complaint | **App Bug & Performance** | Contextually, version info is solicited during bug troubleshooting |
| User says "thanks, it's working now" | Label based on **original complaint** | The resolution doesn't change the intent classification |

### 2.2 Single-Label Rule

Each thread receives exactly **one** `true_intent`. If a message contains multiple issues, label by the **primary complaint** — defined as whichever issue the customer would most want resolved first. Financial issues take priority over technical ones.

---

## 3. Escalation Policy

Each row receives a boolean `should_escalate` and a free-text `escalation_reason`.

### 3.1 Auto-Handle (Escalate = `false`)

The AI agent should attempt resolution autonomously when the issue matches **all** of these conditions:

- Standard troubleshooting steps exist (cache clear, reinstall, device restart, logout/login)
- No financial transaction is involved
- No account security concern is present
- The customer tone is neutral or mildly frustrated (not threatening churn)

**Common auto-handle scenarios and their standard reasons**:

| Scenario | `escalation_reason` value |
|----------|--------------------------|
| Playback skip/stop on mobile | `Standard troubleshooting` |
| App slow or freezing | `Standard troubleshooting` |
| Lock screen controls missing | `Standard troubleshooting` |
| Songs not syncing across devices | `Standard troubleshooting` |
| "Where is [Artist]?" | `Standard troubleshooting` |
| Feature suggestion | `Standard troubleshooting` |
| User asking for version/device info | `Standard troubleshooting` |
| Playlist management question | `Standard troubleshooting` |

### 3.2 Escalate to Human Agent (Escalate = `true`)

Escalation is required when **any one** of these triggers is present:

| Trigger Category | Examples | Typical `escalation_reason` |
|-----------------|----------|----------------------------|
| **Financial dispute** | Double-charged, unexpected charge, refund request | `Requires backend billing refund access` |
| **Account security** | Unauthorized access, password changed without consent, email hijacked | `Account security incident — requires identity verification` |
| **Churn threat** | "Canceling right now", "switching to Apple Music", "why do I pay for this garbage" | `User expressing churn threat` |
| **Persistent multi-turn failure** | User has tried all standard steps across 2+ interactions and issue persists | `Multi-turn persistent error — requires internal log review` |
| **Regulatory/legal** | GDPR data request, legal complaint, accessibility requirement | `Regulatory or legal inquiry — requires compliance team` |
| **Partner/bundle issues** | Carrier bundle redemption failures (Vodafone, Starbucks, etc.) | `Partner bundle issue — requires partner integration team` |

### 3.3 Escalation Decision Flowchart

```
Customer message arrives
│
├─ Does it involve money (charge, refund, payment)?
│   └─ YES → ESCALATE ("Requires backend billing refund access")
│
├─ Does it involve account security (hacked, unauthorized)?
│   └─ YES → ESCALATE ("Account security incident")
│
├─ Is the customer explicitly threatening to cancel/leave?
│   └─ YES → ESCALATE ("User expressing churn threat")
│
├─ Has the customer already tried standard troubleshooting (reinstall, restart)?
│   └─ YES, and issue persists → ESCALATE ("Multi-turn persistent error")
│
└─ None of the above?
    └─ AUTO-HANDLE ("Standard troubleshooting")
```

---

## 4. Quality Assurance

- **Inter-rater reliability**: For production use, a second reviewer should independently label a 20% subset (40 rows). Compute Cohen's Kappa; target κ ≥ 0.80 for intent and κ ≥ 0.85 for escalation.
- **Ambiguity log**: Any row where the labeler hesitates for >30 seconds should be flagged in `escalation_reason` with prefix `[AMBIGUOUS]` for later review.
- **Versioning**: The golden set is immutable once finalized. Any corrections produce a new version (`golden_set_v2.jsonl`) with a changelog.

---

## 5. File Manifest

| File | Purpose |
|------|---------|
| `twcs.csv` | Raw Kaggle TWCS dataset (source of truth) |
| `extract_spotify.py` | Extracts and cleans SpotifyCares threads → `spotify_sample.jsonl` |
| `spotify_sample.jsonl` | 2,000 clean 4-turn threads (intermediate dataset) |
| `intents_taxonomy.md` | 7-class intent taxonomy with definitions and examples |
| `build_golden_candidates.py` | Samples 200 threads → `golden_set_draft.csv` |
| `golden_set_draft.csv` | 200 rows with blank annotation columns (labeling worksheet) |
| `label_cli.py` | Interactive CLI for labeling and export to JSONL |
| `golden_set.jsonl` | **Final labeled golden set** (ground truth anchor) |
| `golden_set_notes.md` | **This file** — methodology documentation |
