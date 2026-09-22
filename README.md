---
title: Asistente de Productividad
emoji: 🗂️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Asistente de Productividad

Convierte solicitudes escritas en lenguaje natural en **tareas estructuradas**, usando un LLM
(Gemini 3.8 Flash) que decide **cuándo** llamar a funciones Python reales — no genera
los datos por sí mismo.

- **Backend:** FastAPI + Gemini *function calling* → Hugging Face Spaces (Docker, puerto 7860)
- **Frontend:** HTML + CSS + JavaScript puro (sin frameworks) → Vercel
- **Sin base de datos.** Todo funciona en el *free tier* de Google AI Studio, Hugging Face y Vercel, sin tarjeta de crédito.

## Cómo funciona

1. El usuario escribe algo como *"Crear una tarea para entregar el informe el viernes a las 16:00 con María y José"*.
2. El backend envía el mensaje a Gemini junto con la definición de dos herramientas:
   - `crear_tarea(titulo, fecha, hora, participantes, prioridad)` → construye la tarea.
   - `calcular_prioridad(impacto, urgencia)` → devuelve `alta` | `normal` | `baja`.
3. El modelo decide qué función llamar y con qué argumentos. **Python ejecuta la función de verdad.**
4. El resultado se devuelve al modelo como un paso `function_result`, permitiendo composición
   (`calcular_prioridad` → `crear_tarea`) en hasta 4 iteraciones.
5. Si falta título, fecha, hora o participantes, el modelo **no inventa nada**: responde en texto pidiendo el dato.

### Respuestas de la API

```json
// Faltan datos
{ "tipo": "respuesta_texto", "mensaje": "Para crear la tarea necesito la hora y los participantes." }

// Tarea creada
{
  "tipo": "tarea_generada",
  "tareas_creadas": [{
    "titulo": "Entregar el informe de pruebas",
    "fecha": "viernes",
    "hora": "16:00",
    "participantes": ["María", "José"],
    "prioridad": "normal",
    "estado": "pendiente",
    "creada_en": "2026-09-21T16:04:11.120394"
  }],
  "calculos": []
}
```

## Endpoints

| Método | Ruta                  | Descripción |
|--------|-----------------------|-------------|
| GET    | `/`                   | Healthcheck |
| POST   | `/procesar-solicitud` | Body: `{"solicitud": "texto"}`. `400` si viene vacío, `500` si falla Gemini. |
| GET    | `/docs`               | Swagger UI automático de FastAPI |

## 1. Obtener una GEMINI_API_KEY gratis

1. Entra a <https://aistudio.google.com/apikey> e inicia sesión con tu cuenta de Google.
2. Pulsa **Create API key** (puedes dejar que cree un proyecto nuevo por ti).
3. **Copia la clave** (empieza por `AIza...`).
4. El *free tier* de AI Studio no pide tarjeta de crédito. Tiene cuota diaria limitada,
   suficiente para pruebas y demos.

> El free tier de Gemini es más ajustado que antes. Si ves errores `429 RESOURCE_EXHAUSTED`,
> añade la variable `GEMINI_MODEL=gemini-3.5-flash-lite` en el Space: es un modelo más ligero
> con límite diario más alto, y funciona igual con estas dos herramientas.

> Nunca subas la clave al repositorio. En local usa una variable de entorno; en Hugging Face usa un *Secret*.

## 2. Desplegar el backend en Hugging Face Spaces

1. Entra a <https://huggingface.co> y crea una cuenta.
2. **New Space** → nombre `asistente-productividad` → **SDK: Docker** → plantilla *Blank* → **Public** → *Create Space*.
3. En la pestaña **Files** → **Add file** → **Upload files**, sube el contenido de `backend/`:
   `main.py`, `funciones.py`, `llm_service.py`, `requirements.txt`, `Dockerfile`
   y además **este `README.md`** (Spaces necesita el bloque YAML del inicio, con `sdk: docker` y `app_port: 7860`).
4. Ve a **Settings** → **Variables and secrets** → **New secret**:
   - Name: `GEMINI_API_KEY`
   - Value: tu clave `AIza...`

   (Opcional) Añade una **variable** `GEMINI_MODEL` si quieres forzar otro modelo.
5. El Space se reconstruye solo. Cuando el estado sea **Running**, tu URL de API es:
   `https://<tu-usuario>-asistente-productividad.hf.space`
