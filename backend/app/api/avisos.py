from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.schemas.aviso import AvisoOut
from app.services.avisos import listar_avisos

# Solo lectura, pero con sesión iniciada, igual que el tablero.
router = APIRouter(
    prefix="/avisos",
    tags=["avisos"],
    dependencies=[Depends(obtener_operador_actual)],
)


def obtener_ahora() -> datetime:
    """Fecha y hora actual con zona (UTC). Las pruebas la reemplazan por una fija."""
    return datetime.now(timezone.utc)


@router.get("", response_model=list[AvisoOut])
def avisos(
    db: Annotated[Session, Depends(obtener_db)],
    ahora: Annotated[datetime, Depends(obtener_ahora)],
):
    """Material detenido (fuera de su tiempo normal) y material listo para retirar."""
    return listar_avisos(db, ahora)
