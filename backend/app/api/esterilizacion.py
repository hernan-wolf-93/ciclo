from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.models import Operador
from app.schemas.avance import PendienteOut
from app.schemas.esterilizacion import (
    CierreLoteIn,
    FallaPosteriorIn,
    FallaPosteriorOut,
    LoteCerradoOut,
    LoteCreadoOut,
    LoteIn,
)
from app.services.esterilizacion import (
    ErrorDeLote,
    FallaPosteriorNoPermitida,
    LoteInexistente,
    LoteYaCerrado,
    cerrar_lote,
    listar_pendientes_equipo,
    marcar_falla_posterior,
    registrar_lote,
)
from app.services.flujo import ErrorDeFlujo
from app.services.numeracion_lote import EquipoInexistente

router = APIRouter(tags=["esterilizacion"], dependencies=[Depends(obtener_operador_actual)])


@router.get("/equipos/{equipo_id}/pendientes", response_model=list[PendienteOut])
def pendientes_del_equipo(equipo_id: int, db: Annotated[Session, Depends(obtener_db)]):
    """Material que puede cargar el equipo (su método), por servicio de origen y material."""
    try:
        return listar_pendientes_equipo(db, equipo_id)
    except EquipoInexistente as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/lotes", response_model=LoteCreadoOut, status_code=status.HTTP_201_CREATED)
def crear_lote(
    datos: LoteIn,
    operador: Annotated[Operador, Depends(obtener_operador_actual)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Carga un equipo: crea el lote y pasa sus ítems a Esterilización. El operador sale del token."""
    try:
        lote, total = registrar_lote(db, operador, datos)
    except EquipoInexistente as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (ErrorDeLote, ErrorDeFlujo) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return LoteCreadoOut(
        id=lote.id,
        numero=lote.numero,
        equipo_id=lote.equipo_id,
        programa_id=lote.programa_id,
        inicio=lote.inicio,
        total_items=total,
    )
    
    
@router.post("/lotes/{lote_id}/cierre", response_model=LoteCerradoOut)
def cerrar(
    lote_id: int,
    datos: CierreLoteIn,
    db: Annotated[Session, Depends(obtener_db)],
):
    """Cierra la carga de un equipo con el resultado del ciclo. El fin lo pone el servidor."""
    try:
        lote = cerrar_lote(db, lote_id, datos)
    except LoteInexistente as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LoteYaCerrado as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    return LoteCerradoOut(
        id=lote.id,
        numero=lote.numero,
        resultado=lote.resultado,
        fin=lote.fin,
        numero_ciclo=lote.numero_ciclo,
        observacion=lote.observacion,
    )
    
    
@router.post("/lotes/{lote_id}/falla-posterior", response_model=FallaPosteriorOut)
def registrar_falla_posterior(
    lote_id: int,
    datos: FallaPosteriorIn,
    operador: Annotated[Operador, Depends(obtener_operador_actual)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Marca como fallido un lote aprobado cuya falla se detectó después del cierre."""
    try:
        lote = marcar_falla_posterior(db, operador, lote_id, datos)
    except LoteInexistente as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except FallaPosteriorNoPermitida as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(error)) from error
    return FallaPosteriorOut(
        id=lote.id,
        numero=lote.numero,
        resultado=lote.resultado,
        observacion=lote.observacion,
        falla_posterior_en=lote.falla_posterior_en,
        marcado_por=operador.numero_operador,
    )