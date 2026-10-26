# Phase 1 — Independent Project Foundation

## 1. Summary

The ITGlasses copy was transformed into an independent project foundation named **AIAdmissionSimulator** in:

`D:\SistemasMaestria\AIAdmissionSimulator`

The original workspace `D:\SistemasMaestria\ITGlasses-master` was not modified. No Git repository or remote was created, no secrets were copied, and no Ollama/model installation was performed.

## 2. Files created, modified, and removed

### Created

- `backend/app/core/errors.py` — generic `AdmissionError` (with `KnowledgeError` compatibility alias).
- `backend/app/utils/document_extract.py` — reusable PDF/DOCX/TXT/Markdown extraction, moved out of the removed RAG knowledge package.
- `backend/app/db.py` — independent SQLite schema and initialization.
- `backend/app/services/candidate_service.py`
- `backend/app/services/session_service.py`
- `backend/app/services/question_bank_service.py`
- `backend/app/services/cv_analysis_service.py`
- `backend/app/services/answer_evaluation_service.py`
- `backend/app/services/report_service.py`
- `.venv/` — local virtual environment for the independent project (environment only, not source).

### Modified

- `backend/app/core/config.py` — rebranded app name/version; added `voice_enabled` and `database_path`; replaced `ITGLASSES_PROVIDER` with `AIADMISSION_PROVIDER`; added `OLLAMA_BASE_URL` override.
- `backend/app/main.py` — removed IT/RAG knowledge router and IT-specific error handling; conditional voice router; initializes independent SQLite DB; seeds question bank; registers service foundations.
- `backend/app/providers/ollama.py` — replaced IT support system prompt with generic AIAdmissionSimulator foundation prompt.
- `backend/app/providers/mock.py` — rebranded mock response.
- `backend/app/voice/service.py` — updated error import to generic errors module.
- `config.toml`, `.env.example` — rebranded and updated environment variable names.
- `frontend/index.html` — rebranded visible title/brand text.
- `scripts/start-backend.ps1` — uses `AIADMISSION_PROVIDER`.
- `tests/smoke_server.py`, `tests/smoke_ollama.py`, `tests/smoke_voice.py` — updated paths and environment variable names.

### Removed

- `backend/app/knowledge/` — IT enterprise RAG package (models, routes, service, store, retrieval, grounding, embeddings, social).
- `tests/smoke_knowledge.py`
- `tests/verify_knowledge_acceptance.py`
- `tests/fixtures/knowledge/`

Generic document extraction was preserved through `backend/app/utils/document_extract.py`.

## 3. New project structure (relevant additions)

```
AIAdmissionSimulator/
  backend/app/
    core/
      config.py
      errors.py
    db.py
    services/
      candidate_service.py
      session_service.py
      question_bank_service.py
      cv_analysis_service.py
      answer_evaluation_service.py
      report_service.py
    utils/
      document_extract.py
    providers/
      ollama.py
      mock.py
  storage/
    admission.db  (created at runtime)
```

## 4. Architecture decisions

- Reused FastAPI factory, typed settings, provider protocol, Ollama adapter transport, MockLLM, static frontend, and document extraction.
- Removed ITGlasses identity, IT support prompts, internal manuals, enterprise RAG knowledge base, and `D:\ITGlasses` paths.
- Voice components are preserved but disabled by default (`voice_enabled = false`).
- Independent SQLite database stores candidate profiles, interview sessions, questions, answers, CV analyses, evaluations, and reports.
- Question bank contains an initial seed of three foundation questions; full 30-question-per-category bank is deferred.
- CV analysis, answer evaluation, and reports are scaffolding only and do not implement full academic logic.
- Ollama integration remains configurable via `OLLAMA_BASE_URL` and provider selection; no model download or installation was performed.

## 5. Isolation verification

- Target directory: `D:\SistemasMaestria\AIAdmissionSimulator`.
- Source directory unchanged: `D:\SistemasMaestria\ITGlasses-master`.
- No `.git` directory or remote in target.
- No `ITGlasses`/`ITGLASSES` references in backend runtime, scripts, or configuration.
- No hardcoded `D:\ITGlasses` paths in runtime code.
- Independent database path: `storage/admission.db` under target.
- Ollama diagnostic: not installed, no `ollama` process, bundled runtime absent.
- Application starts with Ollama unavailable and reports clear `unavailable` status; chat returns `provider_unavailable` (HTTP 503), not fabricated AI output.

## 6. Tests executed and results

- Python compile: `python -m compileall backend` — passed.
- Import/startup: `import backend.app.main` — passed.
- Node frontend tests: `node --test tests/frontend.test.mjs tests/voice.test.mjs` — 26/26 passed.
- Smoke server: `tests/smoke_server.py` — PASS (health, status, chat, loopback listener).
- Ollama unavailable graceful check — PASS (`status=unavailable`, chat HTTP 503).
- Database/service scaffold check — passed (candidate, session, and question creation).
- Pytest collection: no `test_*.py` files; no failures reported.

## 7. Remaining limitations

- Ollama is not installed and no model is available; real LLM behavior was not verified.
- Full interview orchestration, rubric evaluation, CV analysis depth, and report generation are not implemented (Phase 1 scaffolding only).
- Voice remains disabled by default; real speech dependencies/models are not installed.
- Frontend still uses the legacy ITGlasses-era interface and will be redesigned in a later phase.
- SQLite schema is initial and may evolve in later phases.

## 8. Readiness assessment for Phase 2

Phase 1 foundation is complete and verified. The project is ready for Phase 2 implementation of candidate/interview domain logic, provided Ollama/model availability is addressed separately and without automatic downloads.
