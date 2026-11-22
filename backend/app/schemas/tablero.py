"""Esquemas de salida del tablero de material en curso (RF7 y RF6). Solo lectura.

Cada fila es una recepción con al menos un ítem que todavía no llegó a Entrega.
Antes de Esterilización se sigue cada ítem; el lote aparece recién desde esa etapa.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ServicioRef(BaseModel):
    id: int
    nombre: str


class MaterialEnCursoOut(BaseModel):
    """Cuántas unidades de un material de la recepción están hoy en una etapa."""

    material_id: int
    nombre: str
    codigo: str | None
    etapa_orden: int  # 1 a 6: se deduce del último evento de cada ítem
    cantidad: int


class LoteDeFilaOut(BaseModel):
    """Último lote de esterilización de ítems de la recepción (si hubo reesterilización, el último)."""

    id: int
    numero: int  # se repite: va de 1 a 999 y es por equipo
    equipo: str
    resultado: Literal["aprobado", "fallido"] | None  # null mientras el lote está en curso


class FilaTableroOut(BaseModel):
    recepcion_id: int
    fecha_hora: datetime
    urgente: bool
    servicio: ServicioRef
    total_items: int
    # Ítems de la recepción en cada etapa, por orden (1 a 6). Siempre trae las seis.
    por_etapa: dict[int, int]
    materiales: list[MaterialEnCursoOut]
    lotes: list[LoteDeFilaOut]
