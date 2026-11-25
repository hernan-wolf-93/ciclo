"""Esterilización: qué material puede cargar un equipo.

Un equipo carga material de su método: ítems cuyo último evento es Empaque y que
tienen asignado ese método, más los ítems de un lote fallido de ese método que
esperan reesterilizarse (en Esterilizacion o Almacen). La misma consulta alimenta la lista de pendientes y la
elección de ítems al crear el lote, para que lo que se ve sea lo que se puede cargar.
"""

from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.models import (
    Equipo,
    Etapa,
    EventoItem,
    Item,
    Lote,
    Material,
    Operador,
    Recepcion,
    Servicio,
)
from app.models.catalogos import Programa
from app.schemas.esterilizacion import CierreLoteIn, LoteIn
from app.services.avance import ultimo_evento_por_item
from app.services.bowie_dick import METODO_CON_BOWIE_DICK, hay_bowie_dick_aprobado_hoy
from app.services.compatibilidad import validar_servicios_compatibles
from app.services.flujo import (
    ORDEN_ALMACEN,
    ORDEN_ESTERILIZACION,
    RESULTADO_FALLIDO,
    validar_avance_varios,
)
from app.services.numeracion_lote import EquipoInexistente

ORDEN_EMPAQUE = 3


def _disponibles(equipo: Equipo):
    """Consulta (ítem, servicio de origen, material) de lo que el equipo puede cargar."""
    ultimos = ultimo_evento_por_item()
    return (
        select(
            Item.id.label("item_id"),
            Recepcion.servicio_id.label("servicio_id"),
            Item.material_id.label("material_id"),
        )
        .select_from(EventoItem)
        .join(ultimos, ultimos.c.id == EventoItem.id)
        .join(Etapa, Etapa.id == EventoItem.etapa_id)
        .join(Item, Item.id == EventoItem.item_id)
        .join(Recepcion, Recepcion.id == Item.recepcion_id)
        .outerjoin(Lote, Lote.id == EventoItem.lote_id)
        .where(Item.metodo_id == equipo.metodo_id)
        .where(
            or_(
                Etapa.orden == ORDEN_EMPAQUE,
                and_(
                    Etapa.orden.in_([ORDEN_ESTERILIZACION, ORDEN_ALMACEN]),
                    Lote.resultado == RESULTADO_FALLIDO,
                ),
            )
        )
    )


def elegir_items(
    db: Session,
    equipo: Equipo,
    servicio_id: int,
    material_id: int,
    cantidad: int,
    excluir=(),
) -> list[int]:
    """Ids de los ítems más antiguos que el equipo puede cargar, de un servicio y un material.

    Devuelve menos de los pedidos si no alcanzan: quien llama decide el error.
    Con excluir se saltean los que otra línea del mismo pedido ya eligió.
    """
    disponibles = _disponibles(equipo).subquery()
    consulta = select(disponibles.c.item_id).where(
        disponibles.c.servicio_id == servicio_id, disponibles.c.material_id == material_id
    )
    if excluir:
        consulta = consulta.where(disponibles.c.item_id.not_in(list(excluir)))
    return list(db.scalars(consulta.order_by(disponibles.c.item_id).limit(cantidad)))


def listar_pendientes_equipo(db: Session, equipo_id: int) -> list[dict]:
    """Material que puede cargar el equipo, por servicio de origen y material."""
    equipo = db.get(Equipo, equipo_id)
    if equipo is None:
        raise EquipoInexistente(f"No existe el equipo {equipo_id}")
    disponibles = _disponibles(equipo).subquery()
    filas = db.execute(
        select(
            Servicio.id.label("servicio_id"),
            Servicio.nombre.label("servicio"),
            Material.id.label("material_id"),
            Material.nombre.label("material"),
            func.count(disponibles.c.item_id).label("cantidad"),
        )
        .select_from(disponibles)
        .join(Servicio, Servicio.id == disponibles.c.servicio_id)
        .join(Material, Material.id == disponibles.c.material_id)
        .group_by(Servicio.id, Servicio.nombre, Material.id, Material.nombre)
        .order_by(Servicio.nombre, Material.nombre)
    ).mappings()
    return [dict(fila) for fila in filas]


class ErrorDeLote(Exception):
    """El lote no se puede crear. El router lo responde como 422."""
    
class LoteInexistente(Exception):
    """El lote no existe. El router lo responde como 404."""


class LoteYaCerrado(Exception):
    """El lote ya tiene resultado. El router lo responde como 409."""


