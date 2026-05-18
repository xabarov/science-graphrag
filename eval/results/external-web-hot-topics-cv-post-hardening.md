# External CV Hot Topics Live Audit

- Base URL: `http://127.0.0.1:18787`
- Workspace: `ws-pilot-od`
- Lane label: `post-hardening`
- Passed: **1 / 10**, failed: **9**

## Coverage
- web_search: 1
- web_fetch: 1
- final_answer: 1
- semantic_scholar: 1
- read_external_pdf: 1
- runtime_ok_cases: 1; tool_trace_ok_cases: 1; phoenix_ok_cases: 1
- final_answer_validation_present: 1; validation_fail_cases: 0; generic_fallback_with_evidence_cases: 0
- terminal_reason_present: 1
- terminal_reason_distribution: `{'budget_exhausted_with_partial': 1, 'missing': 9}`

## Next-slice gates
- all_ok: `False`
- runtime_ok_cases: `{'ok': False, 'actual': 1, 'minimum': 6}`
- tool_trace_ok_cases: `{'ok': False, 'actual': 1, 'minimum': 6}`
- phoenix_ok_cases: `{'ok': False, 'actual': 1, 'minimum': 5}`
- with_final_answer: `{'ok': False, 'actual': 1, 'minimum': 8}`
- generic_fallback_with_evidence_cases: `{'ok': True, 'actual': 0, 'maximum': 0}`

## Case Results
### sam3_architecture — SAM 3 promptable segmentation
- ok: `True`
- verdicts: runtime=True tool_trace=True phoenix=True
- trace id: `1194fb8811fd49d269207bf8e27609af`
- tools: `coordinator_gate, route_to_specialist, route_to_specialist, web_search, semantic_scholar_search, web_fetch, semantic_scholar_search, web_search, web_fetch, web_fetch, web_search, web_fetch, web_fetch, web_fetch, unpaywall_lookup, read_external_pdf, final_answer`
- quality: answer_len=1120, citations=12, issues=[]
- final_answer_validation: status=ok reasons=['partial_answer_ok'] evidence_present=True
- terminal_reason: `budget_exhausted_with_partial`
- answer preview: На основе доступной информации, официальная архитектура "SAM 3" в компьютерном зрении не подтверждена. Вместо этого, текущая версия — это Segment Anything Model (SAM), представленный Meta AI.

SAM — это фундаментальная модель для сегментации изображений, способная к сегментации объектов без предвари

### open_vocabulary_detection — Open-vocabulary object detection
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: ``
- tools: ``
- quality: answer_len=0, citations=0, issues=['request_failed', 'empty_answer', 'few_citations', 'request_error', 'missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: 

### video_diffusion_world_models — Video diffusion world models
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: ``
- tools: ``
- quality: answer_len=0, citations=0, issues=['request_failed', 'empty_answer', 'few_citations', 'request_error', 'missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: 

### vla_robotics — Vision-language-action for robotics
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: ``
- tools: ``
- quality: answer_len=0, citations=0, issues=['request_failed', 'empty_answer', 'few_citations', 'request_error', 'missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: 

### gaussian_splatting — 3D Gaussian Splatting
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: ``
- tools: ``
- quality: answer_len=0, citations=0, issues=['request_failed', 'empty_answer', 'few_citations', 'request_error', 'missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: 

### efficient_edge_cv — Efficient edge CV models
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: ``
- tools: ``
- quality: answer_len=0, citations=0, issues=['request_failed', 'empty_answer', 'few_citations', 'request_error', 'missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: 

### medical_foundation_vision — Medical vision foundation models
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: ``
- tools: ``
- quality: answer_len=0, citations=0, issues=['request_failed', 'empty_answer', 'few_citations', 'request_error', 'missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: 

### synthetic_data_cv — Synthetic data pipelines for CV
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: ``
- tools: ``
- quality: answer_len=0, citations=0, issues=['request_failed', 'empty_answer', 'few_citations', 'request_error', 'missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: 

### multimodal_pretraining_cv — Multimodal pretraining for CV
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: ``
- tools: ``
- quality: answer_len=0, citations=0, issues=['request_failed', 'empty_answer', 'few_citations', 'request_error', 'missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: 

### document_vlm_ocr_free — OCR-free VLM document understanding
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: ``
- tools: ``
- quality: answer_len=0, citations=0, issues=['request_failed', 'empty_answer', 'few_citations', 'request_error', 'missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: 

