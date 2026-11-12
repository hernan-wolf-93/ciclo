import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import obtener_db
from app.core.database import Base
from app.core.seguridad import hashear_contrasena
from app.main import app
from app.models import Operador, Rol

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