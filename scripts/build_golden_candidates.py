"""
build_golden_candidates.py
--------------------------
Samples 200 unique conversation threads from spotify_sample.jsonl,
extracts key fields, and creates golden_set_draft.csv with blank
annotation columns for human labeling.

Seed: 42 (reproducible)
"""

import json
import random
import csv

INPUT_JSONL = "spotify_sample.jsonl"
OUTPUT_CSV = "golden_set_draft.csv"
SAMPLE_SIZE = 200
SEED = 42

# ---------------------------------------------------------------------------
# 1. Load all threads
# ---------------------------------------------------------------------------
print(f"[1/3] Loading threads from {INPUT_JSONL} ...")
threads = []
with open(INPUT_JSONL, "r", encoding="utf-8") as f:
    for line in f:
        threads.append(json.loads(line.strip()))

print(f"       Total threads available: {len(threads):,}")

# ---------------------------------------------------------------------------
# 2. Sample 200 unique threads
# ---------------------------------------------------------------------------
print(f"[2/3] Sampling {SAMPLE_SIZE} threads (seed={SEED}) ...")
random.seed(SEED)
sampled = random.sample(threads, min(SAMPLE_SIZE, len(threads)))
print(f"       Sampled: {len(sampled)}")

# ---------------------------------------------------------------------------
# 3. Build rows and write CSV
# ---------------------------------------------------------------------------
print(f"[3/3] Writing {OUTPUT_CSV} ...")

fieldnames = [
    "thread_id",
    "customer_text",
    "historical_reply",
    "true_intent",
    "should_escalate",
    
    "escalation_reason",
]

rows = []
for thread in sampled:
    turns = thread["turns"]

    # Turn 0 = customer initial message
    customer_text = turns[0]["text"] if len(turns) > 0 else ""

    # Turn 1 = brand's first response
    historical_reply = turns[1]["text"] if len(turns) > 1 else ""

    rows.append({
        "thread_id": thread["thread_id"],
        "customer_text": customer_text,
        "historical_reply": historical_reply,
        "true_intent": "",
        "should_escalate": "",
        "escalation_reason": "",
    })

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\n✅ Done! {OUTPUT_CSV} created with {len(rows)} rows.")
print(f"   Columns: {', '.join(fieldnames)}")
print()
print("   Next step: fill in true_intent, should_escalate, and escalation_reason")
print("   Then run label_cli.py to finalize → golden_set.jsonl")
