# Startup Guide — AI Admission Simulator

## Prerequisites

- Windows PowerShell.
- Project root: `D:\SistemasMaestria\AIAdmissionSimulator`
- Python virtual environment: `.venv`
- Ollama runtime and model: `storage\runtime\ollama-0.40.6\ollama.exe`, model `qwen3:4b-instruct-2507-q4_K_M`

## Start services

Open two PowerShell terminals.

Terminal 1 — Ollama:

```powershell
Set-Location D:\SistemasMaestria\AIAdmissionSimulator
.\scripts\start-ollama.ps1
```

Terminal 2 — backend with real Ollama:

```powershell
Set-Location D:\SistemasMaestria\AIAdmissionSimulator
.\scripts\start-backend.ps1 -Provider ollama
```

Open:

```text
http://127.0.0.1:8000/
```

For deterministic mock mode, use:

```powershell
.\scripts\start-backend.ps1 -Provider mock
```

## Verify health

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/system/status
```

Expected for real mode:

```json
{
  "status": "ready",
  "provider": "ollama",
  "model": "qwen3:4b-instruct-2507-q4_K_M",
  "mock": false
}
```

## Run Phase 7 E2E validation

With backend and Ollama running:

```powershell
Set-Location D:\SistemasMaestria\AIAdmissionSimulator
.\.venv\Scripts\python.exe .cache\e2e_phase7.py
```

Expected outputs:

- `.cache/e2e_out.txt`
- `.cache/e2e_results.json`
- `IMPLEMENTATION_REPORTS/evidence/phase7/history.json`
- `IMPLEMENTATION_REPORTS/evidence/phase7/evaluation_*.json`
- `IMPLEMENTATION_REPORTS/evidence/phase7/evaluations.json`
- `IMPLEMENTATION_REPORTS/evidence/phase7/reporte_e2e.pdf`

## Run regression tests

Python:

```powershell
Set-Location D:\SistemasMaestria\AIAdmissionSimulator
.\.venv\Scripts\python.exe -m pytest -q
```

JavaScript:

```powershell
Set-Location D:\SistemasMaestria\AIAdmissionSimulator
node --test tests\frontend.test.mjs tests\voice.test.mjs
```

## Troubleshooting

- If port 8000 is occupied, stop the existing backend before starting another one.
- If Ollama is not running, `/api/v1/system/status` will report unavailable.
- CV analysis and evaluation calls can take 30-90 seconds with the local model.
- Do not start duplicate backend or Ollama processes.
- If the E2E script is rerun, it creates a new candidate, session and artifacts.