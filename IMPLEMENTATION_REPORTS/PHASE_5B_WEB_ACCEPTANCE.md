# Phase 5B — Web Interface Acceptance Report

## 1. Browser and environment used

- Project: `D:\SistemasMaestria\AIAdmissionSimulator`
- Browser: Google Chrome 156.0.8078.48, headless, automated through Chrome DevTools Protocol (real browser engine, real DOM, real JavaScript execution).
- Backend: FastAPI on `http://127.0.0.1:8000`.
- AI provider: Ollama, model `qwen3:4b-instruct-2507-q4_K_M`, `mock=false`, `local_only=true`.
- Backend health at acceptance: `{"status":"ready","provider":"ollama","model":"qwen3:4b-instruct-2507-q4_K_M","mock":false,"rag_enabled":false,"local_only":true}`.
- Viewports tested: 1440x900 (desktop), 768x1024 (tablet), 390x844 (mobile).
- Automated CDP workflow screenshots saved under `.cache/acceptance/` (24 PNG files).
- No MockLLM was used; all CV and interview evaluations used real Ollama inference.

## 2. Pages tested

All navigation links were exercised and screenshots captured:

- Dashboard (`01-dashboard-desktop.png`, `02-dashboard.png`)
- Candidate profile (`02-profile.png`, `03-profile-created.png`)
- CV analysis (`02-cv.png`, `04-cv-uploaded.png`, `10-cv-deleted.png`)
- Interview simulator (`02-interview.png`, `05-interview-started.png`, `06-q1..q5-evaluated.png`, `07-interview-finished.png`)
- Question bank (`02-questions.png`)
- Results and history (`02-results.png`, `08-results.png`, `09-after-refresh.png`)
- System status (`02-system.png`)

## 3. Actual UI workflow results

1. Candidate profile created: profile ID displayed in UI.
2. Synthetic PDF CV uploaded through the real file input and UI submit flow.
3. Real Ollama CV analysis completed; UI displayed `Análisis completado` and a professional summary, strengths, missing evidence, recommendations, and requirement classification.
4. Five-question quick interview started (`mode=quick`, 5 questions).
5. All five questions answered through the textarea and submit button; each answer automatically triggered real AI evaluation.
6. Evaluations displayed with numeric score, criteria, feedback, disclaimer, and improved answer/practice tip.
7. Interview completed with `Finalizar entrevista`.
8. Results/history page displayed completed sessions and evaluations.
9. Browser refresh restored `ais_session_id` from localStorage and restored interview state.
10. CV deleted through `Eliminar CV y datos asociados`; UI showed `CV eliminado` / `No hay CV analizado`.

## 4. Console/network findings

- Browser page errors: `0`.
- Browser console errors: `0`.
- Failed network requests: `0`.
- No unhandled promise rejections or runtime exceptions observed during the full workflow.
- All API calls returned successful responses; slow inference (CV analysis and answer evaluation) completed within the configured timeouts.
## 5. Responsive test results

Representative viewport sizes tested:

- Desktop: 1440x900
- Tablet: 768x1024
- Mobile: 390x844

Results:

- Horizontal overflow: `0 px` on mobile; `-15 px` on desktop/tablet (no content clipping; negative values are scrollbar-related).
- Navigation converted to horizontal/static layout via media queries at <=980px.
- Form grids, card grids, status grids, upload rows, and question grids collapse to one column on small screens.
- No overlapping or clipped controls observed in screenshots.
- Text remains readable; headings use `clamp()`.

## 6. Reliability testing

- Duplicate submission prevention: backend rejects duplicate answers with HTTP 409 `duplicate_answer`; frontend disables the submit button while `state.interview.submitting` is true.
- Loading state during slow inference: UI shows `Subiendo y analizando CV…`, `CV subido. Iniciando análisis…`, and `Enviando respuesta y generando evaluación…`; buttons are disabled during submission.
- Invalid PDF handling: uploading non-PDF content returns HTTP 400 `invalid_file` with message `El archivo no es un PDF válido.`; frontend displays the error.
- Session restoration: verified after browser refresh; `ais_session_id` persisted and restored.
- Network failure handling: shared `api()` helper converts `TypeError` to `No se pudo conectar con el backend local...` and timeout to a clear message without claiming cancellation.
- No fabricated results: evaluations are generated only from submitted answers and validated JSON; prompts explicitly forbid inventing candidate data.
- Sensitive CV data: raw PDFs are stored server-side and deleted on request; public routes (`/`, `/ui/*`) serve only static frontend assets. API responses expose analysis, not raw CV text.

## 7. Defects discovered

No blocking visual or functional defects were found during the real-browser acceptance workflow.

Minor observations:

- Evaluation scores can repeat for identical synthetic answer text; this is test-data behavior, not a product defect.
- The CV analysis text in the UI is compact because of rendered text; no layout breakage.
- Responsive overflow measurements are slightly negative on desktop/tablet due to scrollbar width, not content clipping.

## 8. Fixes implemented

No code changes were required during Phase 5B. The acceptance test used the existing Phase 5 implementation unchanged. Validation scripts and screenshots were added under `.cache/acceptance/`.

## 9. Automated test results

- Python: `26 passed, 1 warning` (`pytest -q`).
- JavaScript: `26 passed, 0 failed` (`node --test tests/frontend.test.mjs tests/voice.test.mjs`).
- Syntax: `node --check frontend/app.js` passed.
- Additional manual checks: invalid PDF upload returns HTTP 400; duplicate answer submission returns HTTP 409; backend health reports Ollama ready.

## 10. Remaining limitations

- No real interactive human user was used; automation used Chrome DevTools Protocol to perform actual DOM interactions and real backend calls.
- Screenshots are headless captures; visual polish was assessed through code and captured layouts, not a manual design review by a human.
- Ollama unavailability was not induced by stopping the service; error presentation is implemented and covered by the shared API error handling, but not exercised live.
- Voice features were not part of this acceptance scope.

## 11. Recommendation

GO for Phase 6.

