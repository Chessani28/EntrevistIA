# Phase 0 ? Repository Audit

**Proyecto auditado:** copia local de ITGlasses en `D:\SistemasMaestria\ITGlasses-master`
**Nuevo proyecto objetivo:** AI Admission Simulator (Maestr?a en Inteligencia Artificial ? IT El Llano Aguascalientes)
**Fecha de auditor?a:** 2026-10-24
**Modo:** solo inspecci?n y documentaci?n (sin cambios de negocio)

---

## 1. Alcance y seguridad de aislamiento

- El directorio de trabajo es `D:\SistemasMaestria\ITGlasses-master`. No se accedi? ni modific? ning?n archivo fuera de esa ruta.
- **No existe repositorio Git** en esta copia: `git status` devuelve `fatal: not a git repository`. Por tanto **no hay remote configurado** y es imposible empujar accidentalmente a `https://github.com/Chessani28/ITGlasses`.
- No existen los directorios `storage/`, `documents/` ni `.venv/` en la copia original (solo c?digo fuente, frontend, docs, scripts y reportes). Se cre? un `.venv` local con `uv` ?nicamente para verificar importaciones (ignorado por `.gitignore`).
- No se encontraron claves API, contrase?as, tokens ni secretos en archivos fuente (b?squeda sobre `*.py, *.toml, *.ps1, *.md, *.js, *.html, *.css`).
- No se detectaron documentos empresariales, manuales internos ni datos personales en la copia. El ?nico contenido IT-espec?fico son referencias en c?digo/prompts y en documentaci?n.
- La copia es independiente del original; las rutas duras del original (`D:\ITGlasses`) aparecen ?nicamente en scripts y pruebas de smoke, y deber?n reescribirse en Phase 1.

**Conclusi?n de seguridad:** la copia puede transformarse de forma segura sin riesgo de modificar el repositorio original. El ?nico recurso compartido previsto es el servicio Ollama local, que actualmente **no est? instalado/ejecut?ndose** en esta m?quina.

---

## 2. Estructura del proyecto encontrada

```
ITGlasses-master/
??? backend/
?   ??? app/
?   ?   ??? api/            (routes.py, schemas.py)
?   ?   ??? core/           (config.py)
?   ?   ??? frontend.py     (montaje de assets)
?   ?   ??? main.py         (f?brica create_app)
?   ?   ??? run.py          (launcher uvicorn)
?   ?   ??? providers/      (base.py, mock.py, ollama.py)
?   ?   ??? knowledge/      (RAG: models, routes, service, store, embeddings, extract, grounding, retrieval, social)
?   ?   ??? voice/          (normalize, routes, service, worker)
?   ??? __init__.py
??? frontend/               (index.html, app.js, core.mjs, styles.css, favicon.svg, m?dulos de voz)
??? tests/                  (frontend.test.mjs, voice.test.mjs, smoke_*.py, verify_knowledge_acceptance.py, fixtures)
??? docs/                   (interface.md, knowledge.md, voice-assistant.md, progress.md, mediciones, Modelfile.qwen3)
??? scripts/                (start-backend.ps1, start-ollama.ps1, check-resources.ps1)
??? IMPLEMENTATION_REPORTS/ (reportes de fases ITGlasses)
??? config.toml
??? requirements*.txt
??? pytest.ini
??? README.md
```

Conteo aproximado: 54 archivos de c?digo/documentaci?n (sin entorno, cach?s ni storage).

---

## 3. Arquitectura reutilizable (estable y gen?rica)

| Componente | Ubicaci?n | Reutilizaci?n prevista |
|---|---|---|
| F?brica de app FastAPI + middleware de errores | `backend/app/main.py` | Reusar estructura, cambiar t?tulos/rutas |
| Configuraci?n tipada (TOML + env) | `backend/app/core/config.py` | Reusar patr?n; renombrar `app_name`, env var y rutas |
| Protocolo de proveedor LLM | `backend/app/providers/base.py` | Reusar tal cual (errores tipados) |
| Adaptador Ollama (HTTP local, sin redirects, sin descarga) | `backend/app/providers/ollama.py` | Reusar transporte; **eliminar prompt ITGlasses** |
| MockLLM para pruebas aisladas | `backend/app/providers/mock.py` | Reusar para tests |
| Servicio de archivos est?ticos + CSP | `backend/app/frontend.py` | Reusar |
| Launcher uvicorn | `backend/run.py` | Reusar (ajustar rutas de cach? si se desea) |
| M?dulo de voz (Vosk/Piper) | `backend/app/voice/*` | Reusar como **opcional** (no prioridad) |
| Extracci?n de texto de PDF/DOCX | `backend/app/knowledge/extract.py` | Reusar patr?n para **CV en PDF** |
| Frontend sin build (HTML/CSS/JS) | `frontend/*` | Reusar patr?n; reemplazar branding/p?ginas |
| Pruebas de contrato frontend | `tests/frontend.test.mjs`, `tests/voice.test.mjs` | Adaptar a nuevas rutas |

