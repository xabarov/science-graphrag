# External CV Hot Topics Live Audit

- Base URL: `http://127.0.0.1:18787`
- Workspace: `ws-pilot-od`
- Passed: **1 / 10**, failed: **9**

## Coverage
- web_search: 5
- web_fetch: 5
- final_answer: 3
- semantic_scholar: 5
- read_external_pdf: 5
- runtime_ok_cases: 4; tool_trace_ok_cases: 3; phoenix_ok_cases: 1

## Case Results
### sam3_architecture — SAM 3 promptable segmentation
- ok: `True`
- verdicts: runtime=True tool_trace=True phoenix=True
- trace id: `f856079d85ccb5173e7251bd0c893c32`
- tools: `coordinator_gate, route_to_specialist, route_to_specialist, web_search, semantic_scholar_search, web_fetch, semantic_scholar_paper, read_external_pdf, final_answer`
- quality: answer_len=969, citations=11, issues=[]
- answer preview: SAM 3 (Segment Anything Model 3) — это унифицированная модель для обнаружения, сегментации и отслеживания объектов на изображениях и видео с использованием концептуальных промптов, таких как словосочетания (например, "жёлтый школьный автобус") или примеры изображений. Архитектура модели включает общ

### open_vocabulary_detection — Open-vocabulary object detection
- ok: `False`
- verdicts: runtime=True tool_trace=False phoenix=False
- trace id: `34f4199a4fceb3c3a81ff530aacddf96`
- tools: `coordinator_gate, route_to_specialist, web_search, semantic_scholar_search, web_fetch, semantic_scholar_paper, unpaywall_lookup, web_fetch, read_external_pdf`
- quality: answer_len=2215, citations=14, issues=['missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: ### Обзор open-vocabulary object detection (2025–2026)

#### Лидирующие подходы
Современные методы open-vocabulary object detection (OVD) в 2025–2026 годах сфокусированы на интеграции предобученных визуально-языковых моделей (VLM), таких как CLIP и LLaMA, для распознавания объектов за пределами обуч

### video_diffusion_world_models — Video diffusion world models
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: `9f1b069bbf8b29073d53b2582f566686`
- tools: `coordinator_gate, route_to_specialist, official_web_lookup, web_search, semantic_scholar_search, semantic_scholar_paper, unpaywall_lookup, web_fetch, read_external_pdf, read_external_pdf, web_fetch, semantic_scholar_paper, unpaywall_lookup, web_fetch, web_fetch`
- quality: answer_len=107, citations=7, issues=['missing_final_answer_tool', 'phoenix_missing_final_answer_span']
- answer preview: I could not produce a complete final answer for this turn. Please rephrase the request or narrow the scope.

### vla_robotics — Vision-language-action for robotics
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: `5adc1fcbead4b739b16e7afe7d2a5a50`
- tools: `coordinator_gate`
- quality: answer_len=107, citations=0, issues=['missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'few_citations', 'phoenix_missing_final_answer_span']
- answer preview: I could not produce a complete final answer for this turn. Please rephrase the request or narrow the scope.

### gaussian_splatting — 3D Gaussian Splatting
- ok: `False`
- verdicts: runtime=True tool_trace=True phoenix=False
- trace id: `b8d8c2f98e2e0cc191a5b6e3d9672fcd`
- tools: `coordinator_gate, route_to_specialist, route_to_specialist, web_search, semantic_scholar_search, arxiv_search, arxiv_fetch, arxiv_search, semantic_scholar_paper, read_external_pdf, arxiv_fetch, arxiv_search, arxiv_fetch, read_external_pdf, arxiv_search, web_fetch, arxiv_search, final_answer`
- quality: answer_len=201, citations=17, issues=['phoenix_missing_final_answer_span']
- answer preview: The response time budget for this turn is almost exhausted, so the assistant stopped before starting another model step. Try a narrower question or increase SCIENCE_GRAPHRAG_AGENT_STEP_TIMEOUT_SECONDS.

### efficient_edge_cv — Efficient edge CV models
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: `ad7c9e02613d2efc2f8799cc56efa888`
- tools: `coordinator_gate`
- quality: answer_len=107, citations=0, issues=['missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'few_citations', 'phoenix_missing_final_answer_span']
- answer preview: I could not produce a complete final answer for this turn. Please rephrase the request or narrow the scope.

### medical_foundation_vision — Medical vision foundation models
- ok: `False`
- verdicts: runtime=True tool_trace=True phoenix=False
- trace id: `7f578a1917697e0e08474643efeccc58`
- tools: `coordinator_gate, route_to_specialist, route_to_specialist, web_search, semantic_scholar_search, unpaywall_lookup, unpaywall_lookup, unpaywall_lookup, unpaywall_lookup, unpaywall_lookup, web_fetch, arxiv_fetch, web_fetch, read_external_pdf, final_answer`
- quality: answer_len=201, citations=12, issues=['phoenix_missing_final_answer_span']
- answer preview: The response time budget for this turn is almost exhausted, so the assistant stopped before starting another model step. Try a narrower question or increase SCIENCE_GRAPHRAG_AGENT_STEP_TIMEOUT_SECONDS.

### synthetic_data_cv — Synthetic data pipelines for CV
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: `412cad175221f17f32ddebb85397fe43`
- tools: `coordinator_gate`
- quality: answer_len=107, citations=0, issues=['missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'few_citations', 'phoenix_missing_final_answer_span']
- answer preview: I could not produce a complete final answer for this turn. Please rephrase the request or narrow the scope.

### multimodal_pretraining_cv — Multimodal pretraining for CV
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: `ff440a4f99e69d0c7e16e73512659f39`
- tools: `coordinator_gate`
- quality: answer_len=107, citations=0, issues=['missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'few_citations', 'phoenix_missing_final_answer_span']
- answer preview: I could not produce a complete final answer for this turn. Please rephrase the request or narrow the scope.

### document_vlm_ocr_free — OCR-free VLM document understanding
- ok: `False`
- verdicts: runtime=False tool_trace=False phoenix=False
- trace id: `ec89fcb24edb7ad5d63e35ac2d3a238c`
- tools: `coordinator_gate`
- quality: answer_len=107, citations=0, issues=['missing_web_search', 'missing_web_fetch', 'missing_final_answer_tool', 'few_citations', 'phoenix_missing_final_answer_span']
- answer preview: I could not produce a complete final answer for this turn. Please rephrase the request or narrow the scope.

