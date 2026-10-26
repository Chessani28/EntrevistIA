# EntrevistIA

Simulador inteligente de entrevistas de admisión a posgrado.

EntrevistIA es una aplicación académica local para practicar entrevistas de admisión a programas de posgrado. Permite crear un perfil de candidato, responder preguntas por modo de entrevista, analizar un CV en PDF, evaluar respuestas con un modelo de lenguaje local y generar un reporte PDF de retroalimentación.

La aplicación funciona con FastAPI, una interfaz web sin compilación y Ollama para inferencia local. No utiliza servicios cloud ni claves API.

## Propósito académico

Este proyecto fue desarrollado como simulación académica independiente para apoyar la preparación de candidatos. No es una plataforma oficial de admisiones y no sustituye la evaluación real de un comité académico.

## Características principales

- Entrevistas simuladas en modos rápido, estándar y profundo.
- Banco de preguntas por categorías académicas y profesionales.
- Inclusión obligatoria de la pregunta de estrés `ts-01` en todos los modos.
- Análisis de CV en PDF con extracción de evidencia.
- Evaluación de respuestas con rúbrica y retroalimentación.
- Generación de reporte PDF por sesión.
- Interfaz web local servida por FastAPI.
- Asistente de voz experimental y deshabilitado por defecto.
- Pruebas automatizadas para backend y frontend.

## Stack tecnológico

- Python 3.13
- FastAPI y Uvicorn
- SQLite
- Ollama (inferencia local)
- HTML, CSS y JavaScript sin compilación
- pypdf, python-docx, numpy, httpx
- pytest y node:test

## Arquitectura

```text
backend/
  app/
    api/          Rutas HTTP y esquemas
    core/         Configuración y errores
    prompts/      Prompts de evaluación
    services/     Lógica de negocio
    providers/    Adaptadores LLM (mock y Ollama)
frontend/         Interfaz web estática
scripts/          Scripts de arranque para Windows
tests/            Pruebas Python y JavaScript
```

La 
base de datos SQLite se crea automáticamente en `storage/admission.db`. Las cargas de CV y los reportes se almacenan en `storage/` y se excluyen del repositorio.

## Requisitos previos

- Windows 10/11.
- Python 3.13.
- Node.js con `node` disponible para las pruebas de JavaScript.
- Ollama instalado localmente si se desea usar el proveedor `ollama`.
- Modelo local configurado en `config.toml`. Por defecto: `qwen3:4b-instruct-2507-q4_K_M`.

## Instalación en Windows

1. Clona el repositorio:

```powershell
 git clone https://github.com/Chessani28/EntrevistIA.git
 Set-Location EntrevistIA
```

2. Crea y activa un entorno virtual:

```powershell
 py -3.13 -m venv .venv
 .\.venv\Scripts\Activate.ps1
```

3. Instala dependencias:

```powershell
 .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para desarrollo y pruebas:

```powershell
 .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Variables de entorno y configuración

La aplicación lee `config.toml`. No se requieren API keys.

Variables opcionales para el proceso:

- `AIADMISSION_PROVIDER`: fuerza `mock` u `ollama` para el proceso actual.
- `OLLAMA_BASE_URL`: sobrescribe `ollama_url` de `config.toml`. Debe ser un origen HTTP de loopback IPv4 con puerto.

Ejemplo de `config.toml`:

```toml
provider = "ollama"
ollama_url = "http://127.0.0.1:11434"
model = "qwen3:4b-instruct-2507-q4_K_M"
context_length = 4096
max_output_tokens = 2048
thinking = false
timeout_seconds = 120.0
health_timeout_seconds = 5.0
keep_alive = "30s"
voice_enabled = false
database_path = "storage/admission.db"
```

## Instalación y uso de Ollama

1. Instala Ollama desde el sitio oficial.
2. Descarga el modelo configurado:

```powershell
 ollama pull qwen3:4b-instruct-2507-q4_K_M
```

3. Inicia Ollama:

```powershell
 .\scripts\start-ollama.ps1
```

El script usa el runtime incluido en `storage/runtime` si existe; de lo contrario usa `ollama` disponible en `PATH`.

4. Inicia el backend con Ollama:

```powershell
 .\scripts\start-backend.ps1 -Provider ollama
```

No se descargan modelos automáticamente. Si el modelo no está instalado, la aplicación devuelve un error explícito.