---

## 4. Componentes ITGlasses-espec?ficos a eliminar o reemplazar

1. **Prompt de sistema ITGlasses** en `backend/app/providers/ollama.py` (bloque `messages` con "You are ITGlasses, a local IT support assistant..."). Debe sustituirse por prompts de admisi?n.
2. **M?dulo RAG / Knowledge** (`backend/app/knowledge/*`): dise?ado para manuales/procedimientos empresariales (FTS5, embeddings, autorizaci?n de documentos). No se reutilizar? como base de conocimiento IT. Sus patrones de SQLite/validaci?n pueden inspirar persistencia, pero la l?gica de recuperaci?n documental no aplica al simulador de admisi?n (salvo carga de CV).
3. **Branding y UI** (`frontend/index.html`, `styles.css`, `app.js`): textos "ITGlasses", "Conversaciones", "Documentos", wake phrase "Oye, ITGlasses".
4. **Configuraci?n de identidad**: `app_name = "ITGlasses"`, variable de entorno `ITGLASSES_PROVIDER`, rutas `D:\ITGlasses` en scripts y smoke tests.
5. **Wake phrase experimental** "Oye, ITGlasses" en voz.
6. **Documentaci?n** (`docs/*`, `README.md`, `IMPLEMENTATION_REPORTS/*`) describe el producto ITGlasses; se reemplazar? para el nuevo producto.

---

## 5. Dependencias y entorno

- **Python:** disponible v?a `uv` (CPython 3.14.7). Se cre? un `.venv` local con `uv` para verificaci?n de importaci?n (ignorado por `.gitignore`). No exist?a `.venv` en la copia.
- **Node.js:** v24.21.0 disponible; pruebas JS ejecutan correctamente.
- **Dependencias Python** (`requirements.txt`): FastAPI, Uvicorn, httpx, pypdf, python-docx, python-multipart, numpy. `pypdf` es directamente ?til para extracci?n de CV en PDF.
- **Dependencias opcionales de voz**: vosk, piper-tts (no instaladas; no prioridad).
- **Ollama:** NO instalado ni en ejecuci?n. No se encontr? `ollama.exe` ni directorio `.ollama`. El endpoint `http://127.0.0.1:11434/api/tags` no responde.
- **Modelos:** ninguno disponible localmente. El `config.toml` referencia `qwen3:4b-instruct-2507-q4_K_M`, pero no se puede verificar su presencia hasta instalar/ejecutar Ollama.

**Nota importante:** el desarrollo del motor de IA real requiere instalar Ollama y al menos un modelo de instrucciones compatible. Hasta entonces, el desarrollo podr? avanzar con `MockLLM` **solo para pruebas aisladas**, pero la entrega final debe usar respuestas reales de Ollama.

---

## 6. Verificaci?n de conectividad Ollama

| Prueba | Resultado |
|---|---|
| `GET http://127.0.0.1:11434/api/tags` | No alcanzable (sin servidor) |
| B?squeda de `ollama.exe` en ubicaciones comunes | No encontrado |
| Directorio `%USERPROFILE%\.ollama` | No existe |
| Proceso `ollama` en ejecuci?n | No |

**Acci?n requerida (futura, con aprobaci?n):** instalar Ollama en `D:\` o usar un runtime ya verificado, configurar `OLLAMA_MODELS` en disco D, y descargar ?nicamente un modelo de instrucciones general compatible (sin modificar modelos existentes). No se descarg? nada en esta fase.

---

## 7. Hallazgos de privacidad y seguridad

- No hay credenciales en el c?digo.
- El backend original solo enlaza a `127.0.0.1` (loopback), lo cual es adecuado para datos personales.
- El m?dulo de voz y documentos validan origen (`Origin`) para operaciones de escritura.
- **Riesgos a mitigar en el nuevo producto:**
  - Los CV en PDF contienen datos personales; no deben servirse por rutas est?ticas p?blicas.
  - Debe existir opci?n de eliminar datos del candidato y CVs subidos.
  - La base de datos SQLite debe ser independiente y no reutilizar la de ITGlasses.
  - No se deben registrar contenidos de CV en logs ni respuestas de error.
  - El modelo no debe recibir instrucciones para inventar grados/certificaciones/experiencia.

---

## 8. Arquitectura propuesta para AI Admission Simulator

```
backend/
  app/
    core/          config.py (renombrado), db.py (SQLite), security helpers
    providers/     base.py, mock.py, ollama.py (prompt gen?rico de admisi?n)
    services/      InterviewService, QuestionBankService, AnswerEvaluationService,
                   CVAnalysisService, ReportService, SessionService, ClosingStatementService
    api/           routes.py, schemas.py (endpoints de admisi?n)
    models/        SQLite models para candidate, session, answer, evaluation, cv_analysis, report
    prompts/       system prompts separados por rol
    utils/         pdf_report.py, cv_pdf_extract.py
