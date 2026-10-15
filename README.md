# 3dtong-v2 — live digit-model arena

The repository now has two **strictly separate** research tracks.

## 1. Historical masked holdout (completed)

The permanent historical example was trained on the private, deliberately truncated
`suwei8/pinble-data/data/k3_full_history_test.csv` through **2026263**, and evaluated
against the hidden ten issue results 2026264–2026273. See
[`predictions/LATEST.md`](predictions/LATEST.md) and [`reports/leaderboard.md`](reports/leaderboard.md).
These 10 results are **retrospective simulations**, not evidence of genuine
pre-draw predictive performance.

## 2. Prospective live forecasts (automated)

Workflow [`daily predict`](.github/workflows/daily-predict.yml) runs twice before
21:10 Beijing (20:20 and 20:45, GitHub schedules are best effort). It reads
private **updated** `data/k3_full_history.csv`, uses **only completed `KaiJiang`**
rows, and targets the next issue (including a pending row if present).

- Fails closed if the result feed's CSV commit is older than 36 hours.
- Stops if current Beijing time is 21:10 or later.
- Freezes a **single** forecast per issue in `predictions/live/runs/ISSUE.json`.
- Never overwrites a forecast after new results become known.
- Shows the newest forecast in [`predictions/live/LATEST.md`](predictions/live/LATEST.md).
- Prints no private CSV contents and never commits `private-source/`.

Workflow [`daily evaluate`](.github/workflows/daily-evaluate.yml) runs after a
successful prediction workflow and at 21:45 Beijing. It scores only already-frozen
live forecasts, writing a **separate**
[`reports/live-leaderboard.md`](reports/live-leaderboard.md) and issue-level
hit/miss results without publishing the actual draw digits. Historical holdout
data never contributes to this prospective leaderboard.

**Important:** GitHub cron cannot guarantee exact delivery, and model accuracy
is not proven. A static Top3 has 65.7% theoretical hit rate under iid digits.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m src.pipeline.live --history /path/to/private/k3_full_history.csv
python -m src.pipeline.evaluate_live --full-history /path/to/private/k3_full_history.csv
```

Required repo Actions secret: `PINBLE_DATA_TOKEN` with read-only private
`suwei8/pinble-data` contents access. Default GitHub `GITHUB_TOKEN` needs
`contents:write` for forecasts and reports.

## Contestants

Trained XGBoost, LightGBM, CatBoost, equally-weighted ensemble, 30-issue digit
frequency baseline and `dtong-main10` (**a simplified public rule adapter,
not a verified reconstruction of the original 16-module application**).
Selection uses only chronological validation history; the models see no future results.

Cline MiMo free challenger: [`cline_mimo.py`](src/models/llm/cline_mimo.py)
is an opt-in **real CLI adapter** but requires provider credentials on the host.
No hosted Actions runner currently has a Cline login, and this contestant is
**not** represented as having predicted anything yet. Only valid CLI `run_result`
with exactly three distinct digits may enter the arena. Source private
data and GitHub secrets must never be exposed to the agent.
