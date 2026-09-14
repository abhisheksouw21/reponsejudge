"""
agent_llm.py — LLM Agent using Gemini with model rotation + resume support.
Rotates across multiple Gemini model variants to maximize free-tier quota.
"""

import csv, enum, json, os, sys, time, re
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
INPUT_JSONL = "golden_set.jsonl"
OUTPUT_CSV = "results_llm.csv"
PROGRESS_JSONL = "results_llm_progress.jsonl"
RATE_LIMIT_DELAY = 4.0
MAX_RETRIES = 3

# Models to rotate through (each has its own 20/day free quota)
MODELS = [
    "gemini-2.5-flash",
    "gemini-3.6-flash",
]

# ---------------------------------------------------------------------------
class IntentEnum(str, enum.Enum):
    AUDIO_PLAYBACK = "Audio Playback Failure"
    ACCOUNT_LOGIN = "Account & Login Access"
    BILLING = "Billing & Subscription"
    APP_BUG = "App Bug & Performance"
    PLAYLIST_SYNC = "Playlist & Library Sync"
    CONTENT = "Content Availability"
    FEATURE = "Feature Request & Feedback"

class AgentResponse(BaseModel):
    predicted_intent: IntentEnum
    predicted_escalate: bool
    escalation_reason: str
    draft_reply: str

SYSTEM_PROMPT = """You are an AI customer support agent for Spotify (@SpotifyCares on Twitter).

Given a customer tweet, classify it and respond.

## INTENT TAXONOMY (pick exactly one)
1. Audio Playback Failure — music won't play/skips/no sound. Auto-resolve.
2. Account & Login Access — can't sign in, locked out, account issues. ESCALATE.
3. Billing & Subscription — charges, plan changes, refunds. ESCALATE.
4. App Bug & Performance — crashes, freezes, UI broken. Auto-resolve.
5. Playlist & Library Sync — missing playlists, sync issues. Auto-resolve.
6. Content Availability — artist/song not on Spotify. Auto-resolve.
7. Feature Request & Feedback — feature suggestions. Auto-resolve.

## EDGE CASES
- "App crashes when playing" → App Bug (crash is root cause)
- "Downloaded songs gone" → Playlist & Library Sync
- "Can't find Taylor Swift" → Content Availability
- "Charged twice" → Billing & Subscription
- "Student discount expired, can't log in" → Account & Login Access
- "Shuffle sucks" → Feature Request & Feedback

## ALWAYS ESCALATE IF:
- Double-charged / unauthorized charges
- Churn threat ("canceling my subscription")
- Account takeover / hacking
- Extreme frustration or distress

## REPLY TONE: Casual, empathetic, like a helpful friend at Spotify. 1-2 emoji max. Sign off /AI."""

# ---------------------------------------------------------------------------
def classify_message(client, customer_text, models, exhausted_models):
    """Try models in rotation; skip exhausted ones."""
    available = [m for m in models if m not in exhausted_models]
    if not available:
        raise Exception("All model quotas exhausted for today")

    for model in available:
        for attempt in range(MAX_RETRIES):
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=customer_text,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.2,
                        response_mime_type="application/json",
                        response_schema=AgentResponse,
                    ),
                )
                parsed = json.loads(resp.text)
                return {
                    "predicted_intent": parsed["predicted_intent"],
                    "predicted_escalate": parsed["predicted_escalate"],
                    "escalation_reason": parsed["escalation_reason"],
                    "draft_reply": parsed["draft_reply"],
                    "_model": model,
                }
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    print(f"      ⏳ {model} quota hit. Switching model...")
                    exhausted_models.add(model)
                    break  # try next model
                elif "503" in err or "UNAVAILABLE" in err:
                    wait = 5 * (attempt + 1)
                    print(f"      ⏳ {model} unavailable, retry in {wait}s...")
                    time.sleep(wait)
                else:
                    raise e
    raise Exception("All models exhausted or errored")

# ---------------------------------------------------------------------------
def load_progress(path):
    completed = {}
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line.strip())
                    completed[rec["thread_id"]] = rec
    return completed