frontend/          dashboard, perfil, CV, entrevista, coach, banco, resultados, reporte PDF
tests/             unit + integration + smoke con Ollama
```

Servicios sugeridos (seg?n el enunciado):

- `OllamaProvider` (adaptador existente, reutilizado)
- `InterviewService` (orquestaci?n de entrevista)
- `QuestionBankService` (?30 preguntas por categor?a, modos 5/10/15)
- `AnswerEvaluationService` (r?brica 0?100 con criterios documentados)
- `CVAnalysisService` (extracci?n PDF + comparaci?n con perfil acad?mico exacto)
- `ReportService` (generaci?n de PDF profesional)
- `SessionService` (persistencia SQLite independiente)

Prompts separados:

1. Comit? de admisiones (simulaci?n)
2. Evaluador de CV
3. Coach de comunicaci?n
4. Evaluador de desempe?o de entrevista
5. Generador de declaraciones de cierre

Salidas estructuradas validadas con JSON schema antes de usarse.

---

## 9. Plan por fases (resumen)

- **Phase 0 ? Auditor?a** (este reporte): completo a nivel de inspecci?n.
- **Phase 1 ? Fundaci?n independiente:** renombrar/rebranding, config, DB SQLite, eliminar l?gica IT, rutas duras, env var, branding; verificar aislamiento.
- **Phase 2 ? Motor de admisi?n con IA:** prompts, banco de preguntas, sesiones, integraci?n Ollama real, context preservation.
- **Phase 3 ? An?lisis de CV:** carga PDF, extracci?n, matching con perfil acad?mico exacto, recomendaciones.
- **Phase 4 ? Evaluaci?n de respuestas:** tono/comunicaci?n, estr?s, r?brica, puntuaciones.
- **Phase 5 ? Interfaz:** dashboard y p?ginas en espa?ol, dise?o navy/cian/violeta.
- **Phase 6 ? Reportes:** resultados, declaraciones de cierre, exportaci?n PDF.
- **Phase 7 ? Pruebas y demostraci?n acad?mica:** tests end-to-end reales, checklist de evidencia, guion de video.

---

## 10. Criterios de aceptaci?n de Phase 1 (para aprobaci?n)

1. El proyecto se identifica como "AI Admission Simulator" (nombre, README, config, UI).
2. No existe dependencia del repositorio original (sin remote, sin rutas `D:\ITGlasses`).
3. Base de datos SQLite independiente creada en la nueva ruta del proyecto; no se conecta a la de ITGlasses.
4. Se eliminan todos los prompts y l?gica de soporte IT.
5. El proveedor Ollama usa un prompt gen?rico de admisi?n (o mock solo para tests).
6. La carga de CV PDF funciona y no expone archivos por rutas p?blicas.
7. Pruebas automatizadas m?nimas para config, salud y disponibilidad del proveedor pasan.
8. Se documenta cualquier dato confidencial encontrado (ninguno en esta copia).

---

## 11. Verificaci?n realizada en Phase 0

| Verificaci?n | Resultado |
|---|---|
| Estructura del proyecto | Completada |
| Componentes reutilizables identificados | Completado |
| Componentes IT-espec?ficos identificados | Completado |
| Configuraci?n y dependencias | Completado |
| Repositorio Git / remote | No es repo Git; sin remote |
| Ollama alcanzable | No |
| Modelos instalados | Ninguno detectado |
| Secretos/datos confidenciales | No encontrados |
| Compilaci?n Python (`compileall`) | OK (sin errores) |
| Pruebas frontend (Node) | 11/11 OK |
| Pruebas voz (Node) | 15/15 OK |
| Pruebas Python (pytest) | 0 recolectadas (no hay `test_*.py` en la copia) |

**No se inventaron resultados exitosos.** Los smoke tests originales (`smoke_*.py`) requieren el entorno original `D:\ITGlasses` y no se ejecutaron.

---

## 12. Detenci?n para aprobaci?n

Phase 0 se considera completada a nivel de auditor?a y documentaci?n. **No se ha modificado la l?gica de negocio ni se ha implementado ninguna fase posterior.**

Se requiere aprobaci?n expl?cita antes de iniciar Phase 1 (Fundaci?n independiente). En particular, se solicita confirmar:

1. El nombre final del proyecto y el directorio de trabajo (`D:\SistemasMaestria\ITGlasses-master` o uno nuevo).
2. Si se instalar?/ejecutar? Ollama (y con qu? modelo) para las fases posteriores.
3. Si se reutilizar? el m?dulo de voz opcional o se dejar? fuera del alcance inicial.

**Fin del reporte Phase 0.**
