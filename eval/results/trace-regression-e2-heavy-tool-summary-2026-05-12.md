# Trace Regression Compare

- Status: `fail`
- Delta missing spans: `0.0`
- Delta tool error rate: `0.0`
- Delta final_answer_missing: `0.0`
- Delta latency_p95_ms: `92007.0`
- Delta compaction_churn_score: `0.0`
- Delta shortlist_ratio_avg: `0.0`
- Delta deferred_schema_event_count: `0.0`
- Delta budget_cutoff_count: `0.0`
- Delta side_llm_cache_read_ratio_avg: `0.0`
- Delta subagent_lifecycle_missing_count: `0.0`
- Delta unnecessary_tool_calls_avg: `0.0`
- Delta writer_oscillation_count_max: `0.0`
- Baseline verdict rank: `2`
- Candidate verdict rank: `2`
- Delta live_trust_signal_avg: `None`
- Delta claim_verification_verdict_parse_rate: `None`
- Agent usage total tokens ratio (cand/base): `1.3770783947815268`
- Delta post_compact_paper_sources_restored_total: `0.0` (base=0.0, cand=0.0, compaction_events base=0.0 cand=0.0)

## Fail reasons
- side_llm_cache_read_ratio_avg:0.0000<0.4000
- latency_p95_regress_ratio:161262.0000>103882.5000

## Warn reasons
- latency_p95_increase:69255.0->161262.0
