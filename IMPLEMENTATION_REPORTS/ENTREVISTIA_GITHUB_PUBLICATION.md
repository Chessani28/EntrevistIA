# EntrevistIA GitHub Publication Report

## Repository

- URL: https://github.com/Chessani28/EntrevistIA
- Branch: main
- Commit hash: 2b4dcf908e707a4effccc4ed5eb841895460288a
- Push type: normal, non-forced

## Files included

- FastAPI backend source code
- Frontend HTML, CSS and JavaScript
- Interview engine, question bank, CV analysis, answer evaluation and report generation
- Ollama integration and mock provider
- SQLite schema and initialization logic
- Automated Python and JavaScript tests
- Dependency manifests
- Safe configuration template (`config.toml`, `.env.example`)
- Windows startup scripts
- Professional Spanish README

Total committed files: 69.

## Files excluded

- `.venv/`, Python caches and pytest caches
- `.cache/`, logs and temporary outputs
- `storage/`, SQLite databases, CV uploads and generated reports
- Ollama runtime binaries and model weights
- Uploaded documents and candidate personal data
- Internal documentation, implementation reports and academic delivery artifacts
- `docs/`, `IMPLEMENTATION_REPORTS/`, `DELIVERY/`, `DELIVERY_ACADEMIC_PACKAGE.zip`

## Security and privacy audit

- No API keys, tokens, passwords or connection strings were found in the published source.
- No candidate CVs, private SQLite records or confidential institutional data were published.
- No Ollama model weights or runtime binaries were published.
- Hardcoded `D:/SistemasMaestria` paths were removed from smoke scripts.
- Inherited ITGlasses references were removed from user-facing source and branding was updated to EntrevistIA.
- Published remote tree was checked for excluded runtime, database, PDF and ITGlasses references; none were found.

## Test results

- Python test suite: 37 passed, 1 warning.
- JavaScript test suite: 26 passed.
- JavaScript syntax checks: `frontend/voice-core.mjs`, `frontend/microphone.mjs` and `frontend/app.js` passed.
- Import/startup check: `from backend.app.main import create_app` succeeded and reported title `EntrevistIA`.
- No models or software were downloaded during publication.

## Reproducibility verification

- Dependencies are documented in `requirements.txt`, `requirements-dev.txt`, `requirements-lock.txt` and `requirements-voice.txt`.
- Configuration is safe and uses local-only Ollama settings.
- The database initializes automatically from scratch through `init_db()`.
- No dependency on `D:\SistemasMaestria` or the original ITGlasses installation remains in published source.
- Startup commands use project-relative paths.

## Push result

- Remote branch `main` exists.
- Local commit hash matches remote commit hash: `2b4dcf908e707a4effccc4ed5eb841895460288a`.
- Publication completed successfully.

## Remaining limitations

- Ollama and the configured model must be installed manually by the user.
- Voice support remains experimental and is disabled by default.
- The application is intended for local academic simulation, not production deployment.
- Generated runtime data and reports remain local and are intentionally excluded from version control.
