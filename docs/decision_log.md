# Decision Log & Baseline Insights

## 1. Baseline Performance Observations
- **Trivial Baseline Accuracy**: 46.5%. While not 55%, the dataset is still heavily skewed toward `App Bug & Performance`. This skew is important to document under "What is misleading about my headline number?" because a naive model will superficially look okay just by guessing the majority class, masking poor performance on critical minority classes like `Account & Login Access`.
- **Simple Baseline (TF-IDF + Logistic Regression)**: Achieved 69.0% accuracy (up from 46.5%).
  - It performed very well on `Billing & Subscription` (F1 = 0.81).
  - It struggled heavily on minority and nuanced classes like `Playlist & Library Sync` (F1 = 0.12) and `Feature Request & Feedback` (F1 = 0.00).

## 2. Intent Routing & Architecture Decisions
- **Why not just use TF-IDF?**
  - *Observation*: The TF-IDF model runs extremely fast and provides decent accuracy for distinct classes (like Billing).
  - *Decision Statement*: "Considered deploying TF-IDF + Logistic Regression for intent routing to save compute costs, but opted for the LLM to handle nuanced user frustration and multi-turn context that bag-of-words misses. The simple baseline failed completely on minority intents like 'Feature Requests' because it lacks semantic understanding."
