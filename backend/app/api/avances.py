from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.models import Operador
from app.schemas.avance import AvanceIn, AvanceOut, PendienteOut
from app.services.avance import ErrorDeAvance, listar_pendientes, registrar_avance
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


@router.get(
    "/pendientes",
    response_model=list[PendienteOut],
    dependencies=[Depends(obtener_operador_actual)],
)
def pendientes(
    db: Annotated[Session, Depends(obtener_db)],
    etapa_orden: Annotated[
        int,
        Query(ge=2, le=3, description="Etapa a la que se quiere pasar: 2 = Lavado, 3 = Empaque."),
    ],
):
    """Material que espera para pasar a esa etapa, por servicio de origen y material."""
    return listar_pendientes(db, etapa_orden)