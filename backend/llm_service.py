"""Cliente Gemini + loop de function calling (Interactions API, modo stateless)."""

import json
import os

from google import genai

from funciones import calcular_prioridad, crear_tarea

# gemini-3.8-flash es el Flash actual. Si topas con los límites del free tier,
# pon GEMINI_MODEL=gemini-3.5-flash-lite en las variables del Space.
MODELO = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
MAX_ITERACIONES = 4

_cliente = None


def get_cliente():
    """Instancia perezosa: así la app arranca aunque falte la key al importar."""
    global _cliente
    if _cliente is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Falta la variable de entorno GEMINI_API_KEY")
        _cliente = genai.Client(api_key=api_key)
    return _cliente


# Formato de Gemini: name/description/parameters van al nivel superior del dict
# (no anidados bajo una clave "function" como en la API de OpenAI).
TOOLS = [
    {
        "type": "function",
        "name": "crear_tarea",
        "description": (
            "Crea una tarea o reunión concreta. Usar sólo cuando se conocen "
            "título, fecha, hora y participantes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "titulo": {
                    "type": "string",
                    "description": "Título breve y claro de la tarea o reunión.",
                },
                "fecha": {
                    "type": "string",
                    "description": "Fecha indicada por el usuario, tal como la expresó (ej. 'viernes', '2026-09-25').",
                },
                "hora": {
                    "type": "string",
                    "description": "Hora en formato HH:MM de 24 horas.",
                },
                "participantes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Nombres de las personas involucradas.",
                },
                "prioridad": {
                    "type": "string",
                    "enum": ["alta", "normal", "baja"],
                    "description": "Prioridad de la tarea. Por defecto 'normal'.",
                },
            },
            "required": ["titulo", "fecha", "hora", "participantes"],
        },
    },
    {
        "type": "function",
        "name": "calcular_prioridad",
        "description": (
            "Calcula la prioridad (alta/normal/baja) a partir del impacto y la "
            "urgencia. Usar antes de crear_tarea cuando haya que estimar la prioridad."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "impacto": {
                    "type": "string",
                    "enum": ["bajo", "medio", "alto"],
                    "description": "Impacto estimado de la tarea.",
                },
                "urgencia": {
                    "type": "string",
                    "enum": ["bajo", "medio", "alto"],
                    "description": "Urgencia estimada de la tarea.",
                },
            },
            "required": ["impacto", "urgencia"],
        },
    },
]

FUNCIONES_DISPONIBLES = {
    "crear_tarea": crear_tarea,
    "calcular_prioridad": calcular_prioridad,
}

SYSTEM_PROMPT = """Eres un asistente de productividad que convierte peticiones en lenguaje natural en tareas estructuradas.

Reglas obligatorias:
1. NUNCA inventes datos que el usuario no haya dado. No supongas horas, fechas, nombres ni prioridades.
2. Para crear una tarea necesitas: título, fecha, hora y participantes. Si falta alguno de esos cuatro datos, NO llames a ninguna función: responde en texto, en español, indicando exactamente qué datos faltan y pidiéndolos.
3. Si el usuario indica explícitamente la prioridad (por ejemplo "la prioridad es alta"), úsala directamente en crear_tarea.
4. Si el usuario pide estimar, calcular o deducir la prioridad, llama primero a calcular_prioridad con el impacto y la urgencia que se desprendan del mensaje, y usa su resultado como valor de prioridad al llamar después a crear_tarea.
5. Usa las funciones disponibles en lugar de describir con palabras lo que harías.
6. Responde siempre en español."""


def _ejecutar(nombre, argumentos):
    funcion = FUNCIONES_DISPONIBLES.get(nombre)
    if funcion is None:
        return {"error": f"Función desconocida: {nombre}"}
    return funcion(**argumentos)


def _a_dict(paso):
    """Los pasos vienen como objetos pydantic; el historial los necesita serializables."""
    if hasattr(paso, "model_dump"):
        return paso.model_dump(exclude_none=True)
    return paso


def _argumentos(llamada):
    brutos = getattr(llamada, "arguments", None) or {}
    if isinstance(brutos, str):
        try:
            return json.loads(brutos or "{}")
        except json.JSONDecodeError:
            return {}
    return dict(brutos)


def procesar_solicitud(solicitud):
    """Ejecuta el loop de function calling y devuelve el resultado estructurado."""
    # store=False -> sin estado en el servidor de Google: nosotros llevamos el historial.
    historial = [{"type": "user_input", "content": [{"type": "text", "text": solicitud}]}]

    tareas_creadas = []
    calculos = []
    cliente = get_cliente()

    for _ in range(MAX_ITERACIONES):
        interaccion = cliente.interactions.create(
            model=MODELO,
            store=False,
            input=historial,
            tools=TOOLS,
            system_instruction=SYSTEM_PROMPT,
            generation_config={"temperature": 0.2, "max_output_tokens": 1024},
        )

        pasos = list(interaccion.steps or [])
        historial.extend(_a_dict(p) for p in pasos)

        llamadas = [p for p in pasos if getattr(p, "type", None) == "function_call"]

        if not llamadas:
            # El modelo contestó en texto: o pide aclaración, o resume lo hecho.
            if tareas_creadas or calculos:
                break
            return {
                "tipo": "respuesta_texto",
                "mensaje": interaccion.output_text or "No pude interpretar la solicitud.",
            }

        for llamada in llamadas:
            nombre = llamada.name
            argumentos = _argumentos(llamada)
            resultado = _ejecutar(nombre, argumentos)

            if nombre == "crear_tarea" and isinstance(resultado, dict) and "error" not in resultado:
                tareas_creadas.append(resultado)
            elif nombre == "calcular_prioridad":
                calculos.append({"argumentos": argumentos, "prioridad": resultado})

            historial.append(
                {
                    "type": "function_result",
                    "name": nombre,
                    "call_id": llamada.id,
                    "result": [{"type": "text", "text": json.dumps(resultado, ensure_ascii=False)}],
                }
            )

    return {
        "tipo": "tarea_generada",
        "tareas_creadas": tareas_creadas,
        "calculos": calculos,
    }
