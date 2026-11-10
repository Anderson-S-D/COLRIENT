"""Pruebas del módulo de Gestión de Platos (Sprint 1 de COLRIENT).

Cubre los cinco endpoints y el manejo de excepciones HTTP:
201/200 en éxito, 404 plato inexistente, 400 relaciones inválidas,
403 eliminación sin permiso de Gerente, 413/415 foto inválida y
422 datos inválidos.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.models import Categoria, Region

# Contenido binario mínimo para simular una imagen PNG en las subidas.
PNG_PRUEBA = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _registrar(client, semillas, **cambios) -> dict:
    """Registra un plato válido con datos únicos y devuelve su JSON."""
    id_categoria, id_region = semillas
    payload = {
        "nombre": f"Ajiaco-{uuid.uuid4().hex[:6]}",
        "descripcion": "Sopa típica bogotana",
        "precio": "18000.00",
        "id_categoria": id_categoria,
        "id_region": id_region,
    }
    payload.update(cambios)
    respuesta = client.post("/api/v1/platos", json=payload)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- POST /api/v1/platos ---------------------------------------------------

def test_registrar_plato(client, semillas):
    plato = _registrar(client, semillas)
    assert plato["id"] > 0
    assert plato["estado"] == "disponible"  # valor por defecto
    assert plato["categoria"]["nombre"].startswith("Sopas")
    assert plato["region"]["nombre"].startswith("Andina")


def test_registrar_plato_categoria_inexistente(client, semillas):
    id_categoria, id_region = semillas
    respuesta = client.post(
        "/api/v1/platos",
        json={
            "nombre": "Plato huérfano",
            "precio": "1000.00",
            "id_categoria": 99999,
            "id_region": id_region,
        },
    )
    assert respuesta.status_code == 400
    assert "categoría" in respuesta.json()["detail"]


def test_registrar_plato_datos_invalidos(client, semillas):
    assert _registrar_raw(client, semillas, precio="-5").status_code == 422
    assert _registrar_raw(client, semillas, nombre="").status_code == 422
    assert _registrar_raw(client, semillas, id_categoria=0).status_code == 422


def _registrar_raw(client, semillas, **cambios):
    id_categoria, id_region = semillas
    payload = {
        "nombre": f"X-{uuid.uuid4().hex[:6]}",
        "precio": "1000.00",
        "id_categoria": id_categoria,
        "id_region": id_region,
    }
    payload.update(cambios)
    return client.post("/api/v1/platos", json=payload)


# --- GET /api/v1/platos ----------------------------------------------------

def test_listar_y_filtrar(client, semillas):
    id_categoria, _id_region = semillas

    db = SessionLocal()
    otra_categoria = Categoria(nombre=f"Postres-{uuid.uuid4().hex[:6]}")
    otra_region = Region(nombre=f"Caribe-{uuid.uuid4().hex[:6]}")
    db.add_all([otra_categoria, otra_region])
    db.commit()
    db.refresh(otra_categoria)
    db.refresh(otra_region)
    db.close()

    plato_a = _registrar(client, semillas)  # pertenece a la categoría semilla
    plato_b = _registrar(
        client, semillas, nombre=f"Bandeja-{uuid.uuid4().hex[:6]}",
        id_categoria=otra_categoria.id, id_region=otra_region.id,
    )

    lista = client.get("/api/v1/platos").json()
    nombres = [p["nombre"] for p in lista]
    assert plato_a["nombre"] in nombres and plato_b["nombre"] in nombres

    por_categoria = client.get(
        "/api/v1/platos", params={"categoria": otra_categoria.id}
    ).json()
    assert {p["nombre"] for p in por_categoria} == {plato_b["nombre"]}

    por_region = client.get(
        "/api/v1/platos", params={"region": plato_a["id_region"]}
    ).json()
    assert plato_a["nombre"] in {p["nombre"] for p in por_region}
    assert plato_b["nombre"] not in {p["nombre"] for p in por_region}

    por_nombre = client.get(
        "/api/v1/platos", params={"nombre": plato_b["nombre"][:10]}
    ).json()
    assert {p["nombre"] for p in por_nombre} == {plato_b["nombre"]}


# --- PUT /api/v1/platos/{id} -----------------------------------------------

def test_editar_plato(client, semillas):
    plato = _registrar(client, semillas)
    respuesta = client.put(
        f"/api/v1/platos/{plato['id']}",
        json={"precio": "19500.50", "descripcion": "Receta actualizada"},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["precio"] == "19500.50"  # Pydantic serializa Decimal a texto
    assert cuerpo["descripcion"] == "Receta actualizada"
    assert cuerpo["nombre"] == plato["nombre"]  # campo no enviado, sin cambio


def test_editar_plato_sin_campos(client, semillas):
    plato = _registrar(client, semillas)
    respuesta = client.put(f"/api/v1/platos/{plato['id']}", json={})
    assert respuesta.status_code == 400


def test_editar_plato_inexistente(client):
    respuesta = client.put("/api/v1/platos/999999", json={"precio": "1.00"})
    assert respuesta.status_code == 404


def test_editar_plato_region_invalida(client, semillas):
    plato = _registrar(client, semillas)
    respuesta = client.put(
        f"/api/v1/platos/{plato['id']}", json={"id_region": 999999}
    )
    assert respuesta.status_code == 400
    assert "región" in respuesta.json()["detail"]


# --- DELETE /api/v1/platos/{id} ----------------------------------------------

def test_eliminar_plato_requiere_gerente(client, semillas):
    plato = _registrar(client, semillas)
    url = f"/api/v1/platos/{plato['id']}"

    assert client.delete(url).status_code == 403  # sin cabecera de rol
    assert client.delete(url, headers={"X-Rol": "cocinero"}).status_code == 403

    # El plato sigue existiendo tras los intentos denegados.
    nombres = [p["nombre"] for p in client.get("/api/v1/platos").json()]
    assert plato["nombre"] in nombres


def test_eliminar_plato_como_gerente(client, semillas):
    plato = _registrar(client, semillas)
    url = f"/api/v1/platos/{plato['id']}"

    respuesta = client.delete(url, headers={"X-Rol": "gerente"})
    assert respuesta.status_code == 204

    nombres = [p["nombre"] for p in client.get("/api/v1/platos").json()]
    assert plato["nombre"] not in nombres
    assert client.delete(url, headers={"X-Rol": "gerente"}).status_code == 404


# --- POST /api/v1/platos/{id}/foto -------------------------------------------

def test_subir_foto(client, semillas):
    plato = _registrar(client, semillas)
    respuesta = client.post(
        f"/api/v1/platos/{plato['id']}/foto",
        files={"foto": ("plato.png", PNG_PRUEBA, "image/png")},
    )
    assert respuesta.status_code == 200, respuesta.text
    foto_url = respuesta.json()["foto_url"]
    assert foto_url.startswith("/uploads/platos/")

    # El archivo queda servido públicamente por el servidor.
    assert client.get(foto_url).status_code == 200

    # Y queda asociado al plato en la base de datos.
    plato_actualizado = next(
        p for p in client.get("/api/v1/platos").json() if p["id"] == plato["id"]
    )
    assert plato_actualizado["foto_url"] == foto_url


def test_subir_foto_formato_invalido(client, semillas):
    plato = _registrar(client, semillas)
    respuesta = client.post(
        f"/api/v1/platos/{plato['id']}/foto",
        files={"foto": ("notas.txt", b"texto plano", "text/plain")},
    )
    assert respuesta.status_code == 415


def test_subir_foto_plato_inexistente(client):
    respuesta = client.post(
        "/api/v1/platos/999999/foto",
        files={"foto": ("plato.png", PNG_PRUEBA, "image/png")},
    )
    assert respuesta.status_code == 404


# --- Horarios, promociones y recomendados (interfaz del cliente) -------------

def test_registrar_plato_con_horarios_promocion(client, semillas):
    plato = _registrar(
        client,
        semillas,
        horarios=["Desayuno", "almuerzo", "almuerzo"],  # mayúsculas y duplicado
        recomendado=True,
        precio_promocional="12000.00",
    )
    assert plato["horarios"] == ["desayuno", "almuerzo"]  # normalizado
    assert plato["recomendado"] is True
    assert plato["precio_promocional"] == "12000.00"


def test_registrar_plato_horario_invalido(client, semillas):
    assert (
        _registrar_raw(client, semillas, horarios=["merienda"]).status_code == 422
    )


def test_registrar_plato_promocion_invalida(client, semillas):
    # La promoción no puede ser igual o mayor que el precio normal.
    assert (
        _registrar_raw(client, semillas, precio_promocional="18000.00").status_code
        == 422
    )


def test_filtrar_por_horario(client, semillas):
    almuerzo = _registrar(client, semillas, horarios=["almuerzo"])
    todo_el_dia = _registrar(client, semillas, horarios=["desayuno", "cena"])

    por_horario = client.get("/api/v1/platos", params={"horario": "almuerzo"}).json()
    nombres = {p["nombre"] for p in por_horario}
    assert almuerzo["nombre"] in nombres
    assert todo_el_dia["nombre"] not in nombres

    por_cena = client.get("/api/v1/platos", params={"horario": "cena"}).json()
    assert todo_el_dia["nombre"] in {p["nombre"] for p in por_cena}

    # Horario inexistente en el patrón → 422.
    assert (
        client.get("/api/v1/platos", params={"horario": "brindis"}).status_code == 422
    )


def test_filtrar_recomendados_y_promociones(client, semillas):
    destacado = _registrar(client, semillas, recomendado=True)
    promocion = _registrar(client, semillas, precio_promocional="9000.00")
    normal = _registrar(client, semillas)

    recomendados = client.get(
        "/api/v1/platos", params={"recomendado": True}
    ).json()
    assert destacado["nombre"] in {p["nombre"] for p in recomendados}
    assert normal["nombre"] not in {p["nombre"] for p in recomendados}

    en_promo = client.get("/api/v1/platos", params={"promocion": True}).json()
    assert promocion["nombre"] in {p["nombre"] for p in en_promo}
    assert normal["nombre"] not in {p["nombre"] for p in en_promo}

    sin_promo = client.get("/api/v1/platos", params={"promocion": False}).json()
    nombres = {p["nombre"] for p in sin_promo}
    assert promocion["nombre"] not in nombres
    assert normal["nombre"] in nombres


def test_editar_horarios_promocion_y_recomendado(client, semillas):
    plato = _registrar(client, semillas, horarios=["desayuno"], precio_promocional="15000.00")
    url = f"/api/v1/platos/{plato['id']}"

    respuesta = client.put(
        url,
        json={"horarios": ["almuerzo", "cena"], "recomendado": True},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["horarios"] == ["almuerzo", "cena"]  # reemplaza el conjunto
    assert cuerpo["recomendado"] is True
    assert cuerpo["precio_promocional"] == "15000.00"

    # null explícito retira la promoción.
    retirada = client.put(url, json={"precio_promocional": None})
    assert retirada.json()["precio_promocional"] is None

    # [] vacía retira los horarios.
    sin_horarios = client.put(url, json={"horarios": []})
    assert sin_horarios.json()["horarios"] == []


def test_editar_promocion_incoherente(client, semillas):
    plato = _registrar(client, semillas)  # precio 18000
    respuesta = client.put(
        f"/api/v1/platos/{plato['id']}", json={"precio_promocional": "25000.00"}
    )
    assert respuesta.status_code == 400
    assert "promocional" in respuesta.json()["detail"]

    # La promoción tampoco puede quedar por encima de un precio rebajado.
    con_promo = _registrar(client, semillas, precio_promocional="10000.00")
    respuesta2 = client.put(
        f"/api/v1/platos/{con_promo['id']}", json={"precio": "9000.00"}
    )
    assert respuesta2.status_code == 400
