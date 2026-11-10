"""
Modelos ORM del sistema COLRIENT (SQLAlchemy 2.0).

Traduce el modelo relacional a clases Python; cada clase hereda de
`Base` (app/database.py) y las tablas se crean automáticamente al
iniciar la aplicación mediante `init_db()`.

Tablas y columnas:

    region       (id, nombre, descripcion)
    categoria    (id, nombre, descripcion)
    plato        (id, nombre, descripcion, precio, precio_promocional,
                  foto_url, estado, recomendado, id_categoria, id_region)
    plato_horario(id_plato, horario)    -> PK compuesta (desayuno/almuerzo/cena)
    ingrediente  (id, nombre, unidad_medida)
    receta       (id_plato, id_ingrediente, cantidad)   -> PK compuesta
    menu         (id, nombre, fecha_inicio, fecha_fin, estado, id_categoria)

Relaciones:

    Region   1 --- N  Plato  N --- 1  Categoria  1 --- N  Menu
                      Plato  1 --- N  Receta     N --- 1  Ingrediente
                      Plato  N --- M  Horario de consumo (plato_horario)
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Longitudes de referencia (ajustables) según el diccionario de datos.
_LONG_NOMBRE = 100
_LONG_DESCRIPCION = 255


class Region(Base):
    """Región gastronómica del país (Andina, Caribe, Pacífica, Amazonía, ...)."""

    __tablename__ = "region"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(_LONG_DESCRIPCION))

    # Relación inversa (uno a muchos): platos pertenecientes a la región.
    platos: Mapped[list["Plato"]] = relationship(back_populates="region")

    def __repr__(self) -> str:
        return f"<Region id={self.id} nombre={self.nombre!r}>"


class Categoria(Base):
    """Categoría gastronómica del plato o del menú (sopas, carnes, postres, ...)."""

    __tablename__ = "categoria"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(_LONG_DESCRIPCION))

    # Relaciones inversas (uno a muchos).
    platos: Mapped[list["Plato"]] = relationship(back_populates="categoria")
    menus: Mapped[list["Menu"]] = relationship(back_populates="categoria")

    def __repr__(self) -> str:
        return f"<Categoria id={self.id} nombre={self.nombre!r}>"


class Plato(Base):
    """Plato que forma parte de un menú del restaurante."""

    __tablename__ = "plato"
    __table_args__ = (
        # Una promoción, si existe, debe ser más barata que el precio normal.
        CheckConstraint(
            "precio_promocional IS NULL OR precio_promocional < precio",
            name="ck_plato_precio_promocional_menor",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(
        String(_LONG_NOMBRE), nullable=False, index=True
    )  # índice: búsquedas por nombre
    descripcion: Mapped[Optional[str]] = mapped_column(String(_LONG_DESCRIPCION))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    precio_promocional: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2)
    )  # precio de la promoción activa (visible en la carta digital)
    foto_url: Mapped[Optional[str]] = mapped_column(String(_LONG_DESCRIPCION))
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="disponible"
    )  # valores previstos: "disponible" | "agotado"
    recomendado: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # destacado en la sección "Platos recomendados" de la carta digital

    # Llaves foráneas.
    id_categoria: Mapped[int] = mapped_column(
        ForeignKey("categoria.id"), nullable=False, index=True
    )
    id_region: Mapped[int] = mapped_column(
        ForeignKey("region.id"), nullable=False, index=True
    )

    # Relaciones (muchos a uno / uno a muchos).
    categoria: Mapped["Categoria"] = relationship(back_populates="platos")
    region: Mapped["Region"] = relationship(back_populates="platos")
    recetas: Mapped[list["Receta"]] = relationship(
        back_populates="plato", cascade="all, delete-orphan"
    )  # al borrar un plato se borran sus ingredientes asociados en receta
    horarios_asoc: Mapped[list["PlatoHorario"]] = relationship(
        back_populates="plato", cascade="all, delete-orphan"
    )  # al borrar o editar un plato se gestionan sus horarios en cascada

    # Vista de los horarios como lista de strings ("desayuno", "almuerzo",
    # "cena"): simplifica la serialización y la asignación desde la API.
    horarios = association_proxy(
        "horarios_asoc", "horario", creator=lambda h: PlatoHorario(horario=h)
    )

    def __repr__(self) -> str:
        return f"<Plato id={self.id} nombre={self.nombre!r} precio={self.precio}>"


class PlatoHorario(Base):
    """Horario de consumo de un plato (desayuno, almuerzo o cena).

    Asociación N:M entre plato y horario: un plato puede servirse en
    varios horarios y cada horario agrupa varios platos. La clave
    primaria es compuesta (id_plato, horario) para evitar repeticiones.
    """

    __tablename__ = "plato_horario"
    __table_args__ = (
        CheckConstraint(
            "horario IN ('desayuno', 'almuerzo', 'cena')",
            name="ck_plato_horario_valor",
        ),
    )

    id_plato: Mapped[int] = mapped_column(
        ForeignKey("plato.id", ondelete="CASCADE"), primary_key=True
    )
    horario: Mapped[str] = mapped_column(String(20), primary_key=True)

    # Relación (muchos a uno).
    plato: Mapped["Plato"] = relationship(back_populates="horarios_asoc")

    def __repr__(self) -> str:
        return f"<PlatoHorario id_plato={self.id_plato} horario={self.horario!r}>"


class Ingrediente(Base):
    """Insumo utilizado en la preparación de los platos."""

    __tablename__ = "ingrediente"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(_LONG_NOMBRE), nullable=False, unique=True)
    unidad_medida: Mapped[str] = mapped_column(String(30), nullable=False)  # kg, g, l, ml, unidades

    # Relación inversa: recetas en las que participa el ingrediente.
    recetas: Mapped[list["Receta"]] = relationship(
        back_populates="ingrediente", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Ingrediente id={self.id} nombre={self.nombre!r} unidad={self.unidad_medida!r}>"


class Receta(Base):
    """Asociación Plato-Ingrediente con la cantidad requerida.

    Representa la receta de un plato: qué ingredientes la componen y en
    qué cantidad. La clave primaria es compuesta (id_plato, id_ingrediente),
    de modo que un mismo ingrediente no se repita dentro de un plato.
    """

    __tablename__ = "receta"

    id_plato: Mapped[int] = mapped_column(
        ForeignKey("plato.id", ondelete="CASCADE"), primary_key=True
    )
    id_ingrediente: Mapped[int] = mapped_column(
        ForeignKey("ingrediente.id", ondelete="CASCADE"), primary_key=True
    )
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relaciones (muchos a uno).
    plato: Mapped["Plato"] = relationship(back_populates="recetas")
    ingrediente: Mapped["Ingrediente"] = relationship(back_populates="recetas")

    def __repr__(self) -> str:
        return (
            f"<Receta id_plato={self.id_plato} "
            f"id_ingrediente={self.id_ingrediente} cantidad={self.cantidad}>"
        )


class Menu(Base):
    """Carta digital por categoría con vigencia (rango de fechas)."""

    __tablename__ = "menu"
    __table_args__ = (
        # La vigencia debe ser un rango coherente de fechas.
        CheckConstraint(
            "fecha_fin >= fecha_inicio", name="ck_menu_fecha_fin_posterior"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(_LONG_NOMBRE), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20), nullable=False, default="inactivo"
    )  # valores: "activo" (carta publicada) | "inactivo" (borrador)

    # Llave foránea: el menú se construye por categoría.
    id_categoria: Mapped[int] = mapped_column(
        ForeignKey("categoria.id"), nullable=False, index=True
    )

    # Relación (muchos a uno).
    categoria: Mapped["Categoria"] = relationship(back_populates="menus")

    def __repr__(self) -> str:
        return f"<Menu id={self.id} nombre={self.nombre!r} {self.fecha_inicio} a {self.fecha_fin}>"