def _elegir(db: Session, equipo: Equipo, datos: LoteIn) -> list[int]:
    """Ids de los ítems que entran al lote: los más antiguos de cada línea.

    Las líneas no se repiten (servicio y material), así que no se pisan entre sí.
    Si una línea no alcanza, se rechaza el pedido entero (todo o nada).
    """
    elegidos: list[int] = []
    for linea in sorted(datos.lineas, key=lambda x: (x.servicio_id, x.material_id)):
        ids = elegir_items(db, equipo, linea.servicio_id, linea.material_id, linea.cantidad)
        if len(ids) < linea.cantidad:
            material = db.get(Material, linea.material_id)
            servicio = db.get(Servicio, linea.servicio_id)
            nombre = material.nombre if material else f"material {linea.material_id}"
            origen = servicio.nombre if servicio else f"servicio {linea.servicio_id}"
            raise ErrorDeLote(
                f"{nombre} de {origen}: se pidieron {linea.cantidad} unidades y "
                f"solo hay {len(ids)} disponibles para este equipo"
            )
        elegidos.extend(ids)
    return elegidos


def registrar_lote(
    db: Session, operador: Operador, datos: LoteIn, ahora: datetime | None = None
) -> tuple[Lote, int]:
    """Carga un equipo: crea el lote y pasa sus ítems a Esterilización.

    Todo ocurre en una transacción: si algo falla, no queda nada. Devuelve el lote
    y la cantidad de ítems. Lanza EquipoInexistente, ErrorDeLote o ErrorDeFlujo.
    """
    ahora = ahora or datetime.now(timezone.utc)

    equipo = db.get(Equipo, datos.equipo_id)
    if equipo is None:
        raise EquipoInexistente(f"No existe el equipo {datos.equipo_id}")
    if not equipo.activo:
        raise ErrorDeLote("El equipo está dado de baja")

    programa = db.get(Programa, datos.programa_id)
    if programa is None:
        raise ErrorDeLote(f"No existe el programa {datos.programa_id}")
    if programa.metodo_id != equipo.metodo_id:
        raise ErrorDeLote("El programa no corresponde al método del equipo")

    if equipo.metodo.nombre == METODO_CON_BOWIE_DICK and not hay_bowie_dick_aprobado_hoy(
        db, equipo.id, ahora
    ):
        raise ErrorDeLote("El autoclave no tiene un control Bowie-Dick aprobado hoy")

    item_ids = _elegir(db, equipo, datos)
    validar_servicios_compatibles(db, {linea.servicio_id for linea in datos.lineas}, equipo.metodo_id)
    validar_avance_varios(db, item_ids, ORDEN_ESTERILIZACION)

    etapa = db.scalar(select(Etapa).where(Etapa.orden == ORDEN_ESTERILIZACION))
    if etapa is None:  # error de configuración, no del usuario
        raise RuntimeError(f"Falta la etapa {ORDEN_ESTERILIZACION} en el catálogo")

    try:
        lote = Lote(
            numero=datos.numero,
            equipo_id=equipo.id,
            programa_id=programa.id,
            operador_id=operador.id,
        )
        db.add(lote)
        db.flush()
        db.execute(update(Item).where(Item.id.in_(item_ids)).values(lote_id=lote.id))
        db.add_all(
            [
                EventoItem(
                    item_id=item_id,
                    etapa_id=etapa.id,
                    lote_id=lote.id,
                    operador_id=operador.id,
                )
                for item_id in item_ids
            ]
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(lote)
    return lote, len(item_ids)


def cerrar_lote(
    db: Session, lote_id: int, datos: CierreLoteIn, ahora: datetime | None = None
) -> Lote:
    """Cierra la carga de un equipo: guarda el resultado, el N.º de ciclo y el fin.

    No mueve los ítems de etapa: el paso a Almacén es un avance aparte. La fila del
    lote se bloquea, así que dos cierres simultáneos no se pisan: el segundo ve el
    lote cerrado. Lanza LoteInexistente o LoteYaCerrado.
    """
    ahora = ahora or datetime.now(timezone.utc)

    lote = db.scalar(select(Lote).where(Lote.id == lote_id).with_for_update())
    if lote is None:
        raise LoteInexistente(f"No existe el lote {lote_id}")
    if lote.fin is not None or lote.resultado is not None:
        db.rollback()  # suelta el bloqueo de la fila
        raise LoteYaCerrado(f"El lote {lote.numero} ya está cerrado")

    try:
        lote.fin = ahora
        lote.resultado = datos.resultado
        lote.observacion = datos.observacion
        lote.numero_ciclo = str(datos.numero_ciclo)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(lote)
    return lote