def save_progress(path, thread_id, result):
    rec = {"thread_id": thread_id, **result}
    with open(path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------------------
def main():
    api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    for prefix in ["GEMINI_API_KEY=", "GOOGLE_API_KEY="]:
                        if line.startswith(prefix):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not api_key:
        print("❌ No GEMINI_API_KEY found."); sys.exit(1)

    client = genai.Client(api_key=api_key)

    print("=" * 60)
    print("  LLM AGENT — @SpotifyCares AI (Gemini Multi-Model)")
    print(f"  Models: {', '.join(MODELS)}")
    print("=" * 60)

    # Load data
    golden_rows = []
    with open(INPUT_JSONL, "r") as f:
        for line in f:
            golden_rows.append(json.loads(line.strip()))
    print(f"\n  Loaded {len(golden_rows)} rows.")

    # Resume
    completed = load_progress(PROGRESS_JSONL)
    if completed:
        print(f"  ✅ Resuming: {len(completed)} already done.")

    remaining = [(i, row) for i, row in enumerate(golden_rows)
                 if row["thread_id"] not in completed]
    print(f"  {len(remaining)} rows to process.\n")

    if not remaining:
        print("  All rows done!")
    else:
        exhausted_models = set()
        errors = 0
        start = time.time()

        for idx, (i, row) in enumerate(remaining):
            if (idx + 1) % 10 == 0 or idx == 0:
                elapsed = time.time() - start
                done = idx + 1
                rate = done / elapsed if elapsed > 0 else 0
                eta = (len(remaining) - done) / rate if rate > 0 else 0
                print(f"  [{done:3d}/{len(remaining)}]  "
                      f"elapsed={elapsed:.0f}s  ETA={eta:.0f}s  "
                      f"models_alive={len(MODELS)-len(exhausted_models)}")

            try:
                result = classify_message(client, row["customer_text"],
                                         MODELS, exhausted_models)
                completed[row["thread_id"]] = result
                save_progress(PROGRESS_JSONL, row["thread_id"], result)
                time.sleep(RATE_LIMIT_DELAY)
            except Exception as e:
                errors += 1
                if "All model" in str(e):
                    print(f"\n  ⛔ {e}")
                    print(f"  Processed {len(completed)}/{len(golden_rows)} total.")
                    print(f"  Re-run tomorrow to continue (progress saved).\n")
                    break
                print(f"  ⚠️  Row {i+1} error: {e}")
                fallback = {
                    "predicted_intent": "App Bug & Performance",
                    "predicted_escalate": True,
                    "escalation_reason": f"LLM error",
                    "draft_reply": "Hi there! Can you DM us your account email so we can help? /AI",
                }
                completed[row["thread_id"]] = fallback
                save_progress(PROGRESS_JSONL, row["thread_id"], fallback)

        total = time.time() - start
        print(f"\n  Run finished. {len(completed)}/{len(golden_rows)} done in {total:.0f}s ({errors} errors)")

    # Save final CSV
    print(f"\n  Saving {OUTPUT_CSV}...")
    fields = ["thread_id","customer_text","historical_reply",
              "true_intent","predicted_intent",
              "should_escalate","predicted_escalate",
              "escalation_reason","draft_reply"]
    with open(OUTPUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in golden_rows:
            r = completed.get(row["thread_id"], {
                "predicted_intent":"","predicted_escalate":"",
                "escalation_reason":"NOT PROCESSED","draft_reply":""})
            w.writerow({
                "thread_id": row["thread_id"],
                "customer_text": row["customer_text"],
                "historical_reply": row["historical_reply"],
                "true_intent": row["true_intent"],
                "predicted_intent": r.get("predicted_intent",""),
                "should_escalate": row["should_escalate"],
                "predicted_escalate": r.get("predicted_escalate",""),
                "escalation_reason": r.get("escalation_reason",""),
                "draft_reply": r.get("draft_reply",""),
            })

    done_count = sum(1 for r in golden_rows if r["thread_id"] in completed)
    print(f"  💾 Saved {done_count}/{len(golden_rows)} rows to {OUTPUT_CSV}")
    if done_count < len(golden_rows):
        print(f"  ℹ️  Re-run this script to continue processing remaining rows.")
    print("=" * 60)

if __name__ == "__main__":
    main()
