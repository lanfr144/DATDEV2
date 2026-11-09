# DORA metrics of the release scenario

Computed by `scripts/dora_metrics.py` from `release_history.ndjson` (18 events).

| DORA indicator | Value | Read as |
|---|---|---|
| Deployment frequency | 4 in 3.4 min (70/hour) | how often a new version reaches 100 % of users |
| Lead time for changes | 17 s | deploy on the idle slot -> in production (average) |
| Change failure rate | 40% (2/5: 1.1.0, 2.0.0) | changes rolled back after reaching users |
| Mean time to recover | 14 s | bad version exposed -> users back on a good one |

Version in production at the end: **2.0.2**.
