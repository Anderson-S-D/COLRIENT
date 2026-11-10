"""
COLRIENT - Sistema de gestión de restaurante
===========================================

Punto de entrada del servidor backend (arquitectura Cliente-Servidor).

- Servidor: API REST construida con FastAPI que expone los servicios
  del sistema bajo el prefijo /api/v1.
- Cliente: aplicación web estática (HTML/CSS/JS) que consume la API y
  es servida por este mismo proceso desde la carpeta ../frontend.

Ejecución en desarrollo:
    uvicorn main:app --reload

Ejecución en producción:
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida del servidor: inicializa la base de datos al arrancar."""
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS (Cross-Origin Resource Sharing)
# Habilita que el cliente web consuma la API desde un origen distinto,
# por ejemplo al servir el frontend con VS Code Live Server (puerto 5500).
# Los orígenes permitidos se configuran en app/core/config.py.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API versión 1: expone todos los módulos bajo /api/v1
# ---------------------------------------------------------------------------
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


# ---------------------------------------------------------------------------
# Archivos subidos (fotos de los platos) → se sirven en /uploads/**
# ---------------------------------------------------------------------------
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.FOTOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")


# ---------------------------------------------------------------------------
# Cliente web estático (frontend)
# Se monta AL FINAL para que las rutas /api/v1/** y /docs tengan prioridad.
# ---------------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="cliente-web")
