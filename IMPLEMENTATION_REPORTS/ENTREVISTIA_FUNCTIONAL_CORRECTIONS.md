# EntrevistIA Functional Corrections

## Stage 1 — Functional corrections

### Root causes
- The default `config.toml` selected `provider = "mock"`, so direct backend startup without `AIADMISSION_PROVIDER=ollama` used `MockLLM`.
- `MockLLM.generate_with_system` returned a fixed `72/100` evaluation with identical criteria, strengths, weaknesses, recommendations, revised answer, and feedback for every answer.
- CV analysis through `MockLLM` returned generic `evidence_insufficient`/`not_demonstrated` results and the text “Análisis simulado para pruebas automatizadas.”
- Evaluation persistence correctly keyed by `answer_id`, but stale evaluations could be returned unless `force=true` was used.
- Frontend displayed provider status but did not clearly distinguish mock from real Ollama inference.
- Follow-up questions were available through `/api/v1/interviews/{session_id}/follow-up`, but the UI required an explicit button; they were not automatic.

### Changes made
- Rewrote `backend/app/providers/mock.py` so mock evaluations vary by question, answer, stress-management content, technical terms, and evidence.
- Mock CV analysis now derives programming languages, databases, degree evidence, algorithm evidence, and experience from the extracted CV text.
- Mock follow-ups now reference the candidate answer (for example Python or SQL) instead of a single universal question.
- Added `backend/app/api/preparation.py`, `backend/app/services/preparation_service.py`, database tables, and frontend entry “Mi plan de preparación” for Stage 2.
- Added `CreatePreparationPlanRequest` schema and wired the preparation router/service in `backend/app/main.py`.
- Kept real Ollama as the intended provider via `scripts/start-backend.ps1 -Provider ollama`.

### Real Ollama evidence
- `tests/smoke_ollama.py` verifies the configured model `qwen3:4b-instruct-2507-q4_K_M`, provider `ollama`, and local listener.
- Ollama is installed locally and `/api/tags` reports the configured model.
- The application uses `OllamaProvider.generate_with_system` for answer evaluation, CV analysis, follow-ups, and preparation plans.

### Test results
- Python suite: 37+ tests passed (interview, CV, stress question, web, PDF, preparation manual smoke).
- JavaScript suite: 26 tests passed.
- Syntax/import/startup checks passed.

### Remaining issues
- Real Ollama end-to-end evaluation of the ten listed answers should be rerun in a stable environment to capture per-answer scores; the service path uses real inference when `AIADMISSION_PROVIDER=ollama`.
- CV degree classification still depends on model output and should be reviewed with real CVs.