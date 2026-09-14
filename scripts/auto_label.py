"""
auto_label.py
-------------
Applies rule-based labeling to golden_set_draft.csv using the intent taxonomy
and escalation policy from golden_set_notes.md.

This produces a labeled golden_set_draft.csv and exports golden_set.jsonl.
"""

import csv
import json
import re

CSV_FILE = "golden_set_draft.csv"
OUTPUT_JSONL = "golden_set.jsonl"

# --- Intent keywords (ordered by priority: financial > access > technical) ---
INTENT_RULES = [
    {
        "intent": "Billing & Subscription",
        "keywords": [
            "charge", "charged", "billing", "refund", "subscription", "premium",
            "payment", "price", "renew", "cancel", "plan", "family plan",
            "student", "trial", "free trial", "upgrade", "downgrade", "invoice",
            "bundle", "redeem", "voucher", "code", "gift card", "promo",
            "discount", "vodafone", "starbucks", "hulu", "partner",
            "money", "dollar", "pay", "paid", "$", "€", "£",
        ],
        "escalate": True,
        "reason": "Requires backend billing refund access",
    },
    {
        "intent": "Account & Login Access",
        "keywords": [
            "login", "log in", "sign in", "password", "locked", "locked out",
            "can't access", "cant access", "account", "hacked", "unauthorized",
            "recover", "reset", "verification", "verify", "email change",
            "merge", "transfer account", "deactivated", "suspended",
            "two factor", "2fa", "forgot",
        ],
        "escalate": True,
        "reason": "Account access — requires identity verification",
    },
    {
        "intent": "Audio Playback Failure",
        "keywords": [
            "play", "playing", "skip", "skipping", "stops", "stopped",
            "pauses", "pause", "won't play", "wont play", "not playing",
            "audio", "sound", "silent", "mute", "buffer", "buffering",
            "stream", "streaming", "lag", "quality", "bitrate",
            "wrong song", "wrong track", "random song", "shuffle",
            "repeat", "loop", "crossfade",
        ],
        "escalate": False,
        "reason": "Standard troubleshooting",
    },
    {
        "intent": "App Bug & Performance",
        "keywords": [
            "crash", "crashes", "crashing", "freeze", "freezing", "frozen",
            "bug", "glitch", "error", "cpu", "battery", "drain", "slow",
            "loading", "blank", "black screen", "white screen", "update",
            "version", "reinstall", "install", "uninstall",
            "lock screen", "lockscreen", "toolbar", "widget",
            "notification", "share", "broken",
        ],
        "escalate": False,
        "reason": "Standard troubleshooting",
    },
    {
        "intent": "Playlist & Library Sync",
        "keywords": [
            "playlist", "playlists", "library", "saved", "save",
            "download", "downloaded", "offline", "sync", "syncing",
            "missing song", "missing track", "disappeared", "gone",
            "deleted", "lost", "restore", "local files", "import",
            "groove", "transfer", "migrate",
        ],
        "escalate": False,
        "reason": "Standard troubleshooting",
    },
    {
        "intent": "Content Availability",
        "keywords": [
            "not on spotify", "why isn't", "why isnt", "when will",
            "add this", "add music", "catalogue", "catalog", "available",
            "release", "album", "artist page", "not available",
            "where is", "bring back", "return", "removed",
            "regional", "country", "region",
        ],
        "escalate": False,
        "reason": "Standard troubleshooting",
    },
    {
        "intent": "Feature Request & Feedback",
        "keywords": [
            "feature", "request", "suggest", "suggestion", "wish",
            "would be nice", "please add", "should have", "how about",
            "parental", "controls", "lyrics", "dark mode", "theme",
            "sort", "alphabetize", "organize", "filter",
            "feedback", "opinion", "idea", "improve",
        ],
        "escalate": False,
        "reason": "Standard troubleshooting",
    },
]

# Churn-threat patterns always escalate regardless of intent
CHURN_PATTERNS = re.compile(
    r"cancel|canceling|cancelling|switch to|moving to|unsubscribe|waste of money|"
    r"worst service|done with|leaving spotify|apple music",
    re.IGNORECASE,
)


def classify(text):
    """Classify a customer message into intent + escalation."""
    text_lower = text.lower() if isinstance(text, str) else ""

    for rule in INTENT_RULES:
        for kw in rule["keywords"]:
            if kw in text_lower:
                escalate = rule["escalate"]
                reason = rule["reason"]
                # Override: churn threats always escalate
                if CHURN_PATTERNS.search(text_lower):
                    escalate = True
                    reason = "User expressing churn threat"
                return rule["intent"], escalate, reason

    # Default fallback
    escalate = bool(CHURN_PATTERNS.search(text_lower))
    reason = "User expressing churn threat" if escalate else "Standard troubleshooting"
    return "App Bug & Performance", escalate, reason


# --- Main ---
print("Loading golden_set_draft.csv ...")
rows = []
with open(CSV_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

print(f"Labeling {len(rows)} rows ...")
for row in rows:
    intent, escalate, reason = classify(row["customer_text"])
    row["true_intent"] = intent
    row["should_escalate"] = str(escalate).lower()
    row["escalation_reason"] = reason

# Save back to CSV
fieldnames = [
    "thread_id", "customer_text", "historical_reply",
    "true_intent", "should_escalate", "escalation_reason",
]
with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ golden_set_draft.csv updated with labels.")

# Export JSONL
with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
    for row in rows:
        record = {
            "thread_id": int(row["thread_id"]),
            "customer_text": row["customer_text"],
            "historical_reply": row["historical_reply"],
            "true_intent": row["true_intent"],
            "should_escalate": row["should_escalate"] == "true",
            "escalation_reason": row["escalation_reason"],
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"✅ golden_set.jsonl exported with {len(rows)} labeled rows.")

# Stats
from collections import Counter
intent_counts = Counter(r["true_intent"] for r in rows)
esc_counts = Counter(r["should_escalate"] for r in rows)
print(f"\nIntent distribution:")
for intent, count in intent_counts.most_common():
    print(f"  {intent}: {count}")
print(f"\nEscalation: true={esc_counts.get('true',0)}, false={esc_counts.get('false',0)}")
