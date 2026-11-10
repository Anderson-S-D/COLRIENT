"""Pruebas del módulo de Gestión del Menú (Sprint 2 de COLRIENT).

Cubre: creación con vigencia, histórico con filtros y publicación de
la carta digital (un solo menú activo a la vez).
"""

import uuid
from datetime import date, timedelta

from app.database import SessionLocal
from app.models import Categoria

HOY = date.today()


def _registrar_menu(client, id_categoria, **cambios) -> dict:
    payload = {
        "nombre": f"Menú-{uuid.uuid4().hex[:6]}",
        "fecha_inicio": str(HOY),
        "fecha_fin": str(HOY + timedelta(days=15)),
        "id_categoria": id_categoria,
    }
    payload.update(cambios)
    respuesta = client.post("/api/v1/menus", json=payload)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- POST /api/v1/menus ---------------------------------------------------------

def test_crear_menu(client, semillas):
    id_categoria, _ = semillas
    menu = _registrar_menu(client, id_categoria)
    assert menu["id"] > 0
    assert menu["estado"] == "inactivo"  # se crea como borrador
    assert menu["categoria"]["id"] == id_categoria


def test_crear_menu_categoria_inexistente(client):
    respuesta = client.post(
        "/api/v1/menus",
        json={"nombre": "Menú huérfano", "fecha_inicio": str(HOY), "fecha_fin": str(HOY), "id_categoria": 999999},
    )
    assert respuesta.status_code == 400


def test_crear_menu_fechas_invertidas(client, semillas):
    id_categoria, _ = semillas
    respuesta = client.post(
        "/api/v1/menus",
        json={
            "nombre": "Menú inválido",
            "fecha_inicio": str(HOY + timedelta(days=10)),
            "fecha_fin": str(HOY),
            "id_categoria": id_categoria,
        },
    )
    assert respuesta.status_code == 400
    assert "posterior" in respuesta.json()["detail"]


def test_crear_menu_datos_invalidos(client, semillas):
    id_categoria, _ = semillas
    respuesta = client.post(
        "/api/v1/menus",
        json={"nombre": "X", "fecha_inicio": "no-fecha", "fecha_fin": str(HOY), "id_categoria": id_categoria},
    )
    assert respuesta.status_code == 422


# --- GET /api/v1/menus/historico --------------------------------------------------

def test_historico_ordenado_y_filtrado(client, semillas):
    id_categoria, _ = semillas

    db = SessionLocal()
    otra_categoria = Categoria(nombre=f"Postres-{uuid.uuid4().hex[:6]}")
    db.add(otra_categoria)
    db.commit()
    db.refresh(otra_categoria)
    db.close()

    antiguo = _registrar_menu(
        client, id_categoria, fecha_inicio=str(HOY - timedelta(days=60)),
        fecha_fin=str(HOY - timedelta(days=45)),
    )
    reciente = _registrar_menu(client, id_categoria)
    de_otra_categoria = _registrar_menu(client, otra_categoria.id)

    historico = client.get("/api/v1/menus/historico").json()
    assert historico[0]["id"] in (reciente["id"], de_otra_categoria["id"])
    assert historico[-1]["id"] == antiguo["id"]  # el más antiguo al final

    por_categoria = client.get(
        "/api/v1/menus/historico", params={"categoria": otra_categoria.id}
    ).json()
    assert {m["id"] for m in por_categoria} == {de_otra_categoria["id"]}


def test_historico_filtro_estado(client, semillas):
    id_categoria, _ = semillas
    menu = _registrar_menu(client, id_categoria)
    client.put(f"/api/v1/menus/{menu['id']}/publicar")

    activos = client.get("/api/v1/menus/historico", params={"estado": "activo"}).json()
    inactivos = client.get("/api/v1/menus/historico", params={"estado": "inactivo"}).json()
    assert menu["id"] in {m["id"] for m in activos}
    assert menu["id"] not in {m["id"] for m in inactivos}


# --- PUT /api/v1/menus/{id}/publicar ----------------------------------------------

def test_publicar_menu(client, semillas):
    id_categoria, _ = semillas
    primero = _registrar_menu(client, id_categoria)
    segundo = _registrar_menu(client, id_categoria)

    r1 = client.put(f"/api/v1/menus/{primero['id']}/publicar")
    assert r1.status_code == 200
    assert r1.json()["estado"] == "activo"

    # Publicar el segundo desactiva al primero: solo una carta activa.
    r2 = client.put(f"/api/v1/menus/{segundo['id']}/publicar")
    assert r2.json()["estado"] == "activo"
    historico = client.get("/api/v1/menus/historico").json()
    estados = {m["id"]: m["estado"] for m in historico}
    assert estados[segundo["id"]] == "activo"
    assert estados[primero["id"]] == "inactivo"


def test_publicar_menu_inexistente(client):
    respuesta = client.put("/api/v1/menus/999999/publicar")
    assert respuesta.status_code == 404
