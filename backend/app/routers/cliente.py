"""
Módulo: Interfaz del cliente (COLRIENT).

Casos de uso previstos (acceso público, sin autenticación):
- Visualizar la carta digital
- Filtrar platos por categoría y horario
- Ver imagen y descripción detallada del plato
- Consultar promociones y platos recomendados
"""

from fastapi import APIRouter

router = APIRouter(prefix="/cliente", tags=["Interfaz del cliente"])

# TODO: rutas de solo lectura para el cliente final (consume los otros módulos).
