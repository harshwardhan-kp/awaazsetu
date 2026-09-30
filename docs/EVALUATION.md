# Offline held-out evaluation

This harness scores independently labelled results that you supply. It does not generate labels, run extraction, read `.env`, or call a provider. The built-in synthetic template suite is a separate developer regression tool; it does not qualify as a held-out field evaluation. Keep evaluation reports outside version control when they contain resident data.

From the repository root:

```sh
.venv/bin/python scripts/evaluate_heldout.py --reports /path/reports.jsonl \
  --pairs /path/pairs.jsonl --voice /path/voice.jsonl \
  --feedback /path/feedback.csv --output /path/metrics.json
```

`--reports` is required; an empty file is accepted and yields null scores with zero sample counts. Other inputs and `--output` are optional. Without `--output`, results print as JSON. Invalid input produces a nonzero exit and an explanation. Every JSONL row requires a unique nonempty string `id` within its file. One object per line, UTF-8; blank lines are ignored. JSON booleans are required where specified. Inputs should use independently labelled expected values and actual measured predictions, never copied expected labels.

## Reports JSONL

Required keys: `id`, `language` (`en`, `hi`, `mr`), `expected`, `predicted`. Both objects require `incident_type` (`rescue`, `medical`, `water_in_home`, `road_waterlogging`, `other`) and `severity_band` (`critical`, `high`, `medium`, `low`). Optional `location_text` is a string or null and `coordinates` is `[latitude, longitude]` or null. Optional top-level `latency_ms` is a measured finite nonnegative number. Coordinate bounds are checked globally; no guessed Pune location is substituted.

Illustrative schema example only, not a measured report:

```json
{"id":"case-1","language":"mr","expected":{"incident_type":"rescue","severity_band":"critical","location_text":"Ekta Nagar school","coordinates":[18.478,73.819]},"predicted":{"incident_type":"rescue","severity_band":"high","location_text":"Ekta Nagar","coordinates":null},"latency_ms":1500}
```

Incident-type accuracy divides correct predictions by all report samples. Severity macro F1 averages per-class F1 across the union of observed gold/predicted bands, with gold and predicted counts exposed; absent classes are excluded rather than treated as successes. Critical recall uses gold critical reports as denominator. Report class coverage and language counts accompany results.

Location phrase token F1 is the mean per-sample multiset token F1 for non-null gold phrases. Empty gold and predicted tokens together are undefined and excluded from this metric; an empty prediction against a nonempty gold phrase scores zero. Normalization uses Unicode NFKC, case folding and punctuation/symbol removal while preserving Indic combining marks. This is textual phrase overlap, not geocoding accuracy. `location_within_500m` is the fraction of gold-coordinate cases whose predicted coordinate falls within 500 metres, using spherical haversine distance. Missing predicted coordinates count as failures; missing gold coordinates are excluded. Measured-distance counts and missing-prediction counts are exposed. Latency is the median of provided measured latencies; absent values are excluded. State which interval you measured, such as receipt to acknowledgement, when publishing results.

## Duplicate pairs JSONL

```json
{"id":"pair-1","same_event":true,"predicted_same_event":false}
```

Both labels are required JSON booleans. Compute TP/FP/FN/TN, precision, recall and pairwise F1 (`2 TP / (2 TP + FP + FN)`). Gold-positive/negative sample counts expose class coverage. All-negative correct pairs yield null F1 because its denominator is zero, not a claimed perfect duplicate score. Choose pairs independently across same/different locations, temporal windows and languages; do not pick only obvious matches. This is pairwise evaluation, not incident-cluster quality.

## Voice JSONL

```json
{"id":"voice-1","language":"mr","reference":"घरात पाणी आहे","transcript":"घरात पाणी"}
```

Required `language`, human-corrected `reference`, and actual `transcript` strings. Report aggregate WER per language as total word edit distance divided by total reference words, with sample, reference-word, edit and empty-reference counts. Normalize using the same Unicode rules as phrase evaluation. Word edit distance counts insertions, deletions and substitutions. Empty references contribute transcript insertions, but if an entire language has no reference words, its WER is null. WER can exceed one. This normalized WER does not assess preservation of emergency meaning, which needs separate human review.

## Feedback CSV

Header: `assisted,rating`; optional other columns are ignored. `assisted` accepts `true/false`, `yes/no`, or `1/0`, case insensitive. `rating` is a finite numeric value between 1 and 5. Blank cells are excluded from their individual metric denominator.

```csv
assisted,rating
yes,5
no,3
,
```

Report total responses, assistance-response count/rate, rating-response count, mean and median. Assistance reflects the respondent's supplied answer; it is not independently confirmed aid delivery.

Zero denominators yield JSON null. Missing inputs never produce claimed successful outcomes. Metrics require sufficient samples and class/language coverage and honest uncertainty before publication; this tool does not establish emergency readiness. Unit tests use tiny artificial values with hand-computed expected arithmetic and contain no field performance claims.
