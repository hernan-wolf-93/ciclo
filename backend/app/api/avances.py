from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.models import Operador
from app.schemas.avance import AvanceIn, AvanceOut
from app.services.avance import ErrorDeAvance, registrar_avance
from app.services.flujo import ErrorDeFlujo

router = APIRouter(prefix="/avances", tags=["avances"])


@router.post("", response_model=AvanceOut, status_code=status.HTTP_201_CREATED)
def crear_avance(
    datos: AvanceIn,
    operador: Annotated[Operador, Depends(obtener_operador_actual)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Pasa ítems a Lavado o a Empaque. El operador que firma sale del token."""
    try:
        total = registrar_avance(db, operador, datos)
    except (ErrorDeAvance, ErrorDeFlujo) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return AvanceOut(
        etapa_orden=datos.etapa_orden,
        total_items=total,
        solo_desinfeccion=datos.solo_desinfeccion,
    )