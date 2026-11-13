from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.models import Operador
from app.schemas.recepcion import RecepcionIn, RecepcionOut
from app.services.recepcion import ErrorDeRecepcion, registrar_recepcion

router = APIRouter(prefix="/recepciones", tags=["recepciones"])


@router.post("", response_model=RecepcionOut, status_code=status.HTTP_201_CREATED)
def crear_recepcion(
    datos: RecepcionIn,
    operador: Annotated[Operador, Depends(obtener_operador_actual)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Registra una recepción. El operador que firma sale del token."""
    try:
        recepcion, total = registrar_recepcion(db, operador, datos)
    except ErrorDeRecepcion as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return RecepcionOut(
        id=recepcion.id,
        servicio_id=recepcion.servicio_id,
        fecha_hora=recepcion.fecha_hora,
        total_items=total,
    )