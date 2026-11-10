"""
Módulo: Gestión de Platos (Sprint 1 de COLRIENT).

Endpoints REST bajo /api/v1/platos:

- POST   /                → Registrar plato.
- GET    /                → Consultar platos (filtros: categoría, región,
                            nombre, horario, recomendado, promoción).
- PUT    /{plato_id}      → Editar información del plato.
- DELETE /{plato_id}      → Eliminar plato (solo Gerente).
- POST   /{plato_id}/foto → Cargar y almacenar la imagen del plato.

Actores según el análisis: Cocinero y Gerente/Administrador.
La eliminación es exclusiva del Gerente; mientras el módulo de
autenticación no esté implementado, el rol se recibe en la cabecera
"X-Rol" (X-Rol: gerente | cocinero).

Manejo de excepciones HTTP:
- 404 : el plato (o la relación) solicitado no existe.
- 400 : llaves foráneas inexistentes o petición sin campos que actualizar.
- 403 : un rol sin permisos intenta eliminar un plato.
- 413 : la foto supera el tamaño máximo permitido.
- 415 : la foto tiene un formato no permitido.
- 422 : datos inválidos (validación automática de Pydantic/FastAPI).
"""

import uuid
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models import Categoria, Plato, Region
from app.schemas import HORARIOS_PLATO, FotoOut, PlatoCreate, PlatoOut, PlatoUpdate

router = APIRouter(prefix="/platos", tags=["Platos"])

DB = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Utilidades y dependencias
# ---------------------------------------------------------------------------

def _obtener_plato_o_404(db: Session, plato_id: int) -> Plato:
    """Busca el plato por id o lanza 404 con un mensaje claro."""
    plato = db.get(Plato, plato_id)
    if plato is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No existe un plato con id={plato_id}.",
        )
    return plato


def _validar_relaciones(db: Session, id_categoria: Optional[int], id_region: Optional[int]) -> None:
    """Verifica que las llaves foráneas existan; lanza 400 si no."""
    if id_categoria is not None and db.get(Categoria, id_categoria) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La categoría con id={id_categoria} no existe.",
        )
    if id_region is not None and db.get(Region, id_region) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La región con id={id_region} no existe.",
        )


def _requerir_gerente(x_rol: Annotated[str, Header()] = "") -> None:
    """Dependencia: permite continuar solo si el rol es Gerente/Administrador.

    El valor por defecto evita un 422 cuando la cabecera no se envía;
    en ese caso se responde 403 con un mensaje claro.
    """
    if x_rol.strip().lower() != "gerente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Solo el Gerente/Administrador puede eliminar platos. "
                "Envíe la cabecera 'X-Rol: gerente'."
            ),
        )


def _eliminar_foto_anterior(foto_url: Optional[str]) -> None:
    """Borra del disco la foto previa del plato (si está en nuestro almacenamiento)."""
    if foto_url and foto_url.startswith("/uploads/"):
        ruta = settings.UPLOAD_DIR / foto_url.removeprefix("/uploads/")
        ruta.unlink(missing_ok=True)


def _validar_promocion(plato: Plato) -> None:
    """Comprueba la coherencia de la promoción con el precio vigente."""
    if plato.precio_promocional is not None and plato.precio_promocional >= plato.precio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El precio promocional debe ser menor que el precio normal.",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=PlatoOut, status_code=status.HTTP_201_CREATED)
def registrar_plato(datos: PlatoCreate, db: DB) -> Plato:
    """Registrar un plato nuevo (Cocinero o Gerente).

    Devuelve 201 con el plato creado; 400 si la categoría o la región
    no existen y 422 si algún dato es inválido.
    """
    _validar_relaciones(db, datos.id_categoria, datos.id_region)
    plato = Plato(**datos.model_dump(exclude={"horarios"}))
    plato.horarios = datos.horarios  # association proxy → filas plato_horario
    db.add(plato)
    db.commit()
    db.refresh(plato)
    return plato


