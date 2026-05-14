# References resolution benchmark suite

Cases: 3

Model: mistralai/mistral-small-3.2-24b-instruct
Layer-1 prompt fingerprint: sha256-20:210f7e16d3e0a07ad571
Semantic prompt fingerprint: sha256-20:19c459f1df53094b0a19

## refs_mini_arxiv_id — PASS

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": true,
  "resolution_recall": 1.0,
  "resolution_precision": 1.0,
  "expected_count": 1,
  "predicted_count": 1,
  "matched_span_ids": [
    "span:arxiv_note"
  ],
  "missing_span_ids": [],
  "min_resolution_recall": 1.0
}
```


---

## refs_mini_doi_pair — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "resolution_recall": 0.0,
  "resolution_precision": 0.0,
  "expected_count": 2,
  "predicted_count": 0,
  "matched_span_ids": [],
  "missing_span_ids": [
    "bib:001",
    "bib:002"
  ],
  "min_resolution_recall": 1.0
}
```


---

## refs_mini_work_id — FAIL

```json
{
  "contract_only": false,
  "contract_passed": true,
  "passed": false,
  "resolution_recall": 0.0,
  "resolution_precision": 0.0,
  "expected_count": 1,
  "predicted_count": 0,
  "matched_span_ids": [],
  "missing_span_ids": [
    "span:internal_ref"
  ],
  "min_resolution_recall": 1.0
}
```
