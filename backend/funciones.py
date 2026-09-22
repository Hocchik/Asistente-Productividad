"""Funciones de negocio puras (sin IA). El LLM sólo decide cuándo llamarlas."""

from datetime import datetime

ESCALA = {"bajo": 1, "medio": 2, "alto": 3}


def crear_tarea(titulo, fecha, hora, participantes, prioridad="normal"):
    """Crea la representación de una tarea.

    participantes puede llegar como lista o como texto separado por comas.
    """
    if isinstance(participantes, str):
        participantes = [p.strip() for p in participantes.replace(" y ", ",").split(",") if p.strip()]

    return {
        "titulo": titulo,
        "fecha": fecha,
        "hora": hora,
        "participantes": participantes,
        "prioridad": prioridad,
        "estado": "pendiente",
        "creada_en": datetime.now().isoformat(),
    }


def calcular_prioridad(impacto, urgencia):
    """Combina impacto y urgencia (bajo/medio/alto) en alta | normal | baja."""
    i = ESCALA.get(str(impacto).strip().lower(), 2)
    u = ESCALA.get(str(urgencia).strip().lower(), 2)
    total = i + u

    if total >= 5:
        return "alta"
    if total <= 3:
        return "baja"
    return "normal"
