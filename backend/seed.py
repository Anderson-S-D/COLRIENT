#!/usr/bin/env python3
"""
COLRIENT — Datos de prueba.

Pobla la base de datos con un catálogo completo de demostración para
el restaurante "La cabaña de Álvaro":

- 5 categorías y 4 regiones gastronómicas.
- 45 ingredientes con su unidad de medida.
- 19 platos típicos colombianos con horarios de consumo, 5
  recomendados, 4 promociones y 1 agotado (para apreciar todos los
  estados de la carta digital).
- 18 platos con receta (80 asociaciones plato-ingrediente con cantidad;
  un plato queda deliberadamente sin receta para ver el estado vacío).
- 3 menús: la carta del mes anterior (histórico), la del mes en curso
  (PUBLICADA → la que muestra la carta digital) y la del mes siguiente
  (borrador).

Las fechas de los menús se calculan respecto a la fecha actual para
que la carta vigente siempre esté dentro de su rango de vigencia.

Uso (desde backend/, con el entorno virtual activo):
    python seed.py            → puebla la base si aún no hay platos
    python seed.py --reset    → borra todo y repuebla desde cero

Nota: los tests usan una base aislada (tests/conftest.py), por lo que
este poblado no interfiere con la suite automatizada.
"""

import argparse
from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, init_db
from app.models import (
    Categoria,
    Ingrediente,
    Menu,
    Plato,
    Receta,
    Region,
)

MESES_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

# ---------------------------------------------------------------------------
# Catálogos de referencia
# ---------------------------------------------------------------------------

CATEGORIAS = [
    ("Sopas", "Platos caldosos y sopas tradicionales del país."),
    ("Carnes", "Platos fuertes de res, cerdo, pollo y mar."),
    ("Postres", "Dulces tradicionales colombianos."),
    ("Bebidas", "Bebidas calientes y frías de la casa."),
    ("Acompañantes", "Guarniciones y entradas para compartir."),
]

REGIONES = [
    ("Andina", "Altiplano cundiboyacense y paisa: papa, maíz y caldos."),
    ("Caribe", "Costa norte: sabores del mar, coco y plátano."),
    ("Pacífica", "Litoral del Pacífico: mariscos y leche de coco."),
    ("Llanera", "Sabanas del oriente: maíz tierno y quesos llaneros."),
]

# ---------------------------------------------------------------------------
# Ingredientes: (nombre, unidad_medida)
# ---------------------------------------------------------------------------

INGREDIENTES = [
    ("Papa criolla", "kg"),
    ("Papa pastusa", "kg"),
    ("Papa sabanera", "kg"),
    ("Pechuga de pollo", "kg"),
    ("Gallina campesina", "kg"),
    ("Panceta de cerdo", "kg"),
    ("Estómago de res", "kg"),
    ("Carne de res desmechada", "kg"),
    ("Chicharrón", "kg"),
    ("Chorizo antioqueño", "unidades"),
    ("Huevo", "unidades"),
    ("Pargo rojo", "kg"),
    ("Camarón", "kg"),
    ("Mazorca dulce", "unidades"),
    ("Plátano maduro", "unidades"),
    ("Plátano verde", "unidades"),
    ("Yuca", "kg"),
    ("Aguacate", "unidades"),
    ("Arroz blanco", "kg"),
    ("Frijol cargamanto", "kg"),
    ("Arveja seca", "kg"),
    ("Maíz tierno", "kg"),
    ("Leche entera", "l"),
    ("Crema de leche", "ml"),
    ("Leche de coco", "ml"),
    ("Panela", "kg"),
    ("Queso campesino", "kg"),
    ("Queso guayánes", "kg"),
    ("Brevas", "unidades"),
    ("Arequipe", "kg"),
    ("Chocolate en tabla", "unidades"),
    ("Café en grano", "kg"),
    ("Corozo", "kg"),
    ("Almojábana", "unidades"),
    ("Arepa", "unidades"),
    ("Guascas", "g"),
    ("Cilantro", "g"),
    ("Cebolla larga", "g"),
    ("Tomate", "kg"),
    ("Ajo", "g"),
    ("Alcaparras", "g"),
    ("Canela", "g"),
    ("Comino", "g"),
    ("Pimienta", "g"),
    ("Sal", "g"),
]

# ---------------------------------------------------------------------------
# Platos: (nombre, descripcion, precio, categoria, region, horarios,
#          recomendado, precio_promocional, estado)
# ---------------------------------------------------------------------------

