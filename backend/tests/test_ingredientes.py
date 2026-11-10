"""Pruebas del módulo de Ingredientes y Recetas (Sprint 2 de COLRIENT).

Cubre: registro sin duplicados, asociación a receta, consulta de la
receta completa y eliminación/sustitución de ingredientes.
"""

import uuid

from app.database import SessionLocal
from app.models import Categoria


def _registrar_plato(client, semillas) -> dict:
    id_categoria, id_region = semillas
    respuesta = client.post(
        "/api/v1/platos",
        json={
            "nombre": f"Plato-{uuid.uuid4().hex[:6]}",
            "precio": "12000.00",
            "id_categoria": id_categoria,
            "id_region": id_region,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _registrar_ingrediente(client, nombre=None, unidad="kg") -> dict:
    respuesta = client.post(
        "/api/v1/ingredientes",
        json={"nombre": nombre or f"Insumo-{uuid.uuid4().hex[:6]}", "unidad_medida": unidad},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- POST /api/v1/ingredientes ------------------------------------------------

def test_registrar_ingrediente(client):
    ingrediente = _registrar_ingrediente(client, nombre="Papa criolla")
    assert ingrediente["id"] > 0
    assert ingrediente["unidad_medida"] == "kg"


def test_registrar_ingrediente_duplicado(client):
    _registrar_ingrediente(client, nombre="Pollo")
    respuesta = client.post(
        "/api/v1/ingredientes",
        json={"nombre": "pollo", "unidad_medida": "kg"},  # difiere en mayúsculas
    )
    assert respuesta.status_code == 409
    assert "ya existe" in respuesta.json()["detail"].lower()


def test_listar_ingredientes(client):
    ingrediente = _registrar_ingrediente(client)
    lista = client.get("/api/v1/ingredientes").json()
    assert any(i["id"] == ingrediente["id"] for i in lista)


# --- POST /api/v1/platos/{id}/ingredientes -----------------------------------

def test_asociar_ingrediente(client, semillas):
    plato = _registrar_plato(client, semillas)
    ingrediente = _registrar_ingrediente(client)

    respuesta = client.post(
        f"/api/v1/platos/{plato['id']}/ingredientes",
        json={"id_ingrediente": ingrediente["id"], "cantidad": 0.5},
    )
    assert respuesta.status_code == 201, respuesta.text
    receta = respuesta.json()
    assert receta["id"] == plato["id"]
    assert receta["recetas"][0]["cantidad"] == "0.50"
    assert receta["recetas"][0]["ingrediente"]["nombre"] == ingrediente["nombre"]


def test_asociar_ingrediente_plato_inexistente(client):
    ingrediente = _registrar_ingrediente(client)
    respuesta = client.post(
        "/api/v1/platos/999999/ingredientes",
        json={"id_ingrediente": ingrediente["id"], "cantidad": 1},
    )
    assert respuesta.status_code == 404


def test_asociar_ingrediente_inexistente(client, semillas):
    plato = _registrar_plato(client, semillas)
    respuesta = client.post(
        f"/api/v1/platos/{plato['id']}/ingredientes",
        json={"id_ingrediente": 999999, "cantidad": 1},
    )
    assert respuesta.status_code == 400


def test_asociar_ingrediente_repetido(client, semillas):
    plato = _registrar_plato(client, semillas)
    ingrediente = _registrar_ingrediente(client)
    body = {"id_ingrediente": ingrediente["id"], "cantidad": 1}

    assert client.post(f"/api/v1/platos/{plato['id']}/ingredientes", json=body).status_code == 201
    repetido = client.post(f"/api/v1/platos/{plato['id']}/ingredientes", json=body)
    assert repetido.status_code == 409
    assert "sustituirlo" in repetido.json()["detail"]


# --- GET /api/v1/platos/{id}/receta -------------------------------------------

def test_consultar_receta(client, semillas):
    plato = _registrar_plato(client, semillas)
    a = _registrar_ingrediente(client)
    b = _registrar_ingrediente(client)
    for id_ingrediente, cantidad in ((a["id"], 0.5), (b["id"], 2)):
        assert (
            client.post(
                f"/api/v1/platos/{plato['id']}/ingredientes",
                json={"id_ingrediente": id_ingrediente, "cantidad": cantidad},
            ).status_code
            == 201
        )

    receta = client.get(f"/api/v1/platos/{plato['id']}/receta")
    assert receta.status_code == 200
    cuerpo = receta.json()
    assert cuerpo["nombre"] == plato["nombre"]
    assert {i["id_ingrediente"] for i in cuerpo["recetas"]} == {a["id"], b["id"]}


def test_consultar_receta_vacia(client, semillas):
    plato = _registrar_plato(client, semillas)
    receta = client.get(f"/api/v1/platos/{plato['id']}/receta")
    assert receta.status_code == 200
    assert receta.json()["recetas"] == []


def test_consultar_receta_plato_inexistente(client):
    assert client.get("/api/v1/platos/999999/receta").status_code == 404


# --- DELETE .../ingredientes/{id_ingrediente} -----------------------------------

def test_eliminar_y_sustituir_ingrediente(client, semillas):
    plato = _registrar_plato(client, semillas)
    original = _registrar_ingrediente(client)
    sustituto = _registrar_ingrediente(client)
    url_receta = f"/api/v1/platos/{plato['id']}/ingredientes"

    client.post(url_receta, json={"id_ingrediente": original["id"], "cantidad": 1})

    # Eliminar el ingrediente de la receta.
    respuesta = client.delete(f"{url_receta}/{original['id']}")
    assert respuesta.status_code == 204
    receta = client.get(f"/api/v1/platos/{plato['id']}/receta").json()
    assert receta["recetas"] == []

    # Sustitución: ahora el nuevo ingrediente puede asociarse sin conflicto.
    assert (
        client.post(url_receta, json={"id_ingrediente": sustituto["id"], "cantidad": 3}).status_code
        == 201
    )


def test_eliminar_ingrediente_no_asociado(client, semillas):
    plato = _registrar_plato(client, semillas)
    ingrediente = _registrar_ingrediente(client)
    respuesta = client.delete(
        f"/api/v1/platos/{plato['id']}/ingredientes/{ingrediente['id']}"
    )
    assert respuesta.status_code == 404
    assert "no está asociado" in respuesta.json()["detail"]


def test_eliminar_ingrediente_plato_inexistente(client):
    ingrediente = _registrar_ingrediente(client)
    respuesta = client.delete(f"/api/v1/platos/999999/ingredientes/{ingrediente['id']}")
    assert respuesta.status_code == 404


# --- Catálogos (usados por los formularios del frontend) ------------------------

def test_catalogos(client, semillas):
    id_categoria, _id_region = semillas
    categorias = client.get("/api/v1/categorias").json()
    regiones = client.get("/api/v1/regiones").json()
    assert any(c["id"] == id_categoria for c in categorias)
    assert len(regiones) >= 1
