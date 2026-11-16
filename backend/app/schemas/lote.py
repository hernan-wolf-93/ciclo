"""Esquemas de salida del historial de lotes (RF3).

Los nombres copian el contrato del frontend (frontend/src/types.ts): LoteResumen,
LoteDetalle, ItemDelLote, EventoItem, Programa y LoteRef. Solo lectura.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ResultadoLote = Literal["aprobado", "fallido"]


class _DesdeModelo(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MetodoOut(_DesdeModelo):
    id: int
    nombre: str


class EquipoOut(_DesdeModelo):
    id: int
    nombre: str
    metodo_id: int
    metodo: MetodoOut  # el método del lote sale de su equipo


class ProgramaOut(_DesdeModelo):
    id: int
    nombre: str
    metodo_id: int
    # TODO: los parámetros del programa dependen de la migración 0008. Hasta
    # entonces no existen en la base y se devuelven en null.
    temperatura_c: float | None = None
    tiempo_esterilizacion_min: int | None = None
    tiempo_secado_min: int | None = None
    vacio_bar: float | None = None
    vapor_bar: float | None = None
    pulsos: int | None = None


class EtapaOut(_DesdeModelo):
    id: int
    orden: int
    nombre: str
    area: str
    color: str


class OperadorOut(_DesdeModelo):
    """Solo id y número: nunca el hash de la contraseña ni otros datos."""

    id: int
    numero_operador: str


class ServicioOut(_DesdeModelo):
    id: int
    nombre: str
    dias_aireacion: int


class MaterialOut(_DesdeModelo):
    id: int
    nombre: str
    codigo: str | None


class LoteRef(BaseModel):
    id: int
    numero: int


class EventoItemOut(BaseModel):
    id: int
    item_id: int
    etapa_id: int
    operador_id: int
    lote_id: int | None  # solo en Esterilización: el lote de cada intento
    fecha_hora: datetime
    etapa: EtapaOut
    operador: OperadorOut


class ItemDelLoteOut(BaseModel):
    id: int
    recepcion_id: int
    material_id: int
    metodo_id: int | None
    lote_id: int | None  # el lote de su último evento de Esterilización
    entrega_id: int | None
    material: MaterialOut
    servicio: ServicioOut  # servicio de origen (item.recepcion.servicio)
    eventos: list[EventoItemOut]  # ordenados por fecha_hora y, a igual hora, por id


class LoteResumenOut(BaseModel):
    id: int
    numero: int  # se reinicia (1 a 999) y puede repetirse
    inicio: datetime
    fin: datetime | None
    equipo: EquipoOut
    resultado: ResultadoLote | None
    # No se guarda: lote.fin + el mayor servicio.dias_aireacion de sus ítems.
    # Solo para óxido de etileno; null en los demás métodos o si no terminó.
    aireacion_fin_max: datetime | None


class LoteDetalleOut(BaseModel):
    id: int
    numero: int
    equipo_id: int
    programa_id: int
    operador_id: int
    inicio: datetime
    fin: datetime | None
    resultado: ResultadoLote | None
    observacion: str | None  # motivo, obligatorio si el lote falló
    # TODO: lote.numero_ciclo depende de la migración 0008. Hasta entonces, null.
    numero_ciclo: str | None = None
    equipo: EquipoOut
    programa: ProgramaOut
    operador: OperadorOut
    # No se guardan: se deducen de los ítems con dos eventos de Esterilización.
    reemplazado_por: LoteRef | None  # este lote falló y su material pasó a otro
    reemplaza_a: LoteRef | None  # este es el lote de reemplazo de uno que falló
    # Ítems que pasaron por el lote (evento_item.lote_id), no solo los de item.lote_id
    items: list[ItemDelLoteOut]