6. Verifica el healthcheck abriendo esa URL en el navegador: debe responder `{"estado":"ok",...}`.

> Alternativa por git: `git clone https://huggingface.co/spaces/<usuario>/asistente-productividad`, copia los archivos, `git add . && git commit -m "deploy" && git push`.

## 3. Desplegar el frontend en Vercel

1. Abre `frontend/script.js` y pega tu URL del Space en la primera línea (**sin barra final**):
   ```js
   const BACKEND_URL = "https://tu-usuario-asistente-productividad.hf.space";
   ```
2. Sube el proyecto a GitHub.
3. Entra a <https://vercel.com>, inicia sesión con GitHub → **Add New… → Project** → importa el repo.
4. Configura:
   - **Framework Preset:** `Other`
   - **Root Directory:** `frontend`
   - Build Command y Output Directory: **vacíos** (es sitio estático)
5. **Deploy**. Obtendrás una URL tipo `https://asistente-productividad.vercel.app`.

> Alternativa sin GitHub: `npm i -g vercel`, luego `cd frontend && vercel --prod`.

## 4. Probar en local (opcional)

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate    # Windows PowerShell
pip install -r requirements.txt
$env:GEMINI_API_KEY="AIza_tu_clave"               # Windows PowerShell
uvicorn main:app --reload --port 7860
```

Luego pon `const BACKEND_URL = "http://127.0.0.1:7860";` en `script.js` y abre `frontend/index.html`
en el navegador (o sirve la carpeta con `python -m http.server 5500`).

## 5. Casos de prueba

Pega cada texto en el textarea y pulsa **Procesar solicitud**.

### Caso 1 — Tarea completa sin prioridad explícita
> Crear una tarea para entregar el informe de pruebas el viernes a las 16:00. Participarán María y José.

**Esperado:** `tipo: "tarea_generada"` con una tarjeta — título *Entregar el informe de pruebas*,
fecha *viernes*, hora *16:00*, participantes *María, José*, prioridad *normal* (valor por defecto),
estado *pendiente*.

### Caso 2 — Reunión con prioridad explícita
> Programar una reunión de revisión de requisitos para el lunes a las 09:30 con Carlos, Elena y Pedro. La prioridad es alta.

**Esperado:** una tarjeta con los 3 participantes y prioridad **alta** tomada directamente del texto
(la regla 3 del system prompt evita recalcularla).

### Caso 3 — Datos faltantes
> Necesito preparar una actividad de documentación del sistema para el próximo miércoles.

**Esperado:** `tipo: "respuesta_texto"`. El asistente **no inventa** hora ni participantes: muestra el
bloque *"Faltan datos"* pidiendo la hora y quiénes participan.

### Probar la API directamente

```bash
curl -X POST https://tu-usuario-asistente-productividad.hf.space/procesar-solicitud \
  -H "Content-Type: application/json" \
  -d '{"solicitud":"Crear una tarea para entregar el informe el viernes a las 16:00 con María y José."}'
```

## Estructura

```
asistente-productividad/
├── backend/
│   ├── main.py            # FastAPI: CORS, healthcheck, POST /procesar-solicitud
│   ├── funciones.py       # Lógica de negocio pura (sin IA)
│   ├── llm_service.py     # Cliente Gemini, tools y loop de function calling
│   ├── requirements.txt
│   ├── Dockerfile         # python:3.11-slim, uvicorn en el puerto 7860
│   └── .gitignore
├── frontend/
│   ├── index.html         # Textarea + botón + zonas de estado y resultado
│   ├── style.css          # Diseño centrado, sin dependencias externas
│   └── script.js          # BACKEND_URL + fetch + render de tarjetas
└── README.md              # Esta guía (y metadata de Hugging Face Spaces)
```

## Notas y limitaciones

- **CORS abierto** (`allow_origins=["*"]`) para facilitar la demo. En producción, restringir al dominio de Vercel.
- **Sin persistencia**: las tareas se devuelven en la respuesta, no se guardan.
- Las fechas se conservan **tal como las escribe el usuario** (*"viernes"*, *"el próximo miércoles"*);
  no hay resolución a calendario, por diseño, para no inventar datos.
- El Space gratuito **se duerme** tras un rato sin uso: la primera petición puede tardar unos segundos.
- Se usa la **Interactions API** de Gemini en modo `store=False`: el historial lo gestiona el backend,
  no se guarda conversación en los servidores de Google.
