from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal


def obtener_db() -> Iterator[Session]:
    """Entrega una sesión de base de datos por pedido y la cierra al terminar."""
    with SessionLocal() as db:
        yield db