## Inicio rapido en Windows con Ollama real

1. Clona el repositorio:

```powershell
git clone https://github.com/Chessani28/EntrevistIA.git
Set-Location EntrevistIA
```

2. Crea y activa el entorno virtual:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instala dependencias:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

4. Descarga el modelo requerido (una sola vez):

```powershell
ollama pull qwen3:4b-instruct-2507-q4_K_M
```

5. Inicia Ollama:

```powershell
.\scripts\start-ollama.ps1
```

6. Selecciona el proveedor real de Ollama y arranca FastAPI:

```powershell
.\scripts\start-backend.ps1 -Provider ollama
```

7. Abre EntrevistIA en el navegador:

```text
http://127.0.0.1:8000/
```

8. Verifica que se usa Ollama y no MockLLM:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/system/status
```

La respuesta esperada debe incluir "provider": "ollama", "mock": false y "model": "qwen3:4b-instruct-2507-q4_K_M".


## Inicialización de la base de datos

La base de datos se inicializa automáticamente al arrancar la aplicación:

```powershell
 .\.venv\Scripts\python.exe -m backend.run
```

También puede inicializarse importando la aplicación:

```powershell
 .\.venv\Scripts\python.exe -c "from backend.app.main import create_app; app = create_app(); print('database initialized')"
```

No se incluyen bases de datos reales ni datos de candidatos en el repositorio.

## Arranque del backend

Modo mock, sin Ollama:

```powershell
 .\scripts\start-backend.ps1 -Provider mock
```

Modo Ollama:

```powershell
 .\scripts\start-backend.ps1 -Provider ollama
```

Arranque directo:

```powershell
 .\.venv\Scripts\python.exe -m backend.run
```

## Acceso a la interfaz web

Abre:

```text
 http://127.0.0.1:8000/
```

La interfaz permite registrar candidatos, iniciar entrevistas, responder preguntas, analizar CV, evaluar respuestas y generar reportes.

## Flujo de ejemplo de entrevista

1. Abre la aplicación en modo mock.
2. Crea o selecciona un candidato.
3. Inicia una sesión de entrevista en modo rápido.
4. Responde las preguntas mostradas, incluyendo `ts-01`.
5. Evalúa las respuestas desde la interfaz.
6. Genera el reporte PDF de la sesión.
7. Revisa la retroalimentación y las áreas de mejora.

## Pruebas automatizadas

Pruebas Python:

```powershell
 .\.venv\Scripts\python.exe -m pytest -q
```

Pruebas JavaScript:

```powershell
 node --test tests\*.mjs
```

Verificación de sintaxis JavaScript:

```powershell
 node --check frontend\voice-core.mjs
 node --check frontend\microphone.mjs
 node --check frontend\app.js
```

Verificación de importación:

```powershell
 .\.venv\Scripts\python.exe -c "from backend.app.main import create_app; app = create_app(); print(app.title)"
```

## Generación de reportes PDF

Los reportes se generan por sesión desde la API o la interfaz web. Los archivos generados se almacenan en `storage/` y no se publican en el repositorio.

Ejemplo de verificación local:

```powershell
 .\.venv\Scripts\python.exe -m pytest tests\test_phase6_pdf.py -q
```

## Limitaciones conocidas

- La calidad de la evaluación depende del modelo local configurado.
- El asistente de voz es experimental y está deshabilitado por defecto.
- No hay autenticación multiusuario ni despliegue productivo.
- Las puntuaciones son retroalimentación simulada, no una decisión oficial de admisión.
- El análisis de CV depende de la calidad del texto extraíble del PDF.
- No se incluyen modelos, runtimes ni datos personales en el repositorio.

- Ollama debe estar en ejecucion para usar inferencia real; si no esta disponible, las operaciones de entrevista pueden responder HTTP 503.
- La inferencia con Ollama en CPU puede ser lenta.
- La extraccion de grado/titulo desde CV tiene limitaciones conocidas.
- Los IDs historicos de entrevista no disponibles responden HTTP 404.
## Aviso académico

EntrevistIA es una simulación académica independiente. Las respuestas, puntuaciones y reportes generados por IA son herramientas de preparación y no constituyen una decisión oficial de admisión ni una medición psicométrica validada. El sistema no estima la probabilidad real de admisión del candidato.
