# EntrevistIA Integration Validation

## 1. Scope and method

This report consolidates the real-Ollama integration validation for EntrevistIA. Validation used the local Ollama provider (`qwen3:4b-instruct-2507-q4_K_M`) with `mock=false`, `rag_enabled=false`, and `local_only=true`. No MockLLM was used for the reported real-provider checks.

Evidence sources:
- `IMPLEMENTATION_REPORTS/PHASE_5B_WEB_ACCEPTANCE.md`
- `IMPLEMENTATION_REPORTS/PHASE_7_FINAL_INTEGRATION_AUDIT.md`
- `IMPLEMENTATION_REPORTS/REQUIREMENTS_MATRIX.md`
- `IMPLEMENTATION_REPORTS/ENTREVISTIA_PERSONALIZED_PREPARATION.md`
- `cv_real_results.json`
- `prep_simple_results.json`
- `prep_compare_results.json`
- `scoring_real_test.py` / `scoring_real.out`
- Current regression test runs

## 2. Startup configuration validation

Configuration validated:
- Provider: `ollama`
- Ollama URL: `http://127.0.0.1:11434`
- Model: `qwen3:4b-instruct-2507-q4_K_M`
- Host binding: `127.0.0.1:8000`
- Context length: `4096`
- Max output tokens: `2048`
- Thinking: `false`
- Timeout: `120.0s`
- Health timeout: `5.0s`
- Keep alive: `30s`
- Voice enabled: `false`
- Database: `storage/admission.db`

Observed behavior:
- Ollama `/api/tags` responds and lists `qwen3:4b-instruct-2507-q4_K_M`.
- `/api/v1/status` reports `ready`, `mock=false`, `rag_enabled=false`, `local_only=true`.
- Settings validation rejects non-loopback Ollama URLs, non-local model names, invalid host binding, and out-of-range timeout/context values.

Result: **PASS**

## 3. CV analysis validation

Real CV analysis was exercised with at least two synthetic CV profiles:
- Ana Pérez: Informática degree, Data Science master's degree, Python/Java/SQL, PostgreSQL, AI project evidence.
- Carlos Gomez: Systems Engineering background, MySQL/Oracle, JavaScript/TypeScript, generic support experience.

Observed behavior:
- Analysis status: `completed`.
- Professional summary, strengths, missing/unclear evidence, recommendations, and requirement classification were generated.
- Extracted evidence included education, degrees, programming languages, databases, projects, and experience snippets.
- Timing: approximately `43.03s` for the stronger CV.

Known limitation:
- CV degree extraction remains imperfect for some synthetic CVs. In Phase 7, the mandatory degree requirement was marked `not_demonstrated` even though the CV text contained `B.Sc. in Computer Systems Engineering`; the `degrees` field also captured an interest statement instead of the degree. This is tracked as a future CV extraction hardening item and does not invalidate the integration run.

Cleanup behavior:
- `DELETE /api/v1/cv/{analysis_id}` removes the stored PDF, removes empty storage directories, and deletes the database row.
- Browser acceptance verified the UI shows `CV eliminado` / `No hay CV analizado`.

Result: **PASS with documented CV extraction limitation**

## 4. Personalized preparation validation

Validated behavior:
- Candidate profile creation works.
- Quick interview completion works.
- `POST /api/v1/preparation` generated a plan with `4` activities.
- Activity completion updated progress to `1` of `4` (`25.0%`).
- Plan retrieval after creating a new app instance returned the same plan ID and progress, confirming SQLite persistence.
- `GET /api/v1/preparation/candidate/{id}/interviews` returned comparison data when the interview was linked to a candidate ID.

Observed result artifact:
- `prep_simple_results.json`: candidate, session, plan, 4 activities, 25% progress, persisted plan.

Limitation:
- Comparison average scores can be `null` when interviews were completed without answer evaluations or when an interview was not linked to a candidate ID. Plan generation and progress persistence themselves passed.

Result: **PASS for plan generation and persistence**
PY
## 5. Browser workflow validation

Source: `PHASE_5B_WEB_ACCEPTANCE.md`.

