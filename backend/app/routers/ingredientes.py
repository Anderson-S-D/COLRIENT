"""
Módulo: Gestión de Ingredientes y Recetas (Sprint 2 de COLRIENT).

Endpoints REST:

- POST   /api/v1/ingredientes                          → Registrar ingrediente (sin duplicados).
- GET    /api/v1/ingredientes                          → Listar ingredientes (catálogo para formularios).
- POST   /api/v1/platos/{id}/ingredientes              → Asociar ingrediente y cantidad a la receta.
- GET    /api/v1/platos/{id}/receta                    → Consultar la receta completa del plato.
- DELETE /api/v1/platos/{id_plato}/ingredientes/{id_ingrediente} → Eliminar ingrediente de la receta.

La sustitución de un ingrediente se logra combinando dos operaciones:
eliminar el ingrediente actual y asociar el nuevo.

Manejo de excepciones HTTP:
- 404 : el plato no existe.
- 400 : el ingrediente referenciado no existe.
- 409 : nombre de ingrediente duplicado o ingrediente ya asociado al plato.
- 422 : datos inválidos (validación automática de Pydantic).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ingrediente, Plato, Receta
from app.schemas import IngredienteCreate, IngredienteOut, RecetaAsociar, RecetaOut

router = APIRouter(tags=["Ingredientes y recetas"])

DB = Annotated[Session, Depends(get_db)]


def _obtener_plato_o_404(db: Session, plato_id: int) -> Plato:
    """Busca el plato por id o lanza 404 con un mensaje claro."""
    plato = db.get(Plato, plato_id)
    if plato is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un plato con id={plato_id}.",
        )
    return plato


@router.post("/ingredientes", response_model=IngredienteOut, status_code=status.HTTP_201_CREATED)
def registrar_ingrediente(datos: IngredienteCreate, db: DB) -> Ingrediente:
    """Registrar un ingrediente nuevo; el nombre no puede repetirse.

    La comparación es insensible a mayúsculas ("Papa" == "papa").
    Devuelve 409 si ya existe un ingrediente con ese nombre.
    """
    duplicado = db.scalar(
        select(Ingrediente).where(func.lower(Ingrediente.nombre) == datos.nombre.strip().lower())
    )
    if duplicado is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un ingrediente registrado con el nombre '{duplicado.nombre}'.",
        )
    ingrediente = Ingrediente(**datos.model_dump())
    db.add(ingrediente)
    db.commit()
    db.refresh(ingrediente)
    return ingrediente


@router.get("/ingredientes", response_model=list[IngredienteOut])
def listar_ingredientes(db: DB) -> list[Ingrediente]:
    """Listar todos los ingredientes registrados (catálogo para formularios)."""
    return list(db.scalars(select(Ingrediente).order_by(Ingrediente.nombre)))


@router.post(
    "/platos/{plato_id}/ingredientes", response_model=RecetaOut, status_code=status.HTTP_201_CREATED
)
def asociar_ingrediente(plato_id: int, datos: RecetaAsociar, db: DB) -> Plato:
    """Asociar un ingrediente con su cantidad a la receta de un plato.

    Devuelve la receta completa actualizada. Responde 404 si el plato no
    existe, 400 si el ingrediente no existe y 409 si el ingrediente ya
    está asociado (para sustituirlo, elimínelo primero).
    """
    plato = _obtener_plato_o_404(db, plato_id)
    ingrediente = db.get(Ingrediente, datos.id_ingrediente)
    if ingrediente is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El ingrediente con id={datos.id_ingrediente} no existe.",
        )
    if db.get(Receta, (plato_id, datos.id_ingrediente)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"El ingrediente '{ingrediente.nombre}' ya está asociado al plato "
                f"'{plato.nombre}'. Elimínelo primero para sustituirlo."
            ),
        )
    db.add(Receta(id_plato=plato_id, id_ingrediente=datos.id_ingrediente, cantidad=datos.cantidad))
    db.commit()
    db.refresh(plato)
    return plato


@router.get("/platos/{plato_id}/receta", response_model=RecetaOut)
def consultar_receta(plato_id: int, db: DB) -> Plato:
    """Consultar la receta completa de un plato (ingredientes y cantidades).

    Un plato sin ingredientes devuelve una lista vacía.
    """
    return _obtener_plato_o_404(db, plato_id)


@router.delete(
    "/platos/{plato_id}/ingredientes/{ingrediente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def eliminar_ingrediente_de_receta(plato_id: int, ingrediente_id: int, db: DB) -> None:
    """Eliminar un ingrediente de la receta del plato (sustitución paso 1).

    Responde 404 si el plato no existe o si el ingrediente no está
    asociado a su receta.
    """
    _obtener_plato_o_404(db, plato_id)
    item = db.get(Receta, (plato_id, ingrediente_id))
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"El ingrediente con id={ingrediente_id} no está asociado "
                f"a la receta del plato con id={plato_id}."
            ),
        )
    db.delete(item)
    db.commit()
