# Prospective Model Arena

Only one immutable pre-result forecast per target issue is scored.
Historical masked holdout runs are excluded from every statistic below.
Skipped/unavailable OpenCode calls are NOT counted as wrong predictions.

| Model | Hits | Valid votes | Success rate | 95% Wilson CI | Attempts | Unavailable |
|---|---:|---:|---:|---:|---:|---:|
| catboost | 3 | 3 | 100.00% | 43.8%–100.0% | 3 | 0 |
| ensemble | 3 | 3 | 100.00% | 43.8%–100.0% | 3 | 0 |
| lightgbm | 3 | 3 | 100.00% | 43.8%–100.0% | 3 | 0 |
| xgboost | 3 | 3 | 100.00% | 43.8%–100.0% | 3 | 0 |
| ml-opencode-hybrid | 2 | 2 | 100.00% | 34.2%–100.0% | 2 | 0 |
| opencode-consensus | 2 | 2 | 100.00% | 34.2%–100.0% | 2 | 0 |
| opencode/longcat-2.5-preview-free | 2 | 2 | 100.00% | 34.2%–100.0% | 2 | 0 |
| opencode/mimo-v2.6-flash-free | 2 | 2 | 100.00% | 34.2%–100.0% | 2 | 0 |
| opencode/muse-spark-1.3-contributor-free | 2 | 2 | 100.00% | 34.2%–100.0% | 2 | 0 |
| opencode/space-bunny-free | 2 | 2 | 100.00% | 34.2%–100.0% | 2 | 0 |
| random-control-v1 | 2 | 2 | 100.00% | 34.2%–100.0% | 2 | 0 |
| opencode/nemotron-3-ultra-free | 1 | 1 | 100.00% | 20.7%–100.0% | 2 | 1 |
| opencode/nemotron-3.5-lightning-free | 1 | 1 | 100.00% | 20.7%–100.0% | 2 | 1 |
| dtong-main10 | 2 | 3 | 66.67% | 20.8%–93.9% | 3 | 0 |
| frequency-30 | 2 | 3 | 66.67% | 20.8%–93.9% | 3 | 0 |
| opencode/big-pickle | 1 | 2 | 50.00% | 9.5%–90.5% | 2 | 0 |
| opencode/cat-jam-free | 0 | 0 | — | — | 2 | 2 |
| opencode/step-5-preview-free | 0 | 0 | — | — | 2 | 2 |

Scored target issues: **3**.
Pending target issues: **1**.

Fixed three-digit choice chance baseline: **65.7%** (iid uniform assumption).
Do not compare models with tiny or different denominators as if they were equally tested.
Confidence intervals quantify sample uncertainty, not predictive superiority.
