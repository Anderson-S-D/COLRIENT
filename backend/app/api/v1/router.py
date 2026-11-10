"""
Enrutador principal de la API v1.

Agrega los routers de cada módulo del sistema COLRIENT bajo el prefijo
común /api/v1 (definido en app.core.config y aplicado en main.py).

Módulos implementados:
- health       : ruta de prueba del servidor.
- platos       : gestión de platos (Sprint 1).
- ingredientes : ingredientes y recetas (Sprint 2).
- menus        : gestión del menú (Sprint 2).
- catalogos    : categorías y regiones para los formularios.

Módulos previstos (Sprint 3 en adelante):
- cliente : interfaz del cliente final.
"""

from fastapi import APIRouter

from app.routers import catalogos, health, ingredientes, menus, platos

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(platos.router)
api_v1_router.include_router(ingredientes.router)
api_v1_router.include_router(menus.router)
api_v1_router.include_router(catalogos.router)

# --- Módulos previstos ------------------------------------------------------
# from app.routers import cliente
# api_v1_router.include_router(cliente.router)  # Interfaz del cliente
