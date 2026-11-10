"""
Módulo: Gestión del Menú (Sprint 2 de COLRIENT).

Endpoints REST bajo /api/v1/menus:

- POST /api/v1/menus              → Crear menú por categoría con fechas de vigencia.
- GET  /api/v1/menus/historico   → Consultar el histórico de menús (filtros opcionales).
- PUT  /api/v1/menus/{id}/publicar → Publicar la carta digital activa.

Regla de negocio: solo puede existir UN menú publicado (estado "activo")
a la vez; al publicar uno, los demás pasan automáticamente a "inactivo".

Manejo de excepciones HTTP:
- 404 : el menú no existe.
- 400 : categoría inexistente o rango de vigencia inválido.
- 422 : datos inválidos (validación automática de Pydantic).
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Categoria, Menu
from app.schemas import MenuCreate, MenuOut

router = APIRouter(prefix="/menus", tags=["Gestión del menú"])

DB = Annotated[Session, Depends(get_db)]


def _validar_creacion(db: Session, datos: MenuCreate) -> None:
    """Valida la categoría y el rango de vigencia antes de crear el menú."""
    if db.get(Categoria, datos.id_categoria) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La categoría con id={datos.id_categoria} no existe.",
        )
    if datos.fecha_fin < datos.fecha_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La fecha de fin ({datos.fecha_fin}) debe ser posterior "
                f"o igual a la fecha de inicio ({datos.fecha_inicio})."
            ),
        )


@router.post("", response_model=MenuOut, status_code=status.HTTP_201_CREATED)
def crear_menu(datos: MenuCreate, db: DB) -> Menu:
    """Crear un menú por categoría con su rango de vigencia.

    El menú se crea como borrador (estado 'inactivo') hasta que se
    publique con PUT /menus/{id}/publicar.
    """
    _validar_creacion(db, datos)
    menu = Menu(**datos.model_dump())
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return menu


@router.get("/historico", response_model=list[MenuOut])
def historico_menus(
    db: DB,
    categoria: Optional[int] = Query(None, gt=0, description="Filtrar por id de categoría."),
    estado: Optional[str] = Query(
        None, pattern="^(activo|inactivo)$", description="Filtrar por estado."
    ),
) -> list[Menu]:
    """Consultar el histórico de menús, del más reciente al más antiguo.

    Filtros opcionales: categoría y estado (activo/inactivo).
    """
    stmt = select(Menu)
    if categoria is not None:
        stmt = stmt.where(Menu.id_categoria == categoria)
    if estado is not None:
        stmt = stmt.where(Menu.estado == estado)
    return list(db.scalars(stmt.order_by(Menu.fecha_inicio.desc(), Menu.id.desc())))


@router.put("/{menu_id}/publicar", response_model=MenuOut)
def publicar_menu(menu_id: int, db: DB) -> Menu:
    """Publicar la carta digital: activa este menú y desactiva los demás.

    Solo un menú puede estar activo a la vez (la carta digital vigente).
    Responde 404 si el menú no existe.
    """
    menu = db.get(Menu, menu_id)
    if menu is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un menú con id={menu_id}.",
        )
    db.execute(update(Menu).where(Menu.id != menu_id).values(estado="inactivo"))
    menu.estado = "activo"
    db.commit()
    db.refresh(menu)
    return menu
