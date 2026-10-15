# 3dtong-v2

Independent, reproducible **research** arena for selecting three distinct digits from the next draw, using historical features and blind temporal evaluation. A fixed Top3 has **65.7%** theoretical hit probability under iid uniform three-digit draws; no current model has established an out-of-sample edge.

## Sources

Historical training source is the private `suwei8/pinble-data/data/k3_full_history_test.csv`. It intentionally omits the newest disclosed draws. **Never copy this CSV or its raw content into this public repository.**

The benchmark uses a separate private `data/k3_full_history.csv` exclusively for scoring predictions **after** their JSON files have been frozen and committed.

## Running locally

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m src.pipeline.predict --history /path/to/k3_full_history_test.csv --horizon 10
python -m src.pipeline.evaluate --full-history /path/to/k3_full_history.csv
```

## GitHub Actions

`PINBLE_DATA_TOKEN` must be set under repository Actions secrets and permit `Contents: Read` on private `suwei8/pinble-data`. The `GITHUB_TOKEN` has `contents: write` for saving predictions and reports to this public repository.

`daily-predict.yml`: Beijing 20:00 and 20:20 scheduler (UTC 12:00 and 12:20), guarded against writing late scheduled predictions after 21:00 China time. GitHub scheduled starts may be delayed: the schedule **cannot guarantee** a timely run. Push changes during development also trigger immediate testing/prediction. No raw private data are committed.

`daily-evaluate.yml`: separate job with full private data, triggered after prediction workflow, and Beijing 21:45 as a fallback. It compares only issue IDs present in previously committed, frozen forecast JSON. These masked recent historical test rounds are **retrospective holdout simulations**, not genuine future forecasts.

## Arena

XGBoost, LightGBM, CatBoost, equally weighted ensemble, frequency-30, original Main10 rule compete on identical historical validation windows. Model selection uses only validation history. The masked newest outcomes are never visible in prediction jobs. Ten-horizon forecasts deliberately share the same fixed-origin information: the system does not fabricate intermediate outcomes.

Cline free-model challenger is reserved for a separate isolated integration, because the Cline CLI official docs require provider authentication even for headless use. Never treat failed or unauthenticated model output as a valid prediction.

## Limits

If the private test CSV remains fixed at issue 2026263, repeated daily schedules freeze/reuse the **same** horizon targets 2026264–2026273; they do not generate genuinely new daily forecasts. Source updates or a different rolling feed are required for prospective production operation. Past masked outcomes may be known before a simulated forecast is created; this is *not* a prospective prediction experiment.
