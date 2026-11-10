"""
Esquemas Pydantic del módulo de Gestión de Platos (COLRIENT, Sprint 1).

Definen los contratos de entrada/salida de la API REST de platos:

- PlatoCreate : datos para registrar un plato (POST /api/v1/platos).
- PlatoUpdate : campos editables de un plato (PUT /api/v1/platos/{id}).
- PlatoOut    : representación de salida en las respuestas.
- FotoOut     : resultado de la carga de la foto (POST /api/v1/platos/{id}/foto).

FastAPI usa estos esquemas para validar automáticamente las entradas y
responder 422 con mensajes claros cuando el cliente envía datos inválidos
(precio negativo, nombre vacío, campos faltantes, etc.).
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

# Estados permitidos para un plato según el análisis del módulo.
_ESTADOS_PLATO = ("disponible", "agotado")

# Horarios de consumo del restaurante (interfaz del cliente).
HORARIOS_PLATO = ("desayuno", "almuerzo", "cena")


def _normalizar_horarios(valor: list[str]) -> list[str]:
    """Valida y normaliza una lista de horarios (sin duplicados)."""
    limpios: list[str] = []
    for horario in valor:
        h = horario.strip().lower()
        if h not in HORARIOS_PLATO:
            raise ValueError(
                f"Horario inválido: '{horario}'. Valores permitidos: "
                f"{', '.join(HORARIOS_PLATO)}."
            )
        if h not in limpios:
            limpios.append(h)
    return limpios


ListaHorarios = Annotated[list[str], AfterValidator(_normalizar_horarios)]

# Orden natural de presentación de los horarios en la carta digital.
_ORDEN_HORARIOS = {h: i for i, h in enumerate(HORARIOS_PLATO)}


class CategoriaBreve(BaseModel):
    """Resumen de la categoría asociada al plato (salida anidada)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class RegionBreve(BaseModel):
    """Resumen de la región asociada al plato (salida anidada)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class PlatoCreate(BaseModel):
    """Datos requeridos para registrar un plato.

    Caso de uso: Registrar Plato (Cocinero o Gerente).
    """

    nombre: str = Field(
        min_length=1,
        max_length=100,
        examples=["Ajiaco"],
        description="Nombre con el que se reconoce el plato.",
    )
    descripcion: Optional[str] = Field(
        default=None,
        max_length=255,
        examples=["Sopa típica bogotana con pollo, papa y guascas."],
        description="Ingredientes o descripción general del plato.",
    )
    precio: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
        examples=[18000.00],
        description="Precio de venta (mayor que cero, dos decimales).",
    )
    estado: str = Field(
        default="disponible",
        pattern=f"^({'|'.join(_ESTADOS_PLATO)})$",
        examples=["disponible"],
        description="Estado del plato en la carta.",
    )
    id_categoria: int = Field(
        gt=0,
        examples=[1],
        description="Identificador de la categoría gastronómica (FK).",
    )
    id_region: int = Field(
        gt=0,
        examples=[1],
        description="Identificador de la región gastronómica (FK).",
    )
    horarios: ListaHorarios = Field(
        default=[],
        examples=[["almuerzo", "cena"]],
        description="Horarios de consumo del plato (desayuno, almuerzo, cena).",
    )
    recomendado: bool = Field(
        default=False,
        examples=[True],
        description="Destaca el plato en la sección 'Recomendados' de la carta.",
    )
    precio_promocional: Optional[Decimal] = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
        examples=[12000.00],
        description="Precio en promoción; debe ser menor que el precio normal.",
    )

    @model_validator(mode="after")
    def _promocion_menor_que_precio(self) -> "PlatoCreate":
        if self.precio_promocional is not None and self.precio_promocional >= self.precio:
            raise ValueError("El precio promocional debe ser menor que el precio normal.")
        return self


class PlatoUpdate(BaseModel):
    """Campos editables de un plato (PUT).

    Todos los campos son opcionales: solo se actualizan los enviados.
    Caso de uso: Editar Información del Plato (Cocinero o Gerente).
    """

    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    precio: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    estado: Optional[str] = Field(
        default=None, pattern=f"^({'|'.join(_ESTADOS_PLATO)})$"
    )
    id_categoria: Optional[int] = Field(default=None, gt=0)
    id_region: Optional[int] = Field(default=None, gt=0)
    horarios: Optional[ListaHorarios] = Field(
        default=None,
        description="Reemplaza los horarios de consumo del plato.",
    )
    recomendado: Optional[bool] = Field(default=None)
    precio_promocional: Optional[Decimal] = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
        description="Use null explícito para retirar la promoción.",
    )


class PlatoOut(BaseModel):
    """Representación de un plato en las respuestas de la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio: Decimal
    precio_promocional: Optional[Decimal] = None
    estado: str
    recomendado: bool = False
    horarios: list[str] = []
    foto_url: Optional[str] = None
    id_categoria: int
    id_region: int
    categoria: CategoriaBreve
    region: RegionBreve

    @field_validator("horarios", mode="before")
    @classmethod
    def _horarios_como_lista(cls, valor):
        """La relación ORM (association proxy) se convierte en lista de
        strings ordenada de forma natural (desayuno, almuerzo, cena)."""
        return sorted(valor or [], key=lambda h: _ORDEN_HORARIOS.get(h, len(HORARIOS_PLATO)))


