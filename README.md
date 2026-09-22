# Asistente de Productividad

Convierte solicitudes escritas en lenguaje natural en **tareas estructuradas**, usando un LLM
(Gemini 3.8 Flash) que decide **cuándo** llamar a funciones Python reales — no genera
los datos por sí mismo.

- **Backend:** FastAPI + Gemini *function calling* → Render (free tier)
- **Frontend:** HTML + CSS + JavaScript puro (sin frameworks) → Vercel
- **Sin base de datos.** Todo funciona en el *free tier* de Google AI Studio, Render y Vercel, sin tarjeta de crédito.

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

> Nunca subas la clave al repositorio. En local usa una variable de entorno; en Render usa una *Environment Variable*.

## 2. Desplegar el backend en Render

> **Por qué Render y no Hugging Face Spaces:** desde julio de 2026 los Spaces de tipo
> Docker y Gradio requieren plan PRO de pago. Los Static Spaces siguen siendo gratis, pero
> sólo sirven HTML y no pueden ejecutar Python. Render mantiene un free tier real sin tarjeta.

1. Entra a <https://render.com> y crea una cuenta (**Sign up with GitHub** es lo más cómodo).
2. **New +** → **Web Service** → conecta tu repositorio de GitHub y selecciónalo.
3. Configura el servicio:

   | Campo | Valor |
   |---|---|
   | **Name** | `asistente-productividad` |
   | **Language** | `Python 3` |
   | **Branch** | `main` |
   | **Root Directory** | `backend` |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
   | **Instance Type** | **Free** |

   > `Root Directory = backend` es lo que hace que funcione sin mover archivos: Render
   > trata esa carpeta como la raíz del servicio.
   >
   > Si prefieres usar el `Dockerfile` incluido, elige **Language: Docker** y deja vacíos
   > Build y Start Command. Funciona igual.

4. Baja a **Environment Variables** → **Add Environment Variable**:
   - Key: `GEMINI_API_KEY` · Value: tu clave `AIza...`
   - (Opcional) Key: `GEMINI_MODEL` · Value: `gemini-3.5-flash-lite`, si topas con los límites.
5. **Create Web Service**. El primer build tarda unos minutos.
6. Cuando el estado sea **Live**, tu URL es `https://asistente-productividad.onrender.com`
   (Render puede añadirle un sufijo aleatorio; usa la que te muestre arriba).
7. Ábrela en el navegador: debe responder `{"estado":"ok",...}`.

Cada `git push` a `main` redespliega el servicio automáticamente.

## 3. Desplegar el frontend en Vercel

> Despliega primero el backend: necesitas su URL de Render para este paso.

1. Abre `frontend/script.js` y pega la URL de Render en `BACKEND_URL` (**sin barra final**):
   ```js
   const BACKEND_URL = "https://asistente-productividad.onrender.com";
   ```
   Haz commit y push: `git add -A && git commit -m "Apuntar al backend" && git push`
2. Entra a <https://vercel.com>, inicia sesión con GitHub → **Add New… → Project** → importa el repo.
3. Configura:
   - **Framework Preset:** `Other`
   - **Root Directory:** `frontend`
   - Build Command y Output Directory: **vacíos** (es sitio estático, no hay build)
4. **Deploy**. Obtendrás una URL tipo `https://asistente-productividad.vercel.app`.

Cada push a `main` redespliega el frontend automáticamente.

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
curl -X POST https://asistente-productividad.onrender.com/procesar-solicitud \
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
│   ├── Dockerfile         # python:3.11-slim, uvicorn en $PORT (7860 por defecto)
│   └── .gitignore
├── frontend/
│   ├── index.html         # Textarea + botón + zonas de estado y resultado
│   ├── style.css          # Diseño centrado, sin dependencias externas
│   └── script.js          # BACKEND_URL + fetch + render de tarjetas
└── README.md              # Esta guía
```

## Notas y limitaciones

- **CORS abierto** (`allow_origins=["*"]`) para facilitar la demo. En producción, restringir al dominio de Vercel.
- **Sin persistencia**: las tareas se devuelven en la respuesta, no se guardan.
- Las fechas se conservan **tal como las escribe el usuario** (*"viernes"*, *"el próximo miércoles"*);
  no hay resolución a calendario, por diseño, para no inventar datos.
- El plan gratuito de Render **duerme el servicio tras 15 min sin tráfico**: la primera petición
  después de ese rato tarda ~1 minuto en responder. Incluye 750 h/mes, de sobra para una demo.
- Se usa la **Interactions API** de Gemini en modo `store=False`: el historial lo gestiona el backend,
  no se guarda conversación en los servidores de Google.
