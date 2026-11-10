"""
Prueba del endpoint de salud.

Requiere dependencias de desarrollo:
    pip install pytest httpx

Ejecución (desde colrient/backend):
    pytest
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_responde_ok():
    respuesta = client.get("/api/v1/health")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "ok"
    assert "version" in cuerpo
