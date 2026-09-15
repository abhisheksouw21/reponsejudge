"""
llm_judge.py — LLM-as-a-Judge for evaluating Spotify customer support replies.
"""

import csv
import json
import os
import random
import sys
import time
from pydantic import BaseModel, ValidationError
from openai import OpenAI

INPUT_CSV = "results/results_llm.csv"
OUTPUT_CSV = "results/final_pipeline_results.csv"
MODEL = "qwen/qwen3.8-27b"  # Groq free tier
RATE_LIMIT_DELAY = 2.0

class JudgeOutput(BaseModel):
    helpfulness_score: int
    tone_score: int
    judge_reasoning: str

SYSTEM_PROMPT = """You are an expert Customer Support Quality Assurance Judge for Spotify (@SpotifyCares).
Your task is to evaluate a drafted AI response against the customer's original query and the historical ground truth reply from a human agent.

Evaluate the draft response on two criteria on a scale of 1-5:

1. Helpfulness (1-5): Does the reply actually address the user's issue or gracefully request the right information (like a DM) without hallucinating policies?
   - 1: Harmful, hallucinated, or completely ignores the user's problem.
   - 3: Generic acknowledgment but missing key steps, or asks for a DM when not needed.
   - 5: Directly addresses the issue, provides clear next steps, or correctly routes to a DM for sensitive issues.

2. Tone Match (1-5): Does it sound like @SpotifyCares (empathetic, casual, concise)?
   - 1: Robotic, "As an AI language model", or overly formal/corporate.
   - 3: Acceptable but a bit stiff or overly enthusiastic.
   - 5: Perfectly empathetic, casual, concise, and uses 1-2 appropriate emojis max.

You must respond with ONLY a valid JSON object matching this schema:
{
  "helpfulness_score": <int 1-5>,
  "tone_score": <int 1-5>,
  "judge_reasoning": "<string, max 2 sentences explaining the scores>"
}
"""

def evaluate_reply(client, customer_text, historical_reply, draft_reply):
    prompt = f"""
---
CUSTOMER MESSAGE:
{customer_text}

---
HUMAN AGENT REPLY (GROUND TRUTH):
{historical_reply}

---
AI DRAFT REPLY (TO EVALUATE):
{draft_reply}
---
Evaluate the AI DRAFT REPLY. Output only JSON.
"""
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=200,
            )
            raw_json = json.loads(resp.choices[0].message.content)
            
            # Validate with Pydantic
            validated = JudgeOutput(**raw_json)
            
            # Enforce bounds
            validated.helpfulness_score = max(1, min(5, validated.helpfulness_score))
            validated.tone_score = max(1, min(5, validated.tone_score))
            
            return validated
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                wait = 10 * (attempt + 1)
                print(f"      ⏳ Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif attempt == 2:
                print(f"      ❌ Failed to parse JSON: {e}")
                return JudgeOutput(helpfulness_score=3, tone_score=3, judge_reasoning="Evaluation failed due to LLM error.")
            else:
                time.sleep(2)

def main():
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("❌ No GROQ_API_KEY found. Export it first.")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")

    print("=" * 60)
    print("  LLM JUDGE EVALUATION (ALL ROWS)")
    print("=" * 60)

    # Load data
    rows = []
    with open(INPUT_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    print(f"  Loaded {len(rows)} rows from {INPUT_CSV}.")

    evaluated_rows = []
    
    total_helpfulness = 0
    total_tone = 0
    valid_count = 0

    print("\n  Evaluating...")
    start_time = time.time()
    for i, row in enumerate(rows):
        if (i + 1) % 10 == 0 or i == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (len(rows) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1:3d}/200]  elapsed={elapsed:.0f}s  rate={rate:.1f}/s  ETA={eta:.0f}s")
            
        judgement = evaluate_reply(
            client, 
            row["customer_text"], 
            row["historical_reply"], 
            row["draft_reply"]
        )
        
        row["helpfulness_score"] = judgement.helpfulness_score
        row["tone_score"] = judgement.tone_score
        row["judge_reasoning"] = judgement.judge_reasoning
        row["human_helpfulness_score"] = ""
        row["human_tone_score"] = ""
        evaluated_rows.append(row)
        
        total_helpfulness += judgement.helpfulness_score
        total_tone += judgement.tone_score
        valid_count += 1
        
        time.sleep(RATE_LIMIT_DELAY)

    # Save to CSV
    fieldnames = list(rows[0].keys())
    for f in ["helpfulness_score", "tone_score", "judge_reasoning", "human_helpfulness_score", "human_tone_score"]:
        if f not in fieldnames:
            fieldnames.append(f)
            
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(evaluated_rows)

    avg_helpfulness = total_helpfulness / valid_count if valid_count > 0 else 0
    avg_tone = total_tone / valid_count if valid_count > 0 else 0

    print("\n" + "=" * 60)
    print(f"  ✅ Saved {valid_count} evaluated rows to: {OUTPUT_CSV}")
    print("=" * 60)
    print("\n  🏆 FINAL RESULTS (Average Scores):")
    print(f"  Average Helpfulness Score: {avg_helpfulness:.2f} / 5.00")
    print(f"  Average Tone Score:        {avg_tone:.2f} / 5.00")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
