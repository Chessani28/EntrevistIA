# Demo Script — AI Admission Simulator (Phase 7)

## 1. Objective

Demonstrate the complete admissions simulation flow with real local AI, persistent data,
detailed evaluations, PDF reporting and session restoration.

## 2. Preparation

1. Start Ollama and backend using `docs/startup-guide.md`.
2. Open `http://127.0.0.1:8000/`.
3. Verify `/api/v1/system/status` returns `ready` with `mock=false`.

## 3. Candidate and CV

1. Create candidate:
   - Name: `Ana Maria Torres (fictional)`
   - Email: `ana.torres@example.com`
2. Upload `IMPLEMENTATION_REPORTS/evidence/phase7/cv_synthetic.pdf`.
3. Run CV analysis and wait for status `completed`.
4. Observe extracted evidence: education, Python, SQL, databases, FastAPI, ML thesis.

## 4. Interview

1. Create a rapid interview session (5 questions).
2. Start the interview.
3. Answer the five base questions.
4. Answer each generated follow-up question.
5. Complete the interview.

Observed in Phase 7:
- 5 base questions
- 5 follow-up questions
- all submissions returned successfully

## 5. Review

1. Open interview history.
2. Confirm 10 answer records.
3. Open per-answer evaluations.
4. Observe scores, criteria explanations, strengths, weaknesses, recommendations,
   improved answers and practice tips.
5. Note the zero score for the irrelevant follow-up answer as correct
   insufficient-evidence handling.

## 6. Report

1. Download the PDF report.
2. Verify 23 pages and Spanish text.
3. Confirm candidate data, interview metadata, 10 answered questions, 10 evaluations,
   aggregate score 65.5/100, strengths, weaknesses, recommendations, CV findings,
   closing message and academic disclaimer.

## 7. Session restore

1. Reopen or restore the completed session.
2. Confirm status `completed`, position 5 of 5.
3. Confirm answers and evaluations remain available.

## 8. Automated evidence

Run the E2E script and tests:

```powershell
.\.venv\Scripts\python.exe .cache\e2e_phase7.py
.\.venv\Scripts\python.exe -m pytest -q
node --test tests\frontend.test.mjs tests\voice.test.mjs
```

## 9. Key talking points

- Real local Ollama, no cloud dependency.
- Persistent SQLite data.
- AI-generated preparation feedback, not an official admission decision.
- No admission probability is estimated.
- CV findings appear only when a completed analysis exists.
- Report is generated on demand and not stored as a redundant file.