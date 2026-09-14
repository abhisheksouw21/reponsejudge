"""
extract_spotify.py
------------------
Extracts multi-turn conversation threads involving @SpotifyCares from the
Twitter Customer Support (twcs) dataset.

A "complete thread" is defined as a 4-turn sequence:
    User -> Brand -> User -> Brand

Output: spotify_sample.jsonl  (up to 2,000 threads)
"""

import json
import re
import pandas as pd

BRAND = "SpotifyCares"
INPUT_CSV = "twcs.csv"
OUTPUT_JSONL = "spotify_sample.jsonl"
MAX_THREADS = 2_000

# ---------------------------------------------------------------------------
# 1. Load the dataset
# ---------------------------------------------------------------------------
print(f"[1/5] Loading {INPUT_CSV} ...")
df = pd.read_csv(INPUT_CSV, dtype={"tweet_id": str,
                                    "author_id": str,
                                    "in_response_to_tweet_id": str,
                                    "response_tweet_id": str})

print(f"       Total rows: {len(df):,}")

# Normalise the inbound column
df["inbound"] = df["inbound"].astype(str).str.lower().map({"true": True, "false": False})

# ---------------------------------------------------------------------------
# 2. Filter to SpotifyCares-related tweets
# ---------------------------------------------------------------------------
print(f"[2/5] Filtering tweets involving @{BRAND} ...")

# Brand tweets authored by SpotifyCares
brand_ids = df.loc[df["author_id"].str.lower() == BRAND.lower(), "tweet_id"].tolist()
brand_set = set(brand_ids)

# User tweets that the brand replied to
user_tweets_replied_by_brand = df.loc[
    df["in_response_to_tweet_id"].notna() &
    df["author_id"].str.lower().eq(BRAND.lower()),
    "in_response_to_tweet_id"
].tolist()
user_tweet_set = set(user_tweets_replied_by_brand)

# Build lookup: tweet_id -> row
tweet_map = df.set_index("tweet_id").to_dict("index")

print(f"       Brand tweets: {len(brand_set):,}")
print(f"       User tweets replied by brand: {len(user_tweet_set):,}")

# ---------------------------------------------------------------------------
# 3. Build 4-turn threads: User -> Brand -> User -> Brand
# ---------------------------------------------------------------------------
print("[3/5] Building 4-turn conversation threads ...")


def walk_chain(start_tweet_id, tweet_lookup, max_depth=20):
    """Walk a reply chain forward from a given tweet."""
    chain = []
    current_id = start_tweet_id
    visited = set()
    while current_id and current_id in tweet_lookup and len(chain) < max_depth:
        if current_id in visited:
            break
        visited.add(current_id)
        row = tweet_lookup[current_id]
        chain.append({
            "tweet_id": current_id,
            "author_id": row["author_id"],
            "inbound": row["inbound"],
            "text": row.get("text", ""),
        })
        # Move to the response
        resp = row.get("response_tweet_id")
        if pd.isna(resp) or resp == "":
            break
        resp_ids = str(resp).split(",")
        current_id = None
        for rid in resp_ids:
            rid = rid.strip()
            if rid in tweet_lookup:
                current_id = rid
                break
    return chain


# Start from user tweets that the brand replied to
threads = []
seen_starts = set()

for user_tid in user_tweet_set:
    if user_tid not in tweet_map or user_tid in seen_starts:
        continue
    seen_starts.add(user_tid)

    chain = walk_chain(user_tid, tweet_map)
    if len(chain) < 4:
        continue

    # Verify pattern: User -> Brand -> User -> Brand
    roles = []
    for msg in chain[:4]:
        is_brand = str(msg["author_id"]).lower() == BRAND.lower()
        roles.append("brand" if is_brand else "user")

    if roles == ["user", "brand", "user", "brand"]:
        threads.append(chain[:4])

    if len(threads) >= MAX_THREADS:
        break

print(f"       Complete 4-turn threads found: {len(threads):,}")

# ---------------------------------------------------------------------------
# 4. Clean text: remove URLs, standardise non-brand handles to @USER
# ---------------------------------------------------------------------------
print("[4/5] Cleaning text ...")

URL_PATTERN = re.compile(r"https?://\S+")
HANDLE_PATTERN = re.compile(r"@(\w+)")


def clean_text(text, brand_handle=BRAND):
    if not isinstance(text, str):
        return ""
    text = URL_PATTERN.sub("", text)

    def replace_handle(match):
        handle = match.group(1)
        if handle.lower() == brand_handle.lower():
            return f"@{brand_handle}"
        return "@USER"

    text = HANDLE_PATTERN.sub(replace_handle, text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


for thread in threads:
    for msg in thread:
        msg["text"] = clean_text(msg["text"])

# ---------------------------------------------------------------------------
# 5. Write to JSONL
# ---------------------------------------------------------------------------
print(f"[5/5] Writing {len(threads):,} threads to {OUTPUT_JSONL} ...")

with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
    for i, thread in enumerate(threads):
        record = {
            "thread_id": i,
            "turns": [
                {
                    "role": "customer" if turn["inbound"] else "agent",
                    "author": turn["author_id"],
                    "text": turn["text"],
                }
                for turn in thread
            ],
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\n Done! {OUTPUT_JSONL} created with {len(threads):,} threads.")