class FotoOut(BaseModel):
    """Resultado de la carga de la foto de un plato."""

    mensaje: str
    foto_url: str


# ============================================================================
# Módulo: Ingredientes y Recetas (Sprint 2)
# ============================================================================

class IngredienteCreate(BaseModel):
    """Datos para registrar un ingrediente (sin duplicados por nombre)."""

    nombre: str = Field(
        min_length=1,
        max_length=100,
        examples=["Papa criolla"],
        description="Nombre del insumo.",
    )
    unidad_medida: str = Field(
        min_length=1,
        max_length=30,
        examples=["kg"],
        description="Unidad de medida (kg, g, l, ml, unidades, ...).",
    )


class IngredienteOut(BaseModel):
    """Representación de un ingrediente en las respuestas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    unidad_medida: str


class RecetaAsociar(BaseModel):
    """Datos para asociar un ingrediente a la receta de un plato."""

    id_ingrediente: int = Field(gt=0, examples=[1])
    cantidad: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
        examples=[0.5],
        description="Cantidad requerida del ingrediente.",
    )


class RecetaItemOut(BaseModel):
    """Línea de la receta: ingrediente con su cantidad."""

    model_config = ConfigDict(from_attributes=True)

    id_ingrediente: int
    cantidad: Decimal
    ingrediente: IngredienteOut


class RecetaOut(BaseModel):
    """Receta completa de un plato (ingredientes + cantidades)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    recetas: list[RecetaItemOut]


# ============================================================================
# Módulo: Gestión del Menú (Sprint 2)
# ============================================================================

_ESTADOS_MENU = ("activo", "inactivo")


class MenuCreate(BaseModel):
    """Datos para crear un menú por categoría con vigencia."""

    nombre: str = Field(min_length=1, max_length=100, examples=["Almuerzos noviembre"])
    fecha_inicio: date = Field(examples=["2026-11-01"], description="Inicio de vigencia.")
    fecha_fin: date = Field(examples=["2026-11-30"], description="Fin de vigencia.")
    estado: str = Field(
        default="inactivo",
        pattern=f"^({'|'.join(_ESTADOS_MENU)})$",
        description="'inactivo' (borrador) hasta que se publica la carta.",
    )
    id_categoria: int = Field(gt=0, examples=[1])


class MenuOut(BaseModel):
    """Representación de un menú en las respuestas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    fecha_inicio: date
    fecha_fin: date
    estado: str
    id_categoria: int
    categoria: CategoriaBreve
