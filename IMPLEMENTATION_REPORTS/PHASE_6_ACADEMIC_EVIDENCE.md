# Academic Evidence Report — AI Admission Simulator (Phase 6)

## Context

Independent admissions interview simulation for the Master’s Degree in Artificial Intelligence at Instituto Tecnológico El Llano Aguascalientes. All evidence comes from the running local application with synthetic candidate data.

## Requirement 1: Admissions interview question bank
Description: A local question bank with 30 base questions across admission categories.
Implemented feature: `QuestionBankService` seeds and selects 5/10/15 questions by mode.
Evidence: `IMPLEMENTATION_REPORTS/evidence/phase6/ui_questions.png`.
Observed result: Question bank page lists 30 questions and category filtering works.

## Requirement 2: Mandatory stress-management question
Description: Every interview includes a stress/time-management/rest question.
Implemented feature: `time_management_stress` question is forced in all modes.
Evidence: `ui_interview.png`, generated PDF stress section.
Observed result: Interview includes the mandatory question and evaluation captures stress management.

## Requirement 3: Evaluation of professional, confident, natural communication
Description: Responses are evaluated for communication quality.
Implemented feature: Answer evaluator criteria include professionalism, confidence, naturalness.
Evidence: `ui_results.png`, `reporte_ejemplo.pdf`.
Observed result: Evaluations display criterion-level scores and feedback.

## Requirement 4: PDF CV upload and analysis
Description: Candidate CV uploaded as PDF and analyzed against requested profile.
Implemented feature: CV upload and analysis endpoints/services; CV findings included in interview report when completed analysis exists.
Evidence: `ui_profile.png`, report CV section.
Observed result: Profile page and report show candidate data; CV section appears only when a completed analysis exists.

## Requirement 5: Realistic AI-driven interview and contextual follow-up
Description: AI generates interview flow and follow-up questions from answers.
Implemented feature: Interview service + follow-up generation endpoint.
Evidence: `ui_interview.png`.
Observed result: Active interview displays current question, progress, history, and evaluation.

## Requirement 6: Detailed evaluation and improvement feedback
Description: Candidate receives detailed feedback and improvement recommendations.
Implemented feature: Per-answer evaluations and PDF report with scores, criteria, strengths, weaknesses, recommendations, improved answer, tips.
Evidence: `ui_results.png`, `reporte_ejemplo.pdf`.
Observed result: Results page and PDF contain detailed feedback.

## Requirement 7: Personalized interview closing statements
Description: Interview ends with personalized closing message.
Implemented feature: Report closing message based on candidate name and performance band.
Evidence: `reporte_ejemplo.pdf`.
Observed result: PDF includes a personalized closing message and academic disclaimer.

## Screenshots
- `ui_dashboard.png`: Dashboard.
- `ui_profile.png`: Candidate profile.
- `ui_questions.png`: Question bank.
- `ui_interview.png`: Active interview.
- `ui_results.png`: Results and PDF download.
- `ui_system.png`: System status.
- `pdf_page1.png`: Rendered PDF page.
- `reporte_ejemplo.pdf`: Generated candidate PDF.

## Gaps
- CV screenshot of an actual uploaded/analyzed CV is not included because the demo used profile data only; CV analysis requires a separate upload/analysis flow.
- No real Ollama run was performed for this evidence set; mock provider was used for deterministic synthetic data.
