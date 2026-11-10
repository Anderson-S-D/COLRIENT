"""Configuración de las pruebas: aísla BD y carpeta de subidas.

Se ejecuta ANTES de importar la aplicación, de modo que app.core.config
lea variables de entorno apuntando a recursos de prueba y no cree
archivos dentro del proyecto real. Los fixtures compartidos (cliente de
pruebas y datos semilla) viven aquí para todos los módulos.
"""

import os
import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TESTS_DIR = Path(__file__).resolve().parent
TEST_DB = TESTS_DIR / "test_colrient.db"
TEST_UPLOADS = TESTS_DIR / "test_uploads"

# Aislar la base de datos y las fotos antes de importar la app.
os.environ["COLRIENT_DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["COLRIENT_UPLOAD_DIR"] = str(TEST_UPLOADS)


@pytest.fixture(scope="session", autouse=True)
def _limpieza_final():
    """Elimina los recursos de prueba al terminar la sesión de pytest."""
    yield
    TEST_DB.unlink(missing_ok=True)
    shutil.rmtree(TEST_UPLOADS, ignore_errors=True)


@pytest.fixture(scope="session")
def client():
    """Cliente de pruebas con tablas recreadas desde cero."""
    from app import models  # noqa: F401  (registra los modelos)
    from app.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from main import app

    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture(scope="session")
def semillas():
    """Crea una categoría y una región de referencia; devuelve sus ids."""
    from app.database import SessionLocal
    from app.models import Categoria, Region

    db = SessionLocal()
    try:
        categoria = Categoria(nombre=f"Sopas-{uuid.uuid4().hex[:6]}")
        region = Region(nombre=f"Andina-{uuid.uuid4().hex[:6]}")
        db.add_all([categoria, region])
        db.commit()
        db.refresh(categoria)
        db.refresh(region)
        return categoria.id, region.id
    finally:
        db.close()
