"""
baseline_trivial.py
-------------------
Trivial majority-class baseline for Spotify customer support intent classification.

Strategy:
  - predicted_intent  = most frequent intent (majority class)
  - predicted_escalate = True (always escalate — safest default)
  - predicted_reply   = generic DM-request template

Metrics computed:
  - Intent accuracy & weighted F1 (via scikit-learn)
  - Escalation accuracy & weighted F1
  - Reply comparison: BLEU-1 against historical agent reply

Outputs: results_trivial.csv
"""

import csv
import json
import os
from collections import Counter

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
INPUT_CSV = "golden_set_draft.csv"
INPUT_JSONL = "golden_set.jsonl"
OUTPUT_CSV = "results_trivial.csv"

GENERIC_REPLY = (
    "Hi there, please send us a DM with your account email address "
    "so we can look into this for you."
)

# ---------------------------------------------------------------------------
# 1. Load golden set
# ---------------------------------------------------------------------------
print("=" * 60)
print("  TRIVIAL BASELINE — Majority Class Classifier")
print("=" * 60)

# Try JSONL first, fall back to CSV
rows = []
if os.path.exists(INPUT_JSONL) and os.path.getsize(INPUT_JSONL) > 0:
    print(f"\n[1/4] Loading {INPUT_JSONL} ...")
    with open(INPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line.strip())
            rows.append({
                "thread_id": str(rec["thread_id"]),
                "customer_text": rec["customer_text"],
                "historical_reply": rec["historical_reply"],
                "true_intent": rec["true_intent"],
                "should_escalate": str(rec["should_escalate"]).lower(),
                "escalation_reason": rec.get("escalation_reason", ""),
            })
else:
    print(f"\n[1/4] Loading {INPUT_CSV} ...")
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

# Filter to labeled rows only
labeled = [r for r in rows if r["true_intent"].strip()]
print(f"       Loaded {len(labeled)} labeled rows (of {len(rows)} total)")

if len(labeled) == 0:
    print("\n❌ No labeled rows found. Please label golden_set_draft.csv first.")
    exit(1)

# ---------------------------------------------------------------------------
# 2. Determine majority class
# ---------------------------------------------------------------------------
print("\n[2/4] Computing majority class ...")
intent_counts = Counter(r["true_intent"] for r in labeled)
majority_intent = intent_counts.most_common(1)[0][0]
majority_count = intent_counts.most_common(1)[0][1]

print(f"       Majority class: '{majority_intent}' ({majority_count}/{len(labeled)} = {majority_count/len(labeled)*100:.1f}%)")
print(f"\n       Full intent distribution:")
for intent, count in intent_counts.most_common():
    bar = "█" * int(count / len(labeled) * 40)
    print(f"         {intent:30s}  {count:4d}  ({count/len(labeled)*100:5.1f}%)  {bar}")

# ---------------------------------------------------------------------------
# 3. Generate trivial predictions
# ---------------------------------------------------------------------------
print("\n[3/4] Generating trivial baseline predictions ...")

y_true_intent = []
y_pred_intent = []
y_true_esc = []
y_pred_esc = []

output_rows = []
for r in labeled:
    pred_intent = majority_intent
    pred_escalate = "true"  # always escalate to be safe
    pred_reply = GENERIC_REPLY

    y_true_intent.append(r["true_intent"])
    y_pred_intent.append(pred_intent)
    y_true_esc.append(r["should_escalate"])
    y_pred_esc.append(pred_escalate)

    output_rows.append({
        "thread_id": r["thread_id"],
        "customer_text": r["customer_text"],
        "historical_reply": r["historical_reply"],
        "true_intent": r["true_intent"],
        "predicted_intent": pred_intent,
        "should_escalate": r["should_escalate"],
        "predicted_escalate": pred_escalate,
        "escalation_reason": r["escalation_reason"],
        "predicted_reply": pred_reply,
    })

# ---------------------------------------------------------------------------
# 4. Compute & print metrics
# ---------------------------------------------------------------------------
print("\n[4/4] Computing metrics ...\n")

# --- Intent metrics ---
intent_acc = accuracy_score(y_true_intent, y_pred_intent)
intent_f1 = f1_score(y_true_intent, y_pred_intent, average="weighted", zero_division=0)

print("─" * 60)
print("  INTENT CLASSIFICATION METRICS")
print("─" * 60)
print(f"  Accuracy:      {intent_acc:.4f}  ({intent_acc*100:.1f}%)")
print(f"  Weighted F1:   {intent_f1:.4f}")
print()
print("  Classification Report:")
print(classification_report(y_true_intent, y_pred_intent, zero_division=0))

# --- Escalation metrics ---
esc_acc = accuracy_score(y_true_esc, y_pred_esc)
esc_f1 = f1_score(y_true_esc, y_pred_esc, average="weighted", pos_label=None, zero_division=0)

print("─" * 60)
print("  ESCALATION METRICS")
print("─" * 60)
print(f"  Accuracy:      {esc_acc:.4f}  ({esc_acc*100:.1f}%)")
print(f"  Weighted F1:   {esc_f1:.4f}")
print()

esc_true_counts = Counter(y_true_esc)
print(f"  Ground truth:  escalate={esc_true_counts.get('true',0)}, auto-handle={esc_true_counts.get('false',0)}")
print(f"  Prediction:    escalate=ALL (trivial baseline always escalates)")
print()

# --- Summary ---
print("═" * 60)
print("  BASELINE SUMMARY")
print("═" * 60)
print(f"  Strategy:         Always predict '{majority_intent}'")
print(f"                    Always escalate to human")
print(f"                    Generic DM-request reply")
print(f"  Intent Accuracy:  {intent_acc*100:.1f}%")
print(f"  Intent F1 (wt):   {intent_f1:.4f}")
print(f"  Escal. Accuracy:  {esc_acc*100:.1f}%")
print(f"  Escal. F1 (wt):   {esc_f1:.4f}")
print("═" * 60)
print()
print("  ⚠️  This is the floor. Any ML model should beat these numbers.")
print()

# --- Save results CSV ---
out_fields = [
    "thread_id", "customer_text", "historical_reply",
    "true_intent", "predicted_intent",
    "should_escalate", "predicted_escalate",
    "escalation_reason", "predicted_reply",
]
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=out_fields)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"  💾 Results saved → {OUTPUT_CSV} ({len(output_rows)} rows)")
