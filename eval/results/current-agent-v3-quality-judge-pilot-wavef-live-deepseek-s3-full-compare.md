# Agent v3 quality judge — compare

- baseline: `eval/results/baseline-agent-v3-quality-judge-pilot-embedded.json`
- candidate: `eval/results/current-agent-v3-quality-judge-pilot-wavef-live-deepseek-s3-full.json`

## Summary deltas

- **mean_weighted_score_baseline**: `1.2346`
- **mean_weighted_score_candidate**: `1.4923`
- **mean_delta**: `0.2577`
- **pairwise_candidate_win_rate**: `0.1846`
- **pairwise_baseline_win_rate**: `-0.3231`
- **pairwise_tie_rate**: `0.1385`
- **hard_fail_count_baseline**: `2.0`
- **hard_fail_count_candidate**: `1.0`
- **cases_with_any_branch_non_ok**: `0.0`
- **all_passed**: `{'before': True, 'after': False}`
- **cost_delta**: `{'before': None, 'after': {'latency_p95_baseline_ms': 236755.0, 'latency_p95_candidate_ms': 228895.0, 'latency_p95_ratio': 0.9668, 'tokens_total_baseline': None, 'tokens_total_candidate': None, 'tokens_total_ratio': None, 'cases_with_latency_samples': 13, 'cases_with_token_samples_baseline': 0, 'cases_with_token_samples_candidate': 0}}`
