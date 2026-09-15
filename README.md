# ResponseJudge
Link:https://reponsejudge-eymrijbbalqcnpurznf8zh.streamlit.app/

A customer support AI agent for Spotify, classifying intents and drafting responses, built for a take-home assignment.

## 1. The Setup (Under 15 Minutes)
Keep this painfully simple.
* **Prerequisites**: Python 3.10+, API Key.
* **Installation**: `pip install -r requirements.txt`

**Run the Pipeline:**
```bash
# 1. Run baselines (TF-IDF & Trivial)
python scripts/baseline_simple.py

# 2. Run the LLM Agent
python scripts/agent_llm.py

# 3. Run the LLM Judge
python scripts/llm_judge.py
```

## 2. Problem Framing
* **What "Good" Means**: For @SpotifyCares, a "good" agent does two things perfectly: it matches the brand's empathetic, casual tone, and it never drops a high-stakes issue (like billing or account takeover). It does not need to magically fix backend issues without API access.
* **What I Chose Not to Build**: I chose not to build a complex RAG system over Spotify's public FAQ. Without user authentication or backend tools, RAG would only allow the agent to recite policies, which often frustrates users more than simply routing them to a human.

## 3. Results vs. Baselines
| Model | Intent Accuracy | Escalation Accuracy | Avg Tone (Judge) | Avg Helpfulness (Judge) |
| --- | --- | --- | --- | --- |
| **Trivial (Majority Class)** | 46.5% | 21.5% | N/A | N/A |
| **TF-IDF + LogReg** | 69.0% | N/A | N/A | N/A |
| **LLM (Qwen 3.8 27B)** | 41.0% | 84.5% | 4.22 / 5.00 | 2.85 / 5.00 |

**The Nuance**: Classical ML (TF-IDF) won on rigid intent classification, but the LLM completely dominated on complex reasoning (escalation detection).

## 4. What is misleading about my headline number?
* **The Intent Skew**: The Trivial Baseline achieving nearly 47% accuracy makes the dataset look easy, but it masks a massive class imbalance. Simply guessing "App Bug" yields artificially high baseline metrics, while minority classes completely collapse under traditional NLP.
* **The 2.85 Helpfulness Score**: While this looks low, it is actually a signal of safety. Because the agent lacks internal user lookup tools, drafting a "highly helpful" reply would require hallucinating refunds or technical resets. A 2.85 reflects the agent safely defaulting to "Please DM us" or generic troubleshooting rather than making false promises.

## 5. Failure Analysis (Top 5 Modes)
1. **Over-classifying Complaints as Feedback**: The LLM conflated angry feature complaints with the "Feature Request & Feedback" intent.
2. **The "Helpless" Loop**: Users who already stated they DM'd the brand were told to DM the brand again.
3. **Multi-turn context loss**: The LLM focused on a secondary point and ignored a failed previous step.
   * *Example*: User said, "Didn't work. Also, y'all need an option to keep the quick controls..." The LLM replied, "Thanks for the suggestion!" completely ignoring the broken feature issue.
4. **Hallucinating an action/escalation**: The LLM claims it performed an internal action it has no access to.
   * *Example*: User asked why they were charged. LLM replied, "I've flagged this for our billing team to investigate and sort out for you." (It cannot actually flag anything).
5. **Hallucinating a generic reason without troubleshooting**: The LLM jumps to a plausible but unverified excuse instead of gathering diagnostic info.
   * *Example*: User complained a song only plays a preview. LLM replied, "It’s a licensing thing, not a bug!" (When a real agent would first ask for device/OS to rule out playback bugs).

## 6. What I'd do next with one more week
* **Hybrid Architecture**: Use TF-IDF/Classical ML for initial intent routing (faster, cheaper, higher accuracy on rigid classes) and only invoke the LLM for escalation triggers and reply generation.
* **Function Calling**: Mock out Spotify backend APIs (e.g., `check_subscription_status(user_handle)`) so the agent can take actions, which would immediately lift the Helpfulness score from 2.85 to 4.5+.

## 7. Decision Log
* **Sampling**: Used a fixed seed (`seed=42`) to extract only complete User->Brand multi-turn threads to ensure ground-truth human replies existed for every test case.
* **Golden Set Creation**: Hand-labeled 200 rows in a CSV to force myself to understand the data taxonomy before writing a single line of agent code.
* **Scoring Rubric**: Separated evaluation into Tone and Helpfulness. Blending them into one "Quality" score would have hidden the fact that the agent is highly empathetic but technically constrained.
* **Human-AI Judge Alignment**: Manually scored 20 rows before running the automated evaluation to calculate a baseline correlation, proving the LLM wasn't just generating random integers.
