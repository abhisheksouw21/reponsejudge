"""
label_cli.py
------------
Interactive CLI tool for labeling golden_set_draft.csv.

Workflow:
  1. Loads golden_set_draft.csv
  2. Shows each unlabeled row one at a time
  3. Prompts you to assign: true_intent, should_escalate, escalation_reason
  4. Auto-saves progress back to the CSV after each entry
  5. When done (or you quit), exports all labeled rows to golden_set.jsonl

Usage:
  python3 label_cli.py              # start/resume labeling
  python3 label_cli.py --export     # skip labeling, just export what's done
  python3 label_cli.py --stats      # show labeling progress stats
"""

import csv
import json
import sys
import os

CSV_FILE = "golden_set_draft.csv"
OUTPUT_JSONL = "golden_set.jsonl"

VALID_INTENTS = [
    "Audio Playback Failure",
    "Account & Login Access",
    "Billing & Subscription",
    "App Bug & Performance",
    "Playlist & Library Sync",
    "Content Availability",
    "Feature Request & Feedback",
]

INTENT_SHORTCUTS = {str(i+1): intent for i, intent in enumerate(VALID_INTENTS)}


def load_csv():
    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def save_csv(rows):
    fieldnames = [
        "thread_id", "customer_text", "historical_reply",
        "true_intent", "should_escalate", "escalation_reason",
    ]
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_jsonl(rows):
    labeled = [r for r in rows if r["true_intent"].strip()]
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for row in labeled:
            record = {
                "thread_id": int(row["thread_id"]),
                "customer_text": row["customer_text"],
                "historical_reply": row["historical_reply"],
                "true_intent": row["true_intent"],
                "should_escalate": row["should_escalate"].lower() in ("true", "yes", "1"),
                "escalation_reason": row["escalation_reason"],
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"\n✅ Exported {len(labeled)} labeled rows → {OUTPUT_JSONL}")
    return len(labeled)


def show_stats(rows):
    total = len(rows)
    labeled = sum(1 for r in rows if r["true_intent"].strip())
    remaining = total - labeled
    print(f"\n📊 Labeling Progress")
    print(f"   Total rows:     {total}")
    print(f"   Labeled:        {labeled}")
    print(f"   Remaining:      {remaining}")
    print(f"   Progress:       {labeled/total*100:.1f}%")
    if labeled > 0:
        # Intent distribution
        from collections import Counter
        intent_counts = Counter(r["true_intent"] for r in rows if r["true_intent"].strip())
        print(f"\n   Intent distribution:")
        for intent, count in intent_counts.most_common():
            print(f"     {intent}: {count}")
    print()


def label_interactive(rows):
    print("\n" + "=" * 60)
    print("  🏷️  Golden Set Labeling Tool")
    print("=" * 60)
    print("\nIntent shortcuts (type the number):")
    for num, intent in INTENT_SHORTCUTS.items():
        print(f"  {num} → {intent}")
    print("\nCommands:  s = skip  |  q = save & quit  |  stats = progress\n")
    print("-" * 60)

    unlabeled_indices = [
        i for i, r in enumerate(rows) if not r["true_intent"].strip()
    ]

    if not unlabeled_indices:
        print("🎉 All rows are already labeled!")
        return

    print(f"  {len(unlabeled_indices)} rows remaining to label.\n")

    for count, idx in enumerate(unlabeled_indices, 1):
        row = rows[idx]
        print(f"\n{'─' * 60}")
        print(f"  [{count}/{len(unlabeled_indices)}]  Thread #{row['thread_id']}")
        print(f"{'─' * 60}")
        print(f"\n  📩 CUSTOMER:")
        print(f"  {row['customer_text']}")
        print(f"\n  💬 SPOTIFY REPLY:")
        print(f"  {row['historical_reply']}")
        print()

        # --- Intent ---
        while True:
            intent_input = input("  Intent (1-7 / name / s=skip / q=quit): ").strip()
            if intent_input.lower() == "q":
                save_csv(rows)
                print("\n💾 Progress saved to CSV.")
                return
            if intent_input.lower() == "s":
                break
            if intent_input.lower() == "stats":
                show_stats(rows)
                continue
            if intent_input in INTENT_SHORTCUTS:
                row["true_intent"] = INTENT_SHORTCUTS[intent_input]
                break
            # Check if they typed the full name
            matched = [v for v in VALID_INTENTS if intent_input.lower() in v.lower()]
            if len(matched) == 1:
                row["true_intent"] = matched[0]
                break
            print(f"  ⚠️  Invalid. Use 1-7 or type a partial intent name.")

        if intent_input.lower() == "s":
            continue

        # --- Escalation ---
        esc = input("  Should escalate? (y/n): ").strip().lower()
        row["should_escalate"] = "true" if esc in ("y", "yes", "true", "1") else "false"

        # --- Reason ---
        if row["should_escalate"] == "true":
            reason = input("  Escalation reason: ").strip()
        else:
            reason = input("  Resolution note (or Enter to skip): ").strip()
            if not reason:
                reason = "Standard troubleshooting"
        row["escalation_reason"] = reason

        print(f"  ✓ Labeled: {row['true_intent']} | escalate={row['should_escalate']}")

        # Auto-save every 5 labels
        if count % 5 == 0:
            save_csv(rows)
            print("  💾 Auto-saved.")

    save_csv(rows)
    print("\n💾 All progress saved.")


def main():
    if not os.path.exists(CSV_FILE):
        print(f"❌ {CSV_FILE} not found. Run build_golden_candidates.py first.")
        sys.exit(1)

    rows = load_csv()

    if "--export" in sys.argv:
        export_jsonl(rows)
        return

    if "--stats" in sys.argv:
        show_stats(rows)
        return

    label_interactive(rows)

    # After labeling session, offer to export
    labeled_count = sum(1 for r in rows if r["true_intent"].strip())
    if labeled_count > 0:
        do_export = input(f"\nExport {labeled_count} labeled rows to {OUTPUT_JSONL}? (y/n): ").strip().lower()
        if do_export in ("y", "yes"):
            export_jsonl(rows)


if __name__ == "__main__":
    main()
