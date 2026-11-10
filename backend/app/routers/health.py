"""
Endpoint de salud del servidor.

Ruta: GET /api/v1/health

Propósito: verificar de forma rápida que el backend está en ejecución
y respondiendo correctamente (útil para pruebas y monitoreo).
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["Sistema"])


@router.get("/health")
def health_check() -> dict:
    """Ruta de prueba que reporta el estado del servicio."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
