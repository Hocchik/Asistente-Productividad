"""API del asistente de productividad. Escucha en $PORT (7860 por defecto)."""

import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import llm_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("asistente")

app = FastAPI(
    title="Asistente de Productividad",
    description="Convierte solicitudes en lenguaje natural en tareas estructuradas usando Gemini + function calling.",
    version="1.0.0",
)

# Abierto para que el frontend en Vercel pueda consumirlo sin configuración.
# En producción: reemplazar ["*"] por el dominio exacto del frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SolicitudEntrada(BaseModel):
    solicitud: str = ""


@app.get("/")
def healthcheck():
    return {
        "estado": "ok",
        "servicio": "asistente-productividad",
        "modelo": llm_service.MODELO,
    }


@app.post("/procesar-solicitud")
def procesar_solicitud(entrada: SolicitudEntrada):
    texto = (entrada.solicitud or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="El campo 'solicitud' no puede estar vacío.")

    try:
        return llm_service.procesar_solicitud(texto)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error procesando la solicitud")
        raise HTTPException(status_code=500, detail=f"Error al consultar el modelo: {exc}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