@router.get("", response_model=list[PlatoOut])
def listar_platos(
    db: DB,
    categoria: Optional[int] = Query(
        None, gt=0, description="Filtrar por id de categoría."
    ),
    region: Optional[int] = Query(
        None, gt=0, description="Filtrar por id de región."
    ),
    nombre: Optional[str] = Query(
        None, min_length=1, description="Buscar por nombre (coincidencia parcial)."
    ),
    horario: Optional[str] = Query(
        None,
        pattern=f"^({'|'.join(HORARIOS_PLATO)})$",
        description="Filtrar por horario de consumo (desayuno, almuerzo, cena).",
    ),
    recomendado: Optional[bool] = Query(
        None, description="Filtrar por la marca de recomendado."
    ),
    promocion: Optional[bool] = Query(
        None, description="true → solo platos en promoción; false → sin promoción."
    ),
) -> list[Plato]:
    """Consultar la lista general de platos con filtros opcionales."""
    stmt = select(Plato)
    if categoria is not None:
        stmt = stmt.where(Plato.id_categoria == categoria)
    if region is not None:
        stmt = stmt.where(Plato.id_region == region)
    if nombre is not None:
        stmt = stmt.where(Plato.nombre.ilike(f"%{nombre}%"))
    if horario is not None:
        stmt = stmt.where(Plato.horarios_asoc.any(horario=horario))
    if recomendado is not None:
        stmt = stmt.where(Plato.recomendado == recomendado)
    if promocion is not None:
        tiene_promo = (
            Plato.precio_promocional.is_not(None)
            if promocion
            else Plato.precio_promocional.is_(None)
        )
        stmt = stmt.where(tiene_promo)
    return list(db.scalars(stmt.order_by(Plato.id)))


@router.put("/{plato_id}", response_model=PlatoOut)
def editar_plato(plato_id: int, datos: PlatoUpdate, db: DB) -> Plato:
    """Editar la información de un plato (Cocinero o Gerente).

    Solo se actualizan los campos enviados. Devuelve 404 si el plato
    no existe, 400 si la categoría/región destino no existe o si no se
    envió ningún campo.
    """
    plato = _obtener_plato_o_404(db, plato_id)
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se envió ningún campo para actualizar.",
        )
    _validar_relaciones(db, cambios.get("id_categoria"), cambios.get("id_region"))
    horarios = cambios.pop("horarios", None)
    for campo, valor in cambios.items():
        setattr(plato, campo, valor)
    if horarios is not None:
        plato.horarios = horarios  # reemplaza el conjunto de horarios
    _validar_promocion(plato)
    db.commit()
    db.refresh(plato)
    return plato


@router.delete("/{plato_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_plato(plato_id: int, db: DB, _rol: None = Depends(_requerir_gerente)) -> None:
    """Eliminar un plato (solo Gerente/Administrador, cabecera X-Rol).

    Las recetas asociadas se eliminan en cascada. Devuelve 404 si el
    plato no existe y 403 si el rol no tiene permisos.
    """
    plato = _obtener_plato_o_404(db, plato_id)
    _eliminar_foto_anterior(plato.foto_url)
    db.delete(plato)  # cascade="all, delete-orphan" en Plato.recetas
    db.commit()


@router.post("/{plato_id}/foto", response_model=FotoOut)
async def cargar_foto(
    plato_id: int,
    db: DB,
    foto: Annotated[UploadFile, File(description="Imagen del plato (JPEG, PNG o WebP).")],
) -> FotoOut:
    """Cargar y almacenar la imagen de un plato (Cocinero o Gerente).

    La imagen se guarda en el servidor (uploads/platos/) y se actualiza
    el campo foto_url del plato. Devuelve 404 si el plato no existe,
    413 si supera el tamaño máximo y 415 si el formato no está permitido.
    """
    plato = _obtener_plato_o_404(db, plato_id)

    extension = settings.MIME_FOTOS_PERMITIDOS.get(foto.content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Formato '{foto.content_type}' no permitido. "
                f"Use uno de: {', '.join(settings.MIME_FOTOS_PERMITIDOS)}."
            ),
        )

    contenido = await foto.read()
    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de imagen está vacío.",
        )
    if len(contenido) > settings.MAX_FOTO_BYTES:
        maximo_mb = settings.MAX_FOTO_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"La imagen supera el tamaño máximo de {maximo_mb} MB.",
        )

    nombre_archivo = f"plato_{plato_id}_{uuid.uuid4().hex[:8]}{extension}"
    (settings.FOTOS_DIR / nombre_archivo).write_bytes(contenido)

    _eliminar_foto_anterior(plato.foto_url)  # conserva una sola foto por plato
    plato.foto_url = f"/uploads/platos/{nombre_archivo}"
    db.commit()
    db.refresh(plato)
    return FotoOut(
        mensaje=f"Foto del plato '{plato.nombre}' actualizada correctamente.",
        foto_url=plato.foto_url,
    )