PLATOS_DEMO = [
    ("Ajiaco santafereño",
     "Sopa de pollo con tres tipos de papa, mazorca tierna y guascas, "
     "acompañada de crema y alcaparras.",
     18000, "Sopas", "Andina", ["almuerzo", "cena"], True, 15000, "disponible"),
    ("Sancocho de gallina",
     "Sancocho campesino de gallina con yuca, plátano, mazorca y cilantro fresco.",
     22000, "Sopas", "Andina", ["almuerzo"], False, None, "disponible"),
    ("Mondongo santandereano",
     "Estómago de res guisado a fuego lento con papa, arveja y aliños.",
     19500, "Sopas", "Andina", ["almuerzo", "cena"], False, None, "disponible"),
    ("Cazuela de mariscos",
     "Cazuela de camarones y pescado en caldo de coco con verduras del litoral.",
     28000, "Sopas", "Caribe", ["cena"], False, None, "disponible"),
    ("Calentado bogotano",
     "Arroz, frijoles, carne desmechada, huevo frito y arepa: el desayuno "
     "capitalino por excelencia.",
     14000, "Carnes", "Andina", ["desayuno"], True, None, "disponible"),
    ("Bandeja paisa",
     "Frijoles, chicharrón, carne, chorizo, arroz, huevo, aguacate y plátano "
     "maduro: la reina de la mesa antioqueña.",
     32000, "Carnes", "Andina", ["almuerzo", "cena"], True, None, "disponible"),
    ("Lechona tolimense",
     "Cerdo relleno de arroz y arveja: crocante por fuera, jugoso por dentro.",
     26000, "Carnes", "Andina", ["almuerzo", "cena"], False, None, "disponible"),
    ("Pargo rojo frito",
     "Pargo rojo dorado con patacón, arroz de coco y ensalada fresca.",
     28000, "Carnes", "Caribe", ["almuerzo", "cena"], False, 23000, "disponible"),
    ("Encocado de camarones",
     "Camarones guisados en leche de coco con arroz blanco: sazón del Pacífico.",
     26500, "Carnes", "Pacífica", ["almuerzo", "cena"], True, None, "disponible"),
    ("Hormigas culonas",
     "Delicatés santandereana: hormigas reinas tostadas con sal, crujientes "
     "y únicas en el mundo.",
     15000, "Carnes", "Andina", ["cena"], False, None, "disponible"),
    ("Tamal tolimense",
     "Tamal de arroz con pollo y cerdo, envuelto en hoja de plátano.",
     11000, "Acompañantes", "Andina", ["desayuno"], False, None, "agotado"),
    ("Patacón con hogao",
     "Patacón de plátano verde cubierto con hogao de tomate y cebolla larga.",
     6000, "Acompañantes", "Caribe", ["almuerzo", "cena"], False, None, "disponible"),
    ("Arroz con coco",
     "Arroz dulce de la costa con leche de coco, compañero del pescado frito.",
     7000, "Acompañantes", "Caribe", ["almuerzo", "cena"], False, None, "disponible"),
    ("Cachapa llanera",
     "Tortilla de maíz tierno con queso guayánes, dulce y cremosa.",
     7500, "Acompañantes", "Llanera", ["desayuno", "cena"], False, None, "disponible"),
    ("Postre de natas",
     "Dulce tradicional de leche cuajada con panela y un toque de canela.",
     9000, "Postres", "Andina", ["almuerzo", "cena"], False, 6500, "disponible"),
    ("Brevas con arequipe",
     "Brevas caladas en almíbar acompañadas de arequipe y queso campesino.",
     8500, "Postres", "Andina", ["cena"], False, None, "disponible"),
    ("Chocolate completo",
     "Chocolate caliente con queso, almojábana y pan: el desayuno de la casa.",
     12000, "Bebidas", "Andina", ["desayuno"], True, None, "disponible"),
    ("Café de origen",
     "Café colombiano de origen, tostado y molido; se sirve en todos los horarios.",
     4500, "Bebidas", "Andina", ["desayuno", "almuerzo", "cena"], False, None, "disponible"),
    ("Jugo de corozo",
     "Bebida refrescante de la costa Caribe, dulce y ligeramente ácida.",
     8000, "Bebidas", "Caribe", ["desayuno", "almuerzo"], False, 5000, "disponible"),
]

# ---------------------------------------------------------------------------
# Recetas: nombre del plato → [(ingrediente, cantidad), ...]
# Nota: "Hormigas culonas" queda sin receta para mostrar el estado vacío.
# ---------------------------------------------------------------------------

