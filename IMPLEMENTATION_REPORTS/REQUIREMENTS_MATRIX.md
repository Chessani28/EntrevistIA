# Requirements Matrix — AI Admission Simulator

## Academic requirements

| ID | Requirement | Actual implementation | Demonstrated behavior | Evidence | Status |
|---|---|---|---|---|---|
| R1 | Admissions interview question bank with 30 base questions | `QuestionBankService.seed_questions()` seeds 33 base questions; `select_questions(mode)` returns 5/10/15. | Bank count verified as >=30; mode counts verified. | `ui_questions.png`, Phase 6/7 reports | PASS |
| R2 | Mandatory stress/time-management question in every interview | `QuestionBankService.select_questions()` now forces `ts-01` in every mode while preserving 5/10/15 base questions. | Quick, standard, and complete modes include `ts-01` exactly once; real Ollama quick-mode report contains the question and its evaluation. | `question_bank_service.py`, `test_r2_stress_question.py`, `.cache/verify_out.txt`, `.cache/ollama_quick_report.pdf` | PASS |
| R3 | Evaluation of professional, confident, natural communication | `AnswerEvaluationService` normalizes 10 criteria including `professionalism`, `confidence`, and `naturalness`. | 10 real evaluations contain criterion-level scores and explanations. | `evaluation_*.json`, Phase 7 audit | PASS |
| R4 | PDF CV upload and analysis | CV upload, PDF extraction, storage, LLM analysis, requirement classification, report integration. | E2E CV analysis completed; findings included in report. Degree extraction has a known classification inconsistency. | `cv_analysis.json`, `reporte_e2e.pdf` | PASS |
| R5 | Realistic AI-driven interview and contextual follow-up | `InterviewService` plus `generate_followup()` creates contextual follow-up questions from candidate answers. | E2E run: 5 base + 5 follow-up answers, all steps `ok=true`. | `e2e_results.json` | PASS |
| R6 | Detailed evaluation and improvement feedback | Per-answer evaluations with scores, criteria, strengths, weaknesses, recommendations, revised answers, tips. | 10 evaluations generated; report contains aggregate feedback. | `evaluation_*.json`, `reporte_e2e.pdf` | PASS |
| R7 | Personalized interview closing statements | `ReportService` closing message based on candidate name and performance band. | Report includes personalized closing and academic disclaimer. | `reporte_e2e.pdf` | PASS |
| R8 | Personalized AI preparation plan | `PreparationService` plus `/api/v1/preparation` and frontend “Mi plan de preparación” | Plan generation, activity completion, progress persistence, interview comparison smoke-tested. | `ENTREVISTIA_PERSONALIZED_PREPARATION.md` | PASS |

## Phase 7 technical and quality requirements

| ID | Requirement | Implementation / verification | Evidence | Status |
|---|---|---|---|---|
| P7-1 | Real Ollama end-to-end validation | E2E with real provider, `mock=false` | `.cache/e2e_out.txt`, `e2e_results.json` | Complete |
| P7-2 | CV upload and analysis in E2E | Upload plus completed analysis before interview | `cv_analysis.json` | Complete |
| P7-3 | Interview loop with follow-ups | 5 base + 5 follow-up answers | `e2e_results.json` | Complete |
| P7-4 | Completion and history | Completed session plus history retrieval | `history.json` | Complete |
| P7-5 | Per-answer evaluation | 10 evaluations, 10 criteria each | `evaluation_*.json` | Complete |
| P7-6 | PDF download | On-demand PDF, 23 pages | `reporte_e2e.pdf` | Complete |
| P7-7 | Session restore | Restored completed session, position 5/5 | E2E output | Complete |
| P7-8 | Artifact persistence | JSON, evaluations, PDF, results | `IMPLEMENTATION_REPORTS/evidence/phase7` | Complete |
| P7-9 | Regression tests | 37 Python + 26 JavaScript passed | `.cache/pytest_run.txt`, frontend test output | Complete |
| P7-10 | Academic documentation | Audit, matrix, demo, startup guide | This file and linked docs | Complete |
| P7-11 | R2 compliance fix | `select_questions()` includes `ts-01` in all modes; 3 regression tests added; real Ollama quick-mode verification completed | `FINAL_R2_COMPLIANCE_FIX.md`, `.cache/verify_out.txt` | Complete |

## Known limitations

- No authentication or RBAC.
- AI scores are preparation feedback, not validated psychometric measurements.
- CV degree extraction needs hardening for the synthetic CV (mandatory degree classified `not_demonstrated` while feedback states it is satisfied).
- PDF uses standard Type1 fonts and no embedded images.
- Phase 5 speech/voice acceptance is pending and outside Phase 7 scope.
