"""
Catálogos de referencia para los formularios del frontend administrativo.

Endpoints REST:

- GET /api/v1/categorias → listar categorías gastronómicas.
- GET /api/v1/regiones   → listar regiones gastronómicas.

Son endpoints de solo lectura que alimentan los <select> del cliente web
(formulario de platos y de menús).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Categoria, Region
from app.schemas import CategoriaBreve, RegionBreve

router = APIRouter(tags=["Catálogos"])

DB = Annotated[Session, Depends(get_db)]


@router.get("/categorias", response_model=list[CategoriaBreve])
def listar_categorias(db: DB) -> list[Categoria]:
    """Listar las categorías gastronómicas registradas."""
    return list(db.scalars(select(Categoria).order_by(Categoria.nombre)))


@router.get("/regiones", response_model=list[RegionBreve])
def listar_regiones(db: DB) -> list[Region]:
    """Listar las regiones gastronómicas registradas."""
    return list(db.scalars(select(Region).order_by(Region.nombre)))
