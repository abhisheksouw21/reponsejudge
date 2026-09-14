"""
baseline_simple.py
------------------
Simple TF-IDF + Logistic Regression baseline for Intent Classification
and Retrieval-based Reply Generation.

Workflow:
1. Intent Classification:
   - Features: TF-IDF on customer initial messages
   - Model: Logistic Regression
   - Eval: 5-fold cross-validation (Prints Accuracy & Classification Report)

2. Reply Retrieval:
   - For each golden set query, find the most similar historical tweet in
     spotify_sample.jsonl (using TF-IDF cosine similarity).
   - Excludes the query itself from the search index.
   - Drafts the historical reply of the retrieved tweet.

3. Escalation Prediction:
   - Escalate = True if predicted intent is "Billing & Subscription" or "Account & Login Access".

4. Outputs saved to results_simple.csv.
"""

import csv
import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict, StratifiedKFold, KFold
from sklearn.metrics import accuracy_score, classification_report
from sklearn.metrics.pairwise import cosine_similarity
import warnings

# Suppress warnings from undefined metrics in classification_report
warnings.filterwarnings('ignore')

INPUT_JSONL = "golden_set.jsonl"
SAMPLE_JSONL = "spotify_sample.jsonl"
OUTPUT_CSV = "results_simple.csv"

# Intents that require escalation
ESCALATE_INTENTS = {"Billing & Subscription", "Account & Login Access"}

# ---------------------------------------------------------------------------
# 1. Load Data
# ---------------------------------------------------------------------------
print(f"Loading {INPUT_JSONL}...")
golden_rows = []
with open(INPUT_JSONL, "r", encoding="utf-8") as f:
    for line in f:
        golden_rows.append(json.loads(line.strip()))

X_golden_text = [r["customer_text"] for r in golden_rows]
y_true_intent = [r["true_intent"] for r in golden_rows]
golden_thread_ids = [r["thread_id"] for r in golden_rows]

print(f"Loading {SAMPLE_JSONL} for retrieval index...")
sample_texts = []
sample_replies = []
sample_thread_ids = []
with open(SAMPLE_JSONL, "r", encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line.strip())
        turns = rec.get("turns", [])
        if len(turns) >= 2:
            sample_thread_ids.append(rec["thread_id"])
            sample_texts.append(turns[0]["text"])
            sample_replies.append(turns[1]["text"])

# ---------------------------------------------------------------------------
# 2. Intent Classification (5-Fold CV)
# ---------------------------------------------------------------------------
print("\n--- Intent Classification ---")
print("Vectorizing golden set text using TF-IDF...")
vectorizer_clf = TfidfVectorizer(stop_words='english', max_features=5000)
X_golden_features = vectorizer_clf.fit_transform(X_golden_text)

clf = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)

print("Running 5-fold cross-validation...")
try:
    cv_strategy = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    y_pred_intent = cross_val_predict(clf, X_golden_features, y_true_intent, cv=cv_strategy)
except ValueError:
    print("Falling back to standard KFold due to class imbalance...")
    cv_strategy = KFold(n_splits=5, shuffle=True, random_state=42)
    y_pred_intent = cross_val_predict(clf, X_golden_features, y_true_intent, cv=cv_strategy)

acc = accuracy_score(y_true_intent, y_pred_intent)
print(f"\nAccuracy: {acc:.4f} ({acc*100:.1f}%)")
print("\nClassification Report:")
print(classification_report(y_true_intent, y_pred_intent, zero_division=0))


# ---------------------------------------------------------------------------
# 3. Reply Generation (TF-IDF Retrieval)
# ---------------------------------------------------------------------------
print("\n--- Reply Generation (Retrieval) ---")
print("Fitting TF-IDF on full sample for retrieval...")
vectorizer_retrieval = TfidfVectorizer(stop_words='english')
sample_features = vectorizer_retrieval.fit_transform(sample_texts)
query_features = vectorizer_retrieval.transform(X_golden_text)

print("Finding most similar historical tweets (excluding self)...")
retrieved_replies = []
for i, (q_feat, q_tid) in enumerate(zip(query_features, golden_thread_ids)):
    # Compute cosine similarity
    sims = cosine_similarity(q_feat, sample_features)[0]
    
    # Mask out the exact same thread_id
    for j, s_tid in enumerate(sample_thread_ids):
        if s_tid == q_tid:
            sims[j] = -1.0
            
    best_idx = np.argmax(sims)
    retrieved_replies.append(sample_replies[best_idx])


# ---------------------------------------------------------------------------
# 4. Predict Escalation
# ---------------------------------------------------------------------------
print("\n--- Predicting Escalation ---")
y_pred_escalate = [intent in ESCALATE_INTENTS for intent in y_pred_intent]


# ---------------------------------------------------------------------------
# 5. Save Results
# ---------------------------------------------------------------------------
out_rows = []
for i, r in enumerate(golden_rows):
    out_rows.append({
        "thread_id": r["thread_id"],
        "customer_text": r["customer_text"],
        "historical_reply": r["historical_reply"],
        "true_intent": r["true_intent"],
        "predicted_intent": y_pred_intent[i],
        "should_escalate": r["should_escalate"],
        "predicted_escalate": y_pred_escalate[i],
        "retrieved_reply": retrieved_replies[i]
    })

fieldnames = [
    "thread_id", "customer_text", "historical_reply", 
    "true_intent", "predicted_intent", 
    "should_escalate", "predicted_escalate", 
    "retrieved_reply"
]

with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(out_rows)

print(f"\n✅ Results saved to {OUTPUT_CSV} ({len(out_rows)} rows)")
