import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from alembic.script import ScriptDirectory

from sqlalchemy import text
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.api.deps import obtener_db
from app.core.config import settings
from app.core.database import Base
from app.core.seguridad import hashear_contrasena
from app.main import app
from app.models import Material, Operador, Rol, Servicio

CONTRASENA_PRUEBA = "clave-de-prueba-1"
# Se calcula una sola vez: Argon2 es lento a propósito.
HASH_PRUEBA = hashear_contrasena(CONTRASENA_PRUEBA)


@pytest.fixture
def contrasena():
    return CONTRASENA_PRUEBA


@pytest.fixture
def db():
    """Base SQLite en memoria, nueva en cada prueba, solo con rol y operador."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Rol.__table__, Operador.__table__])
    sesion = sessionmaker(bind=engine, autoflush=False)()
    sesion.add_all(
        [
            Rol(id=1, nombre="Administrador principal"),
            Rol(id=3, nombre="Operador"),
        ]
    )
    sesion.commit()
    yield sesion
    sesion.close()
    engine.dispose()


@pytest.fixture
def crear_operador(db):
    """Devuelve una función que crea un operador ficticio en la base de prueba."""

    def _crear(numero="9001", rol_id=1, activo=True):
        operador = Operador(
            numero_operador=numero,
            contrasena_hash=HASH_PRUEBA,
            rol_id=rol_id,
            activo=activo,
        )
        db.add(operador)
        db.commit()
        db.refresh(operador)
        return operador

    return _crear


@pytest.fixture
def cliente(db):
    """Cliente HTTP de prueba con la base de datos reemplazada por la de SQLite."""

    def _db_de_prueba():
        yield db

    app.dependency_overrides[obtener_db] = _db_de_prueba
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    
# ---------------------------------------------------------------------------
# Base PostgreSQL de pruebas (ciclo_test). El esquema lo crean las migraciones.
# ---------------------------------------------------------------------------
RAIZ_BACKEND = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def engine_pg():
    """Conexión a la base de pruebas, con guardas para no tocar la base real."""
    url = settings.test_database_url
    if not url:
        pytest.skip("TEST_DATABASE_URL no está definida en backend/.env: se omiten las pruebas con PostgreSQL")

    nombre = make_url(url).database or ""
    if not nombre.endswith("_test"):
        pytest.fail(f"La base de pruebas debe terminar en _test (se recibió '{nombre}'). No se ejecuta nada.")
    if nombre == make_url(settings.database_url).database:
        pytest.fail("TEST_DATABASE_URL apunta a la misma base que DATABASE_URL. No se ejecuta nada.")

    engine = create_engine(url)
    try:
        with engine.connect() as conexion:
            actual = conexion.scalar(text("SELECT version_num FROM alembic_version"))
    except SQLAlchemyError as error:
        pytest.fail(f"No se pudo leer la versión de la base de pruebas ({type(error).__name__}). "
                    "¿Está creada y migrada? Ver README.")
    cabeza = ScriptDirectory(str(RAIZ_BACKEND / "alembic")).get_current_head()
    if actual != cabeza:
        pytest.fail(f"ciclo_test está en la versión {actual} y el código en {cabeza}. "
                    "Actualizala con la variable DATABASE_URL apuntando a ciclo_test y alembic upgrade head.")
    yield engine
    engine.dispose()


@pytest.fixture
def db_pg(engine_pg):
    """Sesión sobre ciclo_test dentro de una transacción que se revierte al terminar."""
    conexion = engine_pg.connect()
    transaccion = conexion.begin()
    sesion = Session(bind=conexion, autoflush=False, join_transaction_mode="create_savepoint")
    yield sesion
    sesion.close()
    transaccion.rollback()
    conexion.close()
    
@pytest.fixture
def operador(db_pg):
    rol = db_pg.scalar(select(Rol).where(Rol.nombre == "Operador"))
    nuevo = Operador(numero_operador="T-0001", contrasena_hash="hash-de-prueba", rol_id=rol.id)
    db_pg.add(nuevo)
    db_pg.commit()
    return nuevo


@pytest.fixture
def servicio(db_pg):
    return db_pg.scalar(select(Servicio).where(Servicio.activo.is_(True)).order_by(Servicio.id))


@pytest.fixture
def materiales(db_pg):
    return list(
        db_pg.scalars(select(Material).where(Material.activo.is_(True)).order_by(Material.id).limit(2))
    )


@pytest.fixture
def cliente_pg(db_pg):
    """Cliente HTTP de prueba con la base de datos reemplazada por ciclo_test."""

    def _db_de_prueba():
        yield db_pg

    app.dependency_overrides[obtener_db] = _db_de_prueba
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()