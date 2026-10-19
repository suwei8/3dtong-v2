# Prospective Model Arena

Only one immutable pre-result forecast per target issue is scored.
Historical masked holdout runs are excluded from every statistic below.
Skipped/unavailable OpenCode calls are NOT counted as wrong predictions.

| Model | Hits | Valid votes | Success rate | 95% Wilson CI | Attempts | Unavailable |
|---|---:|---:|---:|---:|---:|---:|
| catboost | 4 | 4 | 100.00% | 51.0%–100.0% | 4 | 0 |
| ensemble | 4 | 4 | 100.00% | 51.0%–100.0% | 4 | 0 |
| lightgbm | 4 | 4 | 100.00% | 51.0%–100.0% | 4 | 0 |
| xgboost | 4 | 4 | 100.00% | 51.0%–100.0% | 4 | 0 |
| opencode/space-bunny-free | 3 | 3 | 100.00% | 43.8%–100.0% | 3 | 0 |
| random-control-v1 | 3 | 3 | 100.00% | 43.8%–100.0% | 3 | 0 |
| opencode/longcat-2.5-preview-free | 2 | 2 | 100.00% | 34.2%–100.0% | 3 | 1 |
| opencode/muse-spark-1.3-contributor-free | 2 | 2 | 100.00% | 34.2%–100.0% | 3 | 1 |
| opencode/nemotron-3.5-lightning-free | 1 | 1 | 100.00% | 20.7%–100.0% | 3 | 2 |
| frequency-30 | 3 | 4 | 75.00% | 30.1%–95.4% | 4 | 0 |
| ml-opencode-hybrid | 2 | 3 | 66.67% | 20.8%–93.9% | 3 | 0 |
| opencode-consensus | 2 | 3 | 66.67% | 20.8%–93.9% | 3 | 0 |
| opencode/mimo-v2.6-flash-free | 2 | 3 | 66.67% | 20.8%–93.9% | 3 | 0 |
| dtong-main10 | 2 | 4 | 50.00% | 15.0%–85.0% | 4 | 0 |
| opencode/nemotron-3-ultra-free | 1 | 2 | 50.00% | 9.5%–90.5% | 3 | 1 |
| opencode/big-pickle | 1 | 3 | 33.33% | 6.1%–79.2% | 3 | 0 |
| opencode/cat-jam-free | 0 | 0 | — | — | 3 | 3 |
| opencode/step-5-preview-free | 0 | 0 | — | — | 3 | 3 |

Scored target issues: **4**.
Pending target issues: **1**.

Fixed three-digit choice chance baseline: **65.7%** (iid uniform assumption).
Do not compare models with tiny or different denominators as if they were equally tested.
Confidence intervals quantify sample uncertainty, not predictive superiority.
