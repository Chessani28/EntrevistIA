# Guía de demostración — EntrevistIA

Documento de preparación para la demostración universitaria (YouTube) del sistema EntrevistIA. Prioriza un flujo confiable y reproducible en modo local.

## 1. Requisitos previos

- Windows 10/11.
- Python 3.13 con entorno virtual creado en `.venv`.
- Dependencias instaladas: `pip install -r requirements.txt` y `pip install -r requirements-dev.txt` para pruebas.
- Ollama instalado localmente con el modelo `qwen3:4b-instruct-2507-q4_K_M` disponible en `storage/models` (o configurado en `config.toml`).
- Al menos 3 GB de RAM libre y 3 GB de VRAM disponibles para evitar degradación por swapping.
- Navegador moderno (Chrome/Edge) para la interfaz web.

## 2. Arranque

### Modo mock (sin Ollama, recomendado para ensayo rápido)

```powershell
.\scripts\start-backend.ps1 -Provider mock
```

### Modo real (con Ollama, para la demo final)

```powershell
.\scripts\start-backend.ps1 -Provider ollama
```

Arranque directo equivalente:

```powershell
.\.venv\Scripts\python.exe -m backend.run
```

Verificar que el backend está listo:

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/status
```

La respuesta de `/api/v1/status` debe incluir `"provider": "ollama"`, `"mock": false` y el modelo configurado.

Abrir la interfaz web en: `http://127.0.0.1:8000/`.

## 3. Secuencia de demostración

1. Abrir la aplicación en el navegador.
2. Crear un candidato sintético (datos en la sección 4).
3. Iniciar una entrevista en modo **Rápida** (5 preguntas).
4. Responder las 5 preguntas, incluyendo la pregunta obligatoria de estrés `ts-01`.
5. Completar la entrevista.
6. Ejecutar la evaluación de cada respuesta.
7. Revisar puntuaciones, criterios, fortalezas, áreas de mejora y retroalimentación.
8. Descargar el reporte PDF de la sesión.
9. Abrir el PDF y verificar datos del candidato, preguntas, respuestas, puntuaciones y retroalimentación.

## 4. Candidato sintético

- Nombre: `Demo Candidate`
- Correo: `demo@example.com`
- Formación académica: `Ingeniería en Sistemas`
- Experiencia profesional: `2 años en desarrollo de software`
- Programa objetivo: `Maestría en Inteligencia Artificial`

## 5. Respuestas de ejemplo

### Respuesta fuerte (pregunta de formación académica)

> Mi formación en Ingeniería en Sistemas me dio bases sólidas en programación, estructuras de datos y bases de datos. Durante mi tesis desarrollé un modelo de clasificación con scikit-learn para predecir deserción estudiantil, alcanzando 87% de precisión en validación cruzada. Esto me motivó a profundizar en machine learning y ahora busco la maestría para especializarme en IA aplicada a educación.

### Respuesta débil

> Estudie sistemas y me gusta la tecnología. Quiero la maestría porque es importante. No tengo mucha experiencia pero aprendo rápido.

### Respuesta irrelevante (pregunta de formación académica)

> Me gusta cocinar y viajar. El clima en mi ciudad es agradable. Creo que la maestría es una buena oportunidad para conocer gente nueva.

### Respuesta de estrés (`ts-01`)

> Planifico mi tiempo con un calendario semanal, priorizo las tareas académicas urgentes y mantengo bloques de descanso. Si la carga aumenta, delego actividades secundarias y ajusto el plan con mi familia para mantener el balance trabajo-estudio.

## 6. Resultados esperados

- La entrevista rápida genera **5 preguntas**, incluyendo `ts-01`.
- Cada respuesta evaluada devuelve un `overall_score` entre 0 y 100.
- La respuesta fuerte debe obtener una puntuación **mayor** que la débil e irrelevante.
- La respuesta irrelevante debe obtener una puntuación baja en `relevance` y `technical_accuracy`.
- El reporte PDF debe contener: datos del candidato, fecha, modo, preguntas, respuestas, puntuaciones, criterios, fortalezas, áreas de mejora y retroalimentación.
- El PDF debe ser válido y abrirse sin errores (verificado con `pypdf`).

## 7. Limitaciones conocidas

- La calidad de la evaluación depende del modelo local configurado (`qwen3:4b-instruct-2507-q4_K_M`).
- La inferencia en CPU puede tardar entre 30 y 120 segundos por evaluación.
- El asistente de voz es experimental y está deshabilitado por defecto.
- No hay autenticación multiusuario ni despliegue productivo.
- Las puntuaciones son retroalimentación simulada, no una decisión oficial de admisión.
- El análisis de CV depende de la calidad del texto extraíble del PDF.
- No se incluyen modelos, runtimes ni datos personales en el repositorio.

## 8. Solución de problemas

- **El backend no responde**: verificar que el proceso esté activo y que el puerto 8000 esté libre.
- **`model_unavailable` (503)**: Ollama no está en ejecución o el modelo no está instalado. Iniciar Ollama con `OLLAMA_MODELS` apuntando a `storage/models` y verificar con `curl http://127.0.0.1:11434/api/tags`.
- **Evaluaciones lentas**: cerrar aplicaciones pesadas para liberar RAM/VRAM; el modelo requiere ~2.5 GB.
- **Error de JSON malformado**: el sistema extrae automáticamente el primer objeto JSON válido; si persiste, reintentar la evaluación.
- **PDF no se genera**: verificar que la sesión esté completada y que existan evaluaciones.
- **Pruebas fallan por base de datos**: eliminar `storage/admission.db` y reiniciar.

## 9. Validación final recomendada

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test tests\*.mjs
node --check frontend\app.js
```

Resultado esperado: 37 pruebas Python y 26 pruebas JavaScript pasando.
