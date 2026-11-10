"""
Conexión a la base de datos SQLite y creación automática de tablas.

Contenido:
- `engine`      : pool de conexiones a la base de datos.
- `SessionLocal`: fábrica de sesiones (una sesión por petición).
- `Base`        : base declarativa de la que heredan los modelos (app/models.py).
- `get_db()`    : dependencia de FastAPI para inyectar sesiones en los endpoints.
- `init_db()`   : crea las tablas automáticamente al iniciar la aplicación
                  (invocada desde main.py en el evento de arranque).

La URL de conexión se centraliza en app/core/config.py y puede
sobrescribirse con la variable de entorno COLRIENT_DATABASE_URL; por
defecto se usa SQLite local (./colrient.db) y en producción puede
cambiarse a PostgreSQL o MySQL sin modificar este archivo.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """Base declarativa común de todos los modelos ORM de COLRIENT."""


# SQLite guarda la conexión por hilo: como FastAPI atiende las peticiones
# síncronas en un pool de hilos, se debe permitir compartir el motor.
_connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    echo=settings.DEBUG,  # True => imprime el SQL generado (modo depuración)
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@event.listens_for(engine, "connect")
def _activar_llaves_foraneas_sqlite(dbapi_connection, connection_record):
    """Activa la validación de llaves foráneas en SQLite.

    SQLite NO valida llaves foráneas por defecto; se habilita en cada
    conexión nueva para respetar los ondelete definidos en los modelos.
    """
    if engine.url.drivername.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_db():
    """Dependencia de FastAPI: entrega una sesión y la cierra al finalizar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea las tablas al iniciar la aplicación si aún no existen.

    Importa los modelos para que queden registrados en Base.metadata
    antes de ejecutar create_all (el import es local para evitar la
    dependencia circular: models.py importa Base desde este módulo).

    Nota: pensado para desarrollo. En producción usar migraciones
    controladas (p. ej. Alembic) en lugar de create_all().
    """
    from app import models  # noqa: F401  (registra las tablas)

    Base.metadata.create_all(bind=engine)
