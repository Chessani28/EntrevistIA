# Phase 2 — AI Admissions Interview Engine

## Summary

Phase 2 implements a functional Spanish-language AI admissions interview engine for the Master's Degree in Artificial Intelligence at Instituto Tecnológico El Llano Aguascalientes. It adds a 30-question admissions bank, independent interview sessions, a complete REST lifecycle, context preservation, and Ollama-backed follow-up generation with MockLLM support for automated tests.

Real Ollama validation is **BLOCKED** because Ollama is not installed or running in this environment.

## Architecture changes

- `backend/app/db.py`: migrated `interview_sessions` to store current question, position, start/completion timestamps, and JSON follow-up context; added a unique answer index; changed `connect()` to close SQLite connections reliably.
- `backend/app/services/question_bank_service.py`: replaced the 3-question scaffold with 30 deterministic questions across 10 admissions categories and reproducible mode selection.
- `backend/app/services/session_service.py`: added progress, answer listing, and JSON context persistence.
- `backend/app/services/interview_service.py`: new orchestration service for session lifecycle, question selection, answer submission, duplicate prevention, history, completion, and AI follow-up generation.
- `backend/app/providers/base.py`, `ollama.py`, `mock.py`: added `generate_with_system()` for committee-prompted structured generation.
- `backend/app/prompts/committee.py`: added the admissions committee system prompt.
- `backend/app/api/interview.py`: added versioned interview REST endpoints.
- `backend/app/api/schemas.py`: added typed interview request/response schemas.
- `backend/app/main.py`: registered interview routers and the interview service.
- `tests/test_interview_phase2.py`: added automated Phase 2 tests.

## Files created

- `backend/app/prompts/__init__.py`
- `backend/app/prompts/committee.py`
- `backend/app/services/interview_service.py`
- `backend/app/api/interview.py`
- `tests/test_interview_phase2.py`
- `IMPLEMENTATION_REPORTS/PHASE_2_INTERVIEW_ENGINE.md`

## Files modified

- `backend/app/db.py`
- `backend/app/providers/base.py`
- `backend/app/providers/ollama.py`
- `backend/app/providers/mock.py`
- `backend/app/services/question_bank_service.py`
- `backend/app/services/session_service.py`
- `backend/app/api/schemas.py`
- `backend/app/main.py`

## Question bank structure

Categories:

1. `academic_background`
2. `motivation`
3. `programming`
4. `algorithms`
5. `databases`
6. `ai_fundamentals`
7. `research_interests`
8. `professional_experience`
9. `time_management_stress`
10. `ethics_professional_goals`

- Total base questions: **30** (3 per category).
- Modes:
  - Quick: 5 questions
  - Standard: 10 questions
  - Complete: 15 questions
- Selection is deterministic by category and question ID.
- The mandatory stress question is `ts-01` and is always included in complete mode.
- The stress question is available in shorter modes when selected.


## API endpoints

Base paths: `/api/v1/interviews` and `/api/v1/sessions` (alias).

- `POST /` — create interview session
- `GET /{session_id}` — retrieve session status
- `POST /{session_id}/start` — start interview and select questions
- `GET /{session_id}/current-question` — retrieve current question
- `POST /{session_id}/answers` — submit an answer
- `GET /{session_id}/history` — retrieve interview history
- `POST /{session_id}/complete` — complete interview
- `POST /{session_id}/follow-up` — generate an AI follow-up question

## Session state design

States:

- `created`
- `in_progress`
- `completed`

Persisted fields include session ID, candidate ID, mode, question count, status, current question ID, current position, follow-up context JSON, start timestamp, and completion timestamp. Question history and answers are persisted in `session_questions` and `answers`.

Transitions are validated. Duplicate answers are rejected. Session data is restored from SQLite after a refresh.

## Ollama configuration

- Provider: configured through `AIADMISSION_PROVIDER`.
- Ollama URL: `http://127.0.0.1:11434` (loopback only).
- Configured model: `qwen3:4b-instruct-2507-q4_K_M`.
- Timeout: 120 seconds.
- Context length: 2048 tokens.
- Max output tokens: 256.
- Thinking: disabled.
- The application handles unavailable Ollama with explicit errors and never fabricates responses.

## Automated test results

Command:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Result:

- **11 passed**, 1 warning.
- Coverage includes session creation, modes, question selection, mandatory question inclusion, answer submission, duplicate prevention, context preservation, follow-up generation, database persistence/restoration, invalid requests, Ollama unavailable, malformed LLM output, and interview completion.

## Real-model test results

**BLOCKED.**

Ollama is not installed or running:

- `ollama` command not found.
- Bundled runtime path `storage\runtime\ollama-0.40.6\ollama.exe` is absent.
- `http://127.0.0.1:11434/api/tags` is unreachable.
- No models are installed.

No real model response was obtained, so real LLM integration is not claimed as successful.

### Installation instructions (manual, not performed)

1. Install Ollama for Windows from the official channel: https://ollama.com/download/windows
2. Start the service on `127.0.0.1:11434`.
3. Install a local instruction-following model, for example `qwen3:4b-instruct` or an equivalent Qwen instruct model compatible with available RAM.
4. Set `AIADMISSION_PROVIDER=ollama` and verify with `GET /api/v1/status`.
5. Run a real follow-up request and record the model response.

Given 15.3 GB RAM, a 4B Q4 instruction model is appropriate. Do not download models automatically.

## Known limitations

- Real Ollama behavior is unverified.
- Follow-up generation depends on model JSON compliance; malformed output is rejected with HTTP 502.
- Interview scoring/evaluation remains a Phase 1 scaffold and is not implemented in Phase 2.
- CV analysis, final PDF reporting, voice features, and complete UI redesign remain out of scope.

## Readiness assessment for Phase 3

Phase 2 is ready for Phase 3 pending approval. The interview engine, question bank, session persistence, API lifecycle, and MockLLM tests are implemented and passing. Real-model validation remains blocked until Ollama and a suitable model are installed manually.
