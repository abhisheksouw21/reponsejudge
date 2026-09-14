"""
agent_llm_groq.py — LLM Agent using Groq (free tier: 14,400 req/day)
Uses Llama 3.3 70B via Groq's OpenAI-compatible API with JSON mode.
"""

import csv, json, os, sys, time
from openai import OpenAI

INPUT_JSONL = "golden_set.jsonl"
OUTPUT_CSV = "results_llm.csv"
MODEL = "llama-3.3-70b-versatile"  # Groq free tier
RATE_LIMIT_DELAY = 2.5  # stay under 30 RPM free tier
MAX_RETRIES = 3

VALID_INTENTS = [
    "Audio Playback Failure", "Account & Login Access",
    "Billing & Subscription", "App Bug & Performance",
    "Playlist & Library Sync", "Content Availability",
    "Feature Request & Feedback",
]

SYSTEM_PROMPT = """You are an AI customer support agent for Spotify (@SpotifyCares on Twitter).
Given a customer tweet, you must respond with a JSON object containing exactly these fields:

{
  "predicted_intent": "<one of the 7 intents below>",
  "predicted_escalate": true/false,
  "escalation_reason": "<one sentence>",
  "draft_reply": "<helpful casual reply in @SpotifyCares tone>"
}

## INTENT TAXONOMY (pick exactly one)
1. Audio Playback Failure — music won't play/skips/no sound. Auto-resolve.
2. Account & Login Access — can't sign in, locked out, account issues. ESCALATE.
3. Billing & Subscription — charges, plan changes, refunds. ESCALATE.
4. App Bug & Performance — crashes, freezes, UI broken, CPU/battery. Auto-resolve.
5. Playlist & Library Sync — missing playlists, downloads gone, sync issues. Auto-resolve.
6. Content Availability — artist/song not on Spotify catalogue. Auto-resolve.
7. Feature Request & Feedback — feature suggestions, product feedback. Auto-resolve.

## EDGE CASES
- "App crashes when playing" → App Bug & Performance
- "Downloaded songs gone" → Playlist & Library Sync
- "Can't find Taylor Swift" → Content Availability
- "Charged twice" → Billing & Subscription
- "Student discount expired, can't log in" → Account & Login Access
- "Shuffle sucks, fix algorithm" → Feature Request & Feedback

## ALWAYS ESCALATE IF: double-charged, churn threat, account takeover, extreme frustration.

## REPLY TONE: Casual, empathetic, concise. 1-2 emoji max. Sign off with /AI.

Respond ONLY with the JSON object. No markdown, no extra text."""


def classify_message(client, customer_text):
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": customer_text},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=500,
            )
            parsed = json.loads(resp.choices[0].message.content)
            # Validate intent
            intent = parsed.get("predicted_intent", "")
            if intent not in VALID_INTENTS:
                # Try fuzzy match
                for vi in VALID_INTENTS:
                    if vi.lower() in intent.lower() or intent.lower() in vi.lower():
                        intent = vi
                        break
            parsed["predicted_intent"] = intent
            return parsed
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait = 10 * (attempt + 1)
                print(f"      ⏳ Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(2)
    raise Exception("Max retries exceeded")


def main():
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.strip().startswith("GROQ_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    if not api_key:
        print("❌ No GROQ_API_KEY found.")
        print("   Get one free at: https://console.groq.com")
        print("   Then: export GROQ_API_KEY='gsk_...'")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    print("=" * 60)
    print("  LLM AGENT — @SpotifyCares AI (Groq / Llama 3.3 70B)")
    print("=" * 60)

    golden_rows = []
    with open(INPUT_JSONL, "r") as f:
        for line in f:
            golden_rows.append(json.loads(line.strip()))
    print(f"\n  Loaded {len(golden_rows)} rows.")

    # --- Verify first 5 ---
    print(f"\n  [VERIFY] Testing first 5 rows...\n")
    for i, row in enumerate(golden_rows[:5]):
        print(f"  [{i+1}/5] Thread {row['thread_id']}")
        print(f"    Customer: {row['customer_text'][:90]}...")
        try:
            result = classify_message(client, row["customer_text"])
            match = "✓" if result["predicted_intent"] == row["true_intent"] else "✗"
            print(f"    → {match} Intent: {result['predicted_intent']} (true: {row['true_intent']})")
            print(f"    → Escalate: {result['predicted_escalate']}")
            print(f"    → Reply: {result['draft_reply'][:100]}...")
            print(f"    Raw: {json.dumps(result, ensure_ascii=False)}\n")
        except Exception as e:
            print(f"    ❌ ERROR: {e}\n")
        time.sleep(RATE_LIMIT_DELAY)

    print("  ✅ Verification complete. Running all 200...\n")

    # --- Full run ---
    all_results = []
    errors = 0
    start = time.time()

    for i, row in enumerate(golden_rows):
        if (i + 1) % 20 == 0 or i == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(golden_rows) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1:3d}/200]  elapsed={elapsed:.0f}s  "
                  f"rate={rate:.1f}/s  ETA={eta:.0f}s")
        try:
            result = classify_message(client, row["customer_text"])
            all_results.append(result)
        except Exception as e:
            errors += 1
            print(f"  ⚠️  Row {i+1} error: {e}")
            all_results.append({
                "predicted_intent": "App Bug & Performance",
                "predicted_escalate": True,
                "escalation_reason": "LLM error",
                "draft_reply": "Hi! Can you DM us your account email so we can help? /AI",
            })
        time.sleep(RATE_LIMIT_DELAY)

    total = time.time() - start
    print(f"\n  Done! 200 rows in {total:.0f}s ({errors} errors)")

    # --- Save ---
    fields = ["thread_id", "customer_text", "historical_reply",
              "true_intent", "predicted_intent",
              "should_escalate", "predicted_escalate",
              "escalation_reason", "draft_reply"]
    with open(OUTPUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row, result in zip(golden_rows, all_results):
            w.writerow({
                "thread_id": row["thread_id"],
                "customer_text": row["customer_text"],
                "historical_reply": row["historical_reply"],
                "true_intent": row["true_intent"],
                "predicted_intent": result["predicted_intent"],
                "should_escalate": row["should_escalate"],
                "predicted_escalate": result["predicted_escalate"],
                "escalation_reason": result["escalation_reason"],
                "draft_reply": result["draft_reply"],
            })

    print(f"  💾 Saved to {OUTPUT_CSV}")
    print("=" * 60)

if __name__ == "__main__":
    main()