RECETAS = {
    "Ajiaco santafereño": [
        ("Papa criolla", 1.5), ("Papa pastusa", 1), ("Papa sabanera", 0.8),
        ("Pechuga de pollo", 0.8), ("Mazorca dulce", 2), ("Guascas", 15),
        ("Crema de leche", 200), ("Alcaparras", 30),
    ],
    "Sancocho de gallina": [
        ("Gallina campesina", 1.5), ("Yuca", 1), ("Plátano verde", 2),
        ("Mazorca dulce", 2), ("Cilantro", 15), ("Cebolla larga", 60),
    ],
    "Mondongo santandereano": [
        ("Estómago de res", 1.5), ("Papa pastusa", 1), ("Arveja seca", 0.3),
        ("Cebolla larga", 50), ("Comino", 5),
    ],
    "Cazuela de mariscos": [
        ("Camarón", 0.4), ("Pargo rojo", 0.5), ("Leche de coco", 300),
        ("Tomate", 0.2), ("Cebolla larga", 40), ("Cilantro", 10),
    ],
    "Calentado bogotano": [
        ("Arroz blanco", 0.3), ("Frijol cargamanto", 0.3),
        ("Carne de res desmechada", 0.25), ("Huevo", 1), ("Arepa", 1),
    ],
    "Bandeja paisa": [
        ("Frijol cargamanto", 1), ("Chicharrón", 0.4),
        ("Chorizo antioqueño", 2), ("Carne de res desmechada", 0.3),
        ("Arroz blanco", 0.5), ("Huevo", 2), ("Aguacate", 1),
        ("Plátano maduro", 1),
    ],
    "Lechona tolimense": [
        ("Panceta de cerdo", 3), ("Arroz blanco", 2), ("Arveja seca", 0.5),
        ("Comino", 5), ("Sal", 20),
    ],
    "Pargo rojo frito": [
        ("Pargo rojo", 0.8), ("Plátano verde", 2), ("Arroz blanco", 0.3),
        ("Ajo", 15),
    ],
    "Encocado de camarones": [
        ("Camarón", 0.6), ("Leche de coco", 400), ("Arroz blanco", 0.3),
        ("Cebolla larga", 50), ("Tomate", 0.2), ("Ajo", 10), ("Pimienta", 2),
    ],
    "Tamal tolimense": [
        ("Arroz blanco", 1), ("Pechuga de pollo", 0.5),
        ("Panceta de cerdo", 0.5), ("Arveja seca", 0.2),
    ],
    "Patacón con hogao": [
        ("Plátano verde", 2), ("Tomate", 0.3), ("Cebolla larga", 60), ("Ajo", 5),
    ],
    "Arroz con coco": [
        ("Arroz blanco", 0.5), ("Leche de coco", 500), ("Panela", 0.1),
    ],
    "Cachapa llanera": [
        ("Maíz tierno", 1), ("Queso guayánes", 0.3),
    ],
    "Postre de natas": [
        ("Leche entera", 2), ("Panela", 0.4), ("Canela", 5),
    ],
    "Brevas con arequipe": [
        ("Brevas", 8), ("Arequipe", 0.3), ("Queso campesino", 0.15),
    ],
    "Chocolate completo": [
        ("Chocolate en tabla", 2), ("Leche entera", 1),
        ("Queso campesino", 0.2), ("Almojábana", 2),
    ],
    "Café de origen": [
        ("Café en grano", 0.06),
    ],
    "Jugo de corozo": [
        ("Corozo", 0.5), ("Panela", 0.1),
    ],
}


# ---------------------------------------------------------------------------
# Ayudas de fecha (menús con vigencia relativa a hoy)
# ---------------------------------------------------------------------------

def _mes_anterior(d: date) -> date:
    """Primer día del mes anterior al de la fecha d."""
    return date(d.year - 1, 12, 1) if d.month == 1 else date(d.year, d.month - 1, 1)


def _mes_siguiente(d: date) -> date:
    """Primer día del mes siguiente al de la fecha d."""
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def _rango_del_mes(d: date) -> tuple[date, date]:
    """Rango (primer día, último día) del mes al que pertenece d."""
    return d.replace(day=1), d.replace(day=monthrange(d.year, d.month)[1])


def _menus_de_demostracion(categorias: dict[str, Categoria]) -> list[Menu]:
    """Carta del mes anterior (histórico), del mes en curso (publicada)
    y del mes siguiente (borrador)."""
    hoy = date.today()
    menus: list[Menu] = []
    for referencia, categoria, estado in (
        (_mes_anterior(hoy), "Sopas", "inactivo"),      # histórico
        (hoy, "Carnes", "activo"),                      # carta vigente publicada
        (_mes_siguiente(hoy), "Postres", "inactivo"),   # borrador
    ):
        inicio, fin = _rango_del_mes(referencia)
        menus.append(Menu(
            nombre=f"Carta de {MESES_ES[referencia.month - 1]}",
            fecha_inicio=inicio,
            fecha_fin=fin,
            estado=estado,
            id_categoria=categorias[categoria].id,
        ))
    return menus


