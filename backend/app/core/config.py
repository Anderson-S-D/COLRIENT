"""
Configuración centralizada del backend COLRIENT.

Todos los valores se pueden sobrescribir con variables de entorno para
pasar de desarrollo a producción sin cambiar el código:

    COLRIENT_DEBUG=true
    COLRIENT_DATABASE_URL=postgresql+psycopg://usuario:clave@host:5432/colrient
    COLRIENT_CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
    COLRIENT_UPLOAD_DIR=/var/www/colrient/uploads
"""

import os
from pathlib import Path


class Settings:
    """Parámetros globales de la aplicación."""

    # --- Identidad del servicio ---------------------------------------
    APP_NAME: str = "COLRIENT - Sistema de gestión"
    APP_DESCRIPTION: str = (
        "API REST del sistema de gestión de platos, ingredientes, "
        "menús y carta digital para el restaurante COLRIENT."
    )
    VERSION: str = "0.1.0"

    # --- Servidor -------------------------------------------------------
    HOST: str = os.getenv("COLRIENT_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("COLRIENT_PORT", "8000"))
    DEBUG: bool = os.getenv("COLRIENT_DEBUG", "false").lower() in ("1", "true", "yes")

    # --- API ---------------------------------------------------------------
    API_V1_PREFIX: str = "/api/v1"

    # --- Base de datos -------------------------------------------------------
    # SQLite local por defecto. En producción cambiar a PostgreSQL/MySQL,
    # p. ej.: postgresql+psycopg://usuario:clave@localhost:5432/colrient
    DATABASE_URL: str = os.getenv("COLRIENT_DATABASE_URL", "sqlite:///./colrient.db")

    # --- CORS -----------------------------------------------------------------
    # Orígenes autorizados a consumir la API desde el navegador.
    # 8000 = el propio backend; 5500 = VS Code Live Server.
    CORS_ORIGINS: list[str] = os.getenv(
        "COLRIENT_CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")

    # --- Archivos subidos (fotos de los platos) -----------------------------
    # Raíz del proyecto backend/ (backend/app/core/config.py → backend/).
    _base_dir = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = Path(
        os.getenv("COLRIENT_UPLOAD_DIR", str(_base_dir / "uploads"))
    )
    FOTOS_DIR: Path = UPLOAD_DIR / "platos"
    MAX_FOTO_BYTES: int = 5 * 1024 * 1024  # 5 MB por imagen
    # content_type aceptado → extensión con la que se guarda el archivo.
    MIME_FOTOS_PERMITIDOS: dict[str, str] = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }


settings = Settings()
