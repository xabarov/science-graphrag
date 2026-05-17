# External CV Hot Topics Live Audit

- Base URL: `http://127.0.0.1:18787`
- Workspace: `ws-pilot-od`
- Lane label: `baseline`
- Passed: **4 / 10**, failed: **6**

## Coverage
- web_search: 5
- web_fetch: 5
- final_answer: 5
- semantic_scholar: 5
- read_external_pdf: 3
- runtime_ok_cases: 5; tool_trace_ok_cases: 5; phoenix_ok_cases: 4
- final_answer_validation_present: 5; validation_fail_cases: 0; generic_fallback_with_evidence_cases: 0
- terminal_reason_present: 5
- terminal_reason_distribution: `{'partial_final_answer': 1, 'final_answer_ok': 2, 'budget_exhausted_with_partial': 2, 'missing': 5}`

## Next-slice gates
- all_ok: `False`
- runtime_ok_cases: `{'ok': False, 'actual': 5, 'minimum': 6}`
- tool_trace_ok_cases: `{'ok': False, 'actual': 5, 'minimum': 6}`
- phoenix_ok_cases: `{'ok': False, 'actual': 4, 'minimum': 5}`
- with_final_answer: `{'ok': False, 'actual': 5, 'minimum': 8}`
- generic_fallback_with_evidence_cases: `{'ok': True, 'actual': 0, 'maximum': 0}`

## Case Results
### sam3_architecture — SAM 3 promptable segmentation
- ok: `True`
- verdicts: runtime=True tool_trace=True phoenix=True
- trace id: `eedfe20b17ea7d6798691e013a9109aa`
- tools: `coordinator_gate, route_to_specialist, route_to_specialist, web_search, semantic_scholar_search, web_fetch, unpaywall_lookup, read_external_pdf, final_answer`
- quality: answer_len=719, citations=7, issues=[]
- final_answer_validation: status=ok reasons=['partial_answer_ok'] evidence_present=True
- terminal_reason: `partial_final_answer`
- answer preview: По текущим данным, официальной архитектуры SAM 3 в компьютерном зрении не обнаружено. Была найдена работа *SAM-Mamba: Mamba Guided SAM Architecture for Generalized Zero-Shot Polyp Segmentation*, которая представляет собой модификацию оригинального Segment Anything Model (SAM), но не является его тре

### open_vocabulary_detection — Open-vocabulary object detection
- ok: `True`
- verdicts: runtime=True tool_trace=True phoenix=True
- trace id: `9ea06e9ceb6b6dd2510864a057ef7591`
- tools: `coordinator_gate, route_to_specialist, route_to_specialist, web_search, semantic_scholar_search, web_fetch, unpaywall_lookup, web_fetch, web_search, web_fetch, unpaywall_lookup, web_search, arxiv_search, final_answer`
- quality: answer_len=986, citations=7, issues=[]
- final_answer_validation: status=ok reasons=['answer_ok'] evidence_present=True
- terminal_reason: `final_answer_ok`
- answer preview: На основе проведённого исследования, обзор современных подходов к open-vocabulary object detection (2025-2026) ограничен доступностью информации. Были выявлены несколько потенциальных источников, включая обзорную статью (DOI: 10.1016/j.procs.2025.08.008) и работы по применению технологии в дистанцио

### video_diffusion_world_models — Video diffusion world models
- ok: `True`
- verdicts: runtime=True tool_trace=True phoenix=True
- trace id: `3a02598108d899284fd86b00642d3e1b`
- tools: `coordinator_gate, route_to_specialist, route_to_specialist, web_search, semantic_scholar_search, web_fetch, web_fetch, unpaywall_lookup, web_fetch, read_external_pdf, web_search, web_fetch, web_fetch, read_external_pdf, web_search, web_fetch, web_fetch, final_answer`
- quality: answer_len=977, citations=13, issues=[]
- final_answer_validation: status=ok reasons=['answer_ok'] evidence_present=True
- terminal_reason: `budget_exhausted_with_partial`
- answer preview: Горячим трендом в области computer vision является адаптация video diffusion моделей для создания world models, что позволяет системам лучше понимать и предсказывать динамику визуальной среды. Конкретная работа "AVID: Adapting Video Diffusion Models to World Models" упоминается в нескольких веб-исто

### vla_robotics — Vision-language-action for robotics
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: ``
- tools: ``
- quality: answer_len=0, citations=0, issues=['request_failed', 'empty_answer', 'few_citations', 'request_error', 'missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: 

### gaussian_splatting — 3D Gaussian Splatting
- ok: `True`
- verdicts: runtime=True tool_trace=True phoenix=True
- trace id: `da1c723a139553bb4ca0758613478e71`
- tools: `coordinator_gate, route_to_specialist, route_to_specialist, web_search, semantic_scholar_search, web_fetch, unpaywall_lookup, arxiv_search, web_fetch, web_fetch, read_external_pdf, web_search, web_fetch, web_fetch, unpaywall_lookup, arxiv_search, corpus_explore, final_answer`
- quality: answer_len=1494, citations=12, issues=[]
- final_answer_validation: status=ok reasons=['partial_answer_ok'] evidence_present=True
- terminal_reason: `budget_exhausted_with_partial`
- answer preview: На основе доступных данных, полное сравнение технологий 3D Gaussian Splatting (3DGS) и Neural Radiance Fields (NeRF) с анализом конкретной научной публикации невозможно из-за ограниченного доступа к полнотекстовому контенту.

Было идентифицировано несколько потенциально релевантных источников, включ

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
- verdicts: runtime=True tool_trace=True phoenix=False
- trace id: `3a616fbab50d05faad80dcf60410ac7b`
- tools: `coordinator_gate, route_to_specialist, route_to_specialist, web_search, semantic_scholar_search, idea_search, web_fetch, web_fetch, find_works, semantic_scholar_search, semantic_scholar_search, idea_search, workspace_inspect, paper_profile, paper_quote_search, final_answer`
- quality: answer_len=3092, citations=7, issues=['phoenix_missing_final_answer_span']
- final_answer_validation: status=ok reasons=['answer_ok'] evidence_present=True
- terminal_reason: `final_answer_ok`
- audit_diagnostics: `{'phoenix_missing_final_answer_span': 'missing_span_but_tool_trace_present'}`
- answer preview: ### Обзор OCR-free VLM для понимания документов: анализ компоновки, таблиц/диаграмм и рисков в производстве

#### Ключевые архитектуры и подходы
OCR-free визуальные языковые модели (VLM) для понимания документов представляют собой конвейеры, которые напрямую обрабатывают пиксели изображений документ