Validated with real Chrome through Chrome DevTools Protocol:
- Dashboard, profile, CV analysis, interview simulator, question bank, results/history, and system status pages.
- Candidate profile creation.
- Real PDF CV upload and real Ollama CV analysis.
- Five-question quick interview with real answer evaluation.
- Interview completion.
- Results/history display.
- Browser refresh restoring `ais_session_id` and interview state.
- CV deletion through the UI.

Console/network findings:
- Page errors: `0`
- Console errors: `0`
- Failed network requests: `0`

Responsive testing:
- Viewports: `1440x900`, `768x1024`, `390x844`
- Horizontal overflow: `0 px` mobile; scrollbar-related negative values on desktop/tablet.

Reliability:
- Duplicate answer submission rejected with HTTP `409 duplicate_answer`.
- Invalid PDF upload rejected with HTTP `400 invalid_file`.
- Loading states shown during slow inference.
- Session restoration verified.

Result: **PASS**

## 6. Answer evaluation and scoring validation

Real scoring path exercised:
- `scoring_real_test.py` created a quick interview, submitted an answer, and called `/api/v1/evaluations/{sid}/questions/{qid}/evaluate`.
- Output included `score`, `technical_accuracy`, and 10 criteria.
- Observed irrelevant answer result: overall score `0`, with applicable criteria such as clarity/coherence/depth still scored independently, while `relevance` and `technical_accuracy` were marked `insufficient_evidence`.

Phase 7 real evaluation evidence:
- 10 evaluations generated, one per answer.
- 10 criteria per evaluation: relevance, clarity, coherence, technical accuracy, depth, professionalism, confidence, naturalness, evidence/examples, practical reasoning.
- Score range: `0` to `85`.
- Mean score: `65.5` including one deliberately irrelevant follow-up; `72.8` excluding it.
- The zero score is an appropriate insufficient-evidence result, not a forced nonzero score.
- Evaluations include criterion explanations, strengths, weaknesses, recommendations, revised answers, practice tips, technical accuracy claims, and stress-management feedback.
- No admission probability is estimated.

Partial credit behavior:
- Criteria are normalized independently.
- `overall_score` is produced by the model and is not hard-coded to zero by backend code.
- Weak or irrelevant answers can receive `0` when the model determines insufficient evidence, while partially supported answers can receive intermediate scores.

Result: **PASS**

## 7. Performance observations

Measured observations:
- CV analysis: approximately `43.03s` for the stronger synthetic CV.
- Answer evaluation: Phase 7 measured `477.922s` for 10 evaluations, approximately `47.8s` per evaluation on average. Cold runs may take longer.
- Regression tests: `37 passed` in `22.22s`.
- Frontend tests: `26 passed` in approximately `2.66s`.

Limitation:
- Ollama runs CPU-only in this environment. Inference latency is acceptable for academic demonstration but not a performance benchmark.

Result: **PASS with documented latency**

## 8. Cleanup validation

Validated:
- CV deletion removes the stored file and database analysis row.
- Empty CV storage directories are removed when possible.
- UI reflects deleted state.
- Test artifacts and logs remain in the project directory for evidence; no automatic repository cleanup was performed.

Result: **PASS**

## 9. Regression tests

Python:
- Command: `pytest -q`
- Result: `37 passed, 1 warning`
- Warning: Starlette/httpx deprecation warning only.

JavaScript:
- Command: `node --test tests/frontend.test.mjs tests/voice.test.mjs`
- Result: `26 passed, 0 failed`

Syntax:
- Command: `node --check frontend/app.js`
- Result: passed.

Result: **PASS**

## 10. Known limitations

- No authentication or RBAC; isolation relies on unguessable session IDs.
- AI scores are preparation feedback, not validated psychometric measurements.
- CV degree extraction has a known classification inconsistency for the synthetic CV.
- Ollama inference is CPU-bound and can take tens of seconds per operation.
- Phase 5 speech/voice acceptance remains pending and is outside this validation scope.
- Personalized preparation comparison depends on interviews being linked to candidate IDs and, for meaningful averages, on completed answer evaluations.

## 11. Conclusion

EntrevistIA passed integration validation across startup configuration, real Ollama CV analysis, personalized preparation, browser workflow, answer evaluation/scoring, cleanup, and regression tests. The system is suitable for academic delivery with the documented limitations.

Final recommendation: **GO for academic delivery.**
PY