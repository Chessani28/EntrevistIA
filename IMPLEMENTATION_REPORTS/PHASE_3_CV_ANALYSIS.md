# Phase 3 — Academic CV Analysis Engine

## Summary

Phase 3 implements a privacy-conscious academic CV analysis engine for candidates preparing for admission to the Master's Degree in Artificial Intelligence at Instituto Tecnológico El Llano Aguascalientes. It reuses the independent SQLite database and PDF extraction infrastructure, adds private CV storage, structured AI evaluation through the Ollama provider abstraction, evidence-based findings, and a versioned REST lifecycle.

Real Ollama validation remains **BLOCKED** because Ollama is not installed or running in this environment.

## Architecture changes

- `backend/app/db.py`: expanded `cv_analyses` with private storage metadata, status, extracted evidence, structured analysis results, errors, timestamps, and migration support.
- `backend/app/core/config.py`: added configurable CV storage path and upload size limit.
- `backend/app/services/cv_analysis_service.py`: implemented secure upload validation, PDF text/evidence extraction, candidate association, private storage, analysis orchestration, structured Ollama evaluation, status/result retrieval, and deletion.
- `backend/app/prompts/cv_evaluator.py`: added a dedicated Spanish academic CV evaluator prompt and strict JSON contract.
- `backend/app/api/cv.py`: added versioned CV endpoints.
- `backend/app/api/schemas.py`: added typed CV request/response and LLM output schemas.
- `backend/app/main.py`: registered CV routers and extended upload-size middleware.
- `backend/app/providers/mock.py`: made MockLLM return valid CV analysis JSON only in test contexts.
- `tests/test_cv_phase3.py`: added Phase 3 automated tests.

## Files created

- `backend/app/prompts/cv_evaluator.py`
- `backend/app/api/cv.py`
- `tests/test_cv_phase3.py`
- `IMPLEMENTATION_REPORTS/PHASE_3_CV_ANALYSIS.md`

## Files modified

- `backend/app/db.py`
- `backend/app/core/config.py`
- `backend/app/services/cv_analysis_service.py`
- `backend/app/api/schemas.py`
- `backend/app/main.py`
- `backend/app/providers/mock.py`

## API endpoints

Base paths: `/api/v1/cv`, `/api/v1/cvs`, `/api/v1/cv-analysis`, and `/api/v1/cv-analyses` (aliases).

- `POST /` or `POST /upload` — upload a CV
- `POST /{analysis_id}/analyze` (aliases: `/analysis`, `/start`, `/start-analysis`) — start AI analysis
- `GET /{analysis_id}` (aliases: `/analysis`, `/result`, `/results`) — retrieve analysis results
- `GET /{analysis_id}/status` — retrieve analysis status
- `DELETE /{analysis_id}` (alias: `/delete`) — delete uploaded CV data

## Privacy protections

- Only PDF files are accepted; magic bytes and extraction validation are enforced.
- Configurable size limit is enforced.
- Filenames are sanitized and files are stored under a private directory using an analysis-specific filename.
- Uploaded CVs are not served through any public or unauthenticated file route.
- Raw CV contents are not logged.
- Analysis deletion removes the private file and database row.
- Private storage paths are not exposed in API responses.

## Extraction validation

- Reuses `backend/app/utils/document_extract.py`.
- Extracts education, degrees, programming languages, database experience, technical skills, software projects, AI-related experience, professional experience, certifications, and research interests when present.
- Preserves evidence snippets and page/paragraph references.
- Reports uncertainty and never fabricates candidate data.
- Encrypted, corrupted, empty, and unreadable PDFs produce clear HTTP errors.

## Evidence-based evaluation

- Requirements are classified as `evidence_found`, `evidence_insufficient`, or `not_demonstrated`.
- Mandatory academic eligibility is distinguished from recommended skills.
- Missing evidence is not treated as lack of ability.
- No unsupported numerical admission probabilities are generated.
- AI output is treated as preparation feedback, not an official admissions decision.

## Test results

Command:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Result:

- **24 passed**, 1 warning.
- Includes all 11 Phase 2 tests and 13 Phase 3 tests.
- Coverage includes valid upload, invalid types, oversized files, corrupted PDFs, empty documents, text extraction, evidence classification, structured LLM output validation, missing information, Ollama unavailable, database persistence, CV deletion, and private file access protection.

## Real Ollama integration status

**BLOCKED.**

Ollama is not installed or running in this environment. The implementation uses the provider abstraction and returns an explicit unavailable-provider status (HTTP 503) when Ollama cannot be reached. MockLLM is used only for automated tests.

## Known limitations

- Real Ollama behavior is unverified.
- Heuristic evidence extraction is conservative and may miss information expressed in unusual formats.
- Scanned PDFs without OCR are not supported.
- No final PDF report or frontend redesign is included, per Phase 3 boundaries.

## Phase 4 readiness assessment

Phase 3 is ready for Phase 4 pending approval. The CV analysis lifecycle, private storage, structured AI evaluation, persistence, deletion, and automated tests are implemented and passing. Real-model validation remains blocked until Ollama and a suitable model are installed manually.