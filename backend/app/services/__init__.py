"""
Capa de servicios (lógica de negocio) del sistema COLRIENT.

Cada módulo implementa sus operaciones en un archivo propio, p. ej.:
- app/services/plato_service.py -> registrar, editar, eliminar, clasificar

Los endpoints (app/api/v1/endpoints) delegan aquí el acceso a datos y
las reglas de negocio, manteniendo las capas separadas:

    endpoint -> servicio -> modelo ORM -> base de datos
"""
