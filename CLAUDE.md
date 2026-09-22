# CLAUDE.md — asistente-productividad

Contexto compacto del proyecto. Leer esto antes de tocar código; evita re-explorar archivos.

## Qué es

Demo full-stack: el usuario escribe una solicitud en lenguaje natural y un LLM decide **qué
función Python llamar** para estructurarla como tarea. El LLM no genera los datos de la tarea:
sólo extrae argumentos y elige la herramienta. Python ejecuta la lógica.

Sin base de datos. Sin framework de frontend. Todo en free tier (Google AI Studio + Render + Vercel).

## Stack y despliegue

| Parte | Tecnología | Destino |
|---|---|---|
| Backend | FastAPI + `google-genai`, escucha en `$PORT` (fallback **7860**) | Render free tier, Root Directory `backend` |
| Frontend | HTML/CSS/JS puro | Vercel (estático, Root Directory = `frontend`) |
| Modelo | `gemini-3.8-flash` (override con env `GEMINI_MODEL`) | Google AI Studio |
| Secreto | `GEMINI_API_KEY` (env var en Render) | nunca en el repo |

## Mapa de archivos

```
asistente-productividad/
├── backend/
│   ├── funciones.py     crear_tarea(), calcular_prioridad()  ← lógica pura, sin IA
│   ├── llm_service.py   TOOLS, SYSTEM_PROMPT, procesar_solicitud()  ← loop de tool calling
│   ├── josephgonzales.py  FastAPI: CORS *, GET /, POST /procesar-solicitud  ← el entrypoint
│   ├── requirements.txt fastapi, uvicorn[standard], google-genai, pydantic (versiones fijadas)
│   ├── Dockerfile       usuario sin privilegios, CMD uvicorn en ${PORT:-7860}
│   └── .gitignore
├── frontend/
│   ├── index.html       textarea#solicitud, button#btn-procesar, #estado, #resultado
│   ├── style.css        variables CSS, tarjetas, etiquetas .alta/.normal/.baja
│   └── script.js        BACKEND_URL (línea 3), procesar(), pintar(), tarjetaTarea()
└── README.md            guía de despliegue (Render + Vercel) + 3 casos de prueba
```

## Contratos clave (no romper sin actualizar ambos lados)

**POST /procesar-solicitud** — body `{"solicitud": "texto"}`
- `400` si `solicitud` está vacía; `500` si falla Gemini.
- Respuesta A: `{"tipo":"respuesta_texto","mensaje":str}` → faltan datos.
- Respuesta B: `{"tipo":"tarea_generada","tareas_creadas":[tarea],"calculos":[{"argumentos":{...},"prioridad":str}]}`

**tarea** = `titulo, fecha, hora, participantes[], prioridad, estado="pendiente", creada_en (ISO)`

`script.js` consume exactamente esas dos formas en `pintar()`. Si cambia el contrato, cambiar ahí.

## Reglas de diseño que el código asume

1. **No inventar datos.** Si falta título, fecha, hora o participantes → respuesta en texto, sin tool call.
   Está en `SYSTEM_PROMPT` (regla 2) de `llm_service.py`.
2. **Composición.** `calcular_prioridad` → `crear_tarea` en iteraciones sucesivas del loop
   (`MAX_ITERACIONES = 4`). El resultado de cada función se reinyecta como paso `function_result`.
3. **Prioridad explícita gana.** Si el usuario dice "prioridad alta", se usa directamente (regla 3 del prompt).
4. **Fechas sin normalizar.** Se guarda "viernes" tal cual; no hay parseo a calendario, por diseño.
5. **`get_cliente()` es perezoso**: la app arranca aunque falte `GEMINI_API_KEY`; falla al primer request.
6. **CORS abierto** a propósito, con comentario de restringirlo en producción.
7. **Escapado en frontend**: todo valor del backend pasa por `escapar()` antes del `innerHTML`.

## API de Gemini: lo que hay que recordar

Se usa la **Interactions API** (`client.interactions.create`), GA desde junio 2026 y la vía
recomendada. La antigua `client.models.generate_content` es legacy. Diferencias frente a
la API estilo OpenAI que se usaba con Groq:

| | OpenAI/Groq | Gemini Interactions |
|---|---|---|
| Declarar tool | `{"type":"function","function":{"name",...}}` | `{"type":"function","name",...}` ← **plano** |
| System prompt | mensaje `role:"system"` | parámetro top-level `system_instruction` |
| Historial | lista de `messages` | lista de `input` con `store=False` + `interaction.steps` |
| Tool call | `message.tool_calls[].function.arguments` | pasos con `step.type=="function_call"`, `.name`, `.arguments`, `.id` |
| Resultado | `{"role":"tool","tool_call_id",...}` | `{"type":"function_result","name","call_id","result":[{"type":"text","text"}]}` |
| Texto final | `message.content` | `interaction.output_text` |

- `store=False` es deliberado: sin estado en servidores de Google, el backend lleva el historial
  (igual que antes). Por eso **no** se usa `previous_interaction_id`.
- Los pasos son objetos pydantic → `_a_dict()` los pasa por `model_dump(exclude_none=True)`
  antes de meterlos en el historial.
- `_argumentos()` tolera que `arguments` llegue como dict o como string JSON.
- Free tier ajustado. Si hay `429 RESOURCE_EXHAUSTED`: `GEMINI_MODEL=gemini-3.5-flash-lite`.

## Escala de calcular_prioridad

`bajo=1, medio=2, alto=3`; suma `>=5 → alta`, `<=3 → baja`, resto `normal`. Valores desconocidos → 2.

## Casos de prueba (README §5)

1. Informe + viernes 16:00 + María y José → `tarea_generada`, prioridad `normal`.
2. Reunión + lunes 09:30 + Carlos, Elena, Pedro + "prioridad alta" → `tarea_generada`, prioridad `alta`.
3. "documentación del sistema para el próximo miércoles" → `respuesta_texto` (falta hora y participantes).

## Hosting: por qué Render

Hugging Face Spaces **dejó de servir**: desde julio 2026 los Spaces Docker y Gradio exigen PRO
de pago; los Static Spaces son gratis pero sólo sirven HTML. Render mantiene free tier sin
tarjeta (750 h/mes, duerme a los 15 min, despierta en ~1 min).

- Render inyecta `$PORT`; por eso el `CMD` del Dockerfile usa forma shell (`${PORT:-7860}`)
  y `josephgonzales.py` lee `os.environ.get("PORT", 7860)`. **No hardcodear 7860.**
- Root Directory `backend` en la config de Render: no hay que aplanar ni mover archivos.
- El README ya no lleva frontmatter YAML (era sólo para HF).

## Antes de desplegar

- [ ] `GEMINI_API_KEY` como Environment Variable en Render (no en el código).
- [ ] `BACKEND_URL` en `script.js` apuntando a la URL de Render, **sin barra final**.
- [ ] Root Directory `backend` y Instance Type **Free** en Render.

## Convenciones al editar

- Código, comentarios, prompts y UI **en español**.
- Nada de dependencias nuevas en el frontend; nada de DB en el backend.
- Al añadir una función de negocio: implementarla en `funciones.py`, declararla en `TOOLS`,
  registrarla en `FUNCIONES_DISPONIBLES` y decidir si acumula en `tareas_creadas` o `calculos`.
