"""Quick test: Run LLM agent on first 5 rows only."""
import json, os, sys, time, enum
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

MODEL = "gemini-2.5-flash"

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

SYSTEM_PROMPT = """You are @SpotifyCares AI support agent. Classify the customer tweet into one of these intents:
1. Audio Playback Failure - music won't play/skips/no sound
2. Account & Login Access - can't sign in, locked out, account issues → ESCALATE
3. Billing & Subscription - charges, plan changes, refunds → ESCALATE
4. App Bug & Performance - crashes, freezes, UI broken
5. Playlist & Library Sync - missing playlists, sync issues
6. Content Availability - artist/song not on Spotify
7. Feature Request & Feedback - feature suggestions, product feedback

ESCALATION RULES: Always escalate for Billing and Account issues. Also escalate if user mentions double-charges, threatens to cancel, reports hacking, or shows extreme frustration.

REPLY TONE: Casual, empathetic, helpful. Like a friend at Spotify. Use 1-2 emoji max. Sign off with /AI."""

api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip().startswith("GEMINI_API_KEY="):
                    api_key = line.strip().split("=", 1)[1].strip().strip('"').strip("'")

client = genai.Client(api_key=api_key)

with open("golden_set.jsonl") as f:
    rows = [json.loads(l) for l in f][:5]

print("=" * 60)
print("  TESTING LLM AGENT — First 5 rows")
print("=" * 60)

for i, row in enumerate(rows):
    print(f"\n{'─' * 60}")
    print(f"  [{i+1}/5] Thread {row['thread_id']}")
    print(f"  Customer: {row['customer_text']}")
    print(f"  True Intent: {row['true_intent']}")
    print(f"  Should Escalate: {row['should_escalate']}")
    try:
        resp = client.models.generate_content(
            model=MODEL,
            contents=row["customer_text"],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=AgentResponse,
            ),
        )
        parsed = json.loads(resp.text)
        print(f"\n  ✅ LLM Response:")
        print(f"     Intent:     {parsed['predicted_intent']}")
        match = "✓ MATCH" if parsed['predicted_intent'] == row['true_intent'] else "✗ MISMATCH"
        print(f"     vs Ground:  {match}")
        print(f"     Escalate:   {parsed['predicted_escalate']}")
        print(f"     Reason:     {parsed['escalation_reason']}")
        print(f"     Reply:      {parsed['draft_reply']}")
        print(f"\n     Raw JSON:   {json.dumps(parsed, ensure_ascii=False)}")
    except Exception as e:
        print(f"\n  ❌ ERROR: {e}")
    time.sleep(4)

print(f"\n{'=' * 60}")
print("  TEST COMPLETE")
print("=" * 60)
