# EntrevistIA Personalized Preparation

## Stage 2 — Personalized preparation

### Features implemented
- New SQLite tables: `preparation_plans` and `preparation_activities`.
- `PreparationService` gathers completed interview summaries, weak criteria, and the latest completed CV analysis.
- `POST /api/v1/preparation` generates a personalized plan with local Ollama.
- Plans include priority topics, activities, estimated minutes, weekly scheduling, milestones, and review sessions.
- Time allocation is normalized so total activity minutes do not exceed available study time.
- Activities can be marked completed/pending and progress persists.
- `GET /api/v1/preparation/candidate/{id}/interviews` compares completed interviews.
- Frontend navigation entry “Mi plan de preparación” added.
- Empty states are provided when no candidate or no completed interviews exist.

### Example personalized plan
- Candidate with a quick interview and a CV containing Python/SQL.
- Plan summary: simulated/personalized preparation based on interviews and CV.
- Priority topics: Algorithms (high), Databases (medium).
- Activities: algorithm practice (45 min), SQL JOIN review (30 min), structured answers (25 min).
- Milestone: complete week 1 activities, then a review interview.

### Progress tracking evidence
- `preparation_activities.status` persisted in SQLite.
- `GET /api/v1/preparation/{plan_id}` returns completed/total/percent.
- Manual smoke test verified 3 activities and progress 33.3% after one completion.

### Test results
- Python imports and startup passed.
- Preparation smoke test passed.
- JavaScript suite: 26 passed.

### Notes
- Plans are preparation feedback, not official admissions decisions.
- No paid APIs or external links are required; resources are named generically.