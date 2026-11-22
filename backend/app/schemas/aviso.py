"""Esquemas de salida de los avisos de material detenido (RF4 y RF7). Solo lectura."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.tablero import ServicioRef


class MaterialRef(BaseModel):
    id: int
    nombre: str
    codigo: str | None


class LoteAvisoRef(BaseModel):
    id: int
    numero: int  # se repite por equipo
    equipo: str


class AvisoOut(BaseModel):
    """Un grupo de ítems de una misma recepción, material, etapa y motivo."""

    tipo: Literal["detenido", "listo_para_retirar"]
    recepcion_id: int
    servicio: ServicioRef
    material: MaterialRef
    cantidad: int
    etapa_orden: int
    lote: LoteAvisoRef | None  # desde Esterilización
    desde: datetime  # el ítem más viejo del grupo (o el fin de la aireación)
    minutos_transcurridos: int  # calculado en el servidor con el mismo "ahora"
    umbral_minutos: int | None  # null en "listo para retirar"
    motivo: str