# ---------------------------------------------------------------------------
# Poblado
# ---------------------------------------------------------------------------

def _verificar_referencias() -> None:
    """Comprueba la coherencia interna de los datos declarados."""
    nombres_categorias = {c[0] for c in CATEGORIAS}
    nombres_regiones = {r[0] for r in REGIONES}
    nombres_ingredientes = {i[0] for i in INGREDIENTES}
    nombres_platos = {p[0] for p in PLATOS_DEMO}

    for plato in PLATOS_DEMO:
        assert plato[3] in nombres_categorias, f"Categoría inexistente: {plato[3]}"
        assert plato[4] in nombres_regiones, f"Región inexistente: {plato[4]}"
    for nombre_plato, items in RECETAS.items():
        assert nombre_plato in nombres_platos, f"Plato sin declarar: {nombre_plato}"
        for nombre_ingrediente, _ in items:
            assert nombre_ingrediente in nombres_ingredientes, (
                f"Ingrediente sin declarar: {nombre_ingrediente}"
            )


def poblar(db: Session) -> dict[str, int]:
    """Crea todos los registros y devuelve un resumen con los conteos."""
    _verificar_referencias()

    # Catálogos: categorías y regiones.
    categorias = {
        nombre: Categoria(nombre=nombre, descripcion=desc)
        for nombre, desc in CATEGORIAS
    }
    regiones = {
        nombre: Region(nombre=nombre, descripcion=desc)
        for nombre, desc in REGIONES
    }
    db.add_all(categorias.values())
    db.add_all(regiones.values())
    db.flush()  # asigna ids para las llaves foráneas

    # Ingredientes (el nombre es único).
    ingredientes = {
        nombre: Ingrediente(nombre=nombre, unidad_medida=unidad)
        for nombre, unidad in INGREDIENTES
    }
    db.add_all(ingredientes.values())
    db.flush()

    # Platos con sus horarios, promociones y recomendados.
    platos: dict[str, Plato] = {}
    for (nombre, descripcion, precio, categoria, region,
         horarios, recomendado, promocion, estado) in PLATOS_DEMO:
        plato = Plato(
            nombre=nombre,
            descripcion=descripcion,
            precio=Decimal(precio),
            precio_promocional=Decimal(promocion) if promocion is not None else None,
            estado=estado,
            recomendado=recomendado,
            id_categoria=categorias[categoria].id,
            id_region=regiones[region].id,
        )
        plato.horarios = horarios  # association proxy → filas plato_horario
        db.add(plato)
        platos[nombre] = plato
    db.flush()

    # Recetas: qué ingredientes componen cada plato y en qué cantidad.
    recetas = [
        Receta(
            id_plato=platos[nombre_plato].id,
            id_ingrediente=ingredientes[nombre_ingrediente].id,
            cantidad=Decimal(str(cantidad)),
        )
        for nombre_plato, items in RECETAS.items()
        for nombre_ingrediente, cantidad in items
    ]
    db.add_all(recetas)

    # Menús (uno publicado como carta digital vigente).
    db.add_all(_menus_de_demostracion(categorias))

    db.commit()

    return {
        "categorias": len(categorias),
        "regiones": len(regiones),
        "ingredientes": len(ingredientes),
        "platos": len(platos),
        "recomendados": sum(1 for p in PLATOS_DEMO if p[6]),
        "promociones": sum(1 for p in PLATOS_DEMO if p[7] is not None),
        "agotados": sum(1 for p in PLATOS_DEMO if p[8] == "agotado"),
        "recetas": len(recetas),
        "menus": 3,
    }


def _imprimir_resumen(r: dict[str, int]) -> None:
    print("✔ Datos de prueba cargados")
    print(f"   Categorías: {r['categorias']} · Regiones: {r['regiones']}")
    print(f"   Platos: {r['platos']} (recomendados: {r['recomendados']}, "
          f"promociones: {r['promociones']}, agotados: {r['agotados']})")
    print(f"   Ingredientes: {r['ingredientes']} · Recetas: {r['recetas']}")
    print(f"   Menús: {r['menus']} (uno publicado como carta vigente)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Puebla la base de datos de COLRIENT con datos de prueba."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="borra todas las tablas y vuelve a poblar desde cero",
    )
    args = parser.parse_args()

    if args.reset:
        Base.metadata.drop_all(bind=engine)
        print("→ Tablas eliminadas (modo --reset).")

    init_db()
    db = SessionLocal()
    try:
        if not args.reset and db.scalar(select(func.count()).select_from(Plato)):
            print("La base de datos ya contiene platos; use --reset para repoblarla.")
            return
        _imprimir_resumen(poblar(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
