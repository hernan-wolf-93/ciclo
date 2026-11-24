from collections import defaultdict

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Etapa,
    EventoItem,
    Item,
    Material,
    MetodoEsterilizacion,
    Operador,
    Recepcion,
    Servicio,
)
from app.schemas.avance import AvanceIn
from app.services.flujo import validar_avance_varios


class ErrorDeAvance(Exception):
    """Una regla de negocio no se cumple. El router la responde como 422."""


def _ultimo_evento_por_item(material_id: int | None = None):
    """Subconsulta con el id del último evento de cada ítem (el de mayor id).

    Con material_id, solo de los ítems de ese material.
    """
    consulta = (
        select(func.max(EventoItem.id).label("id"))
        .select_from(EventoItem)
        .join(Item, Item.id == EventoItem.item_id)
    )
    if material_id is not None:
        consulta = consulta.where(Item.material_id == material_id)
    return consulta.group_by(EventoItem.item_id).subquery()


def _items_en_espera(
    db: Session, material_id: int, orden_origen: int, cantidad: int, excluir=()
) -> list[int]:
    """Ids de los ítems más antiguos del material cuyo último evento es de la etapa de origen.

    "Último" es el evento de mayor id, no el de mayor fecha: los eventos de una
    misma transacción comparten fecha_hora. Con excluir se saltean ítems que otra
    línea del mismo pedido ya eligió.
    """
    ultimos = _ultimo_evento_por_item(material_id)
    consulta = (
        select(EventoItem.item_id)
        .join(ultimos, ultimos.c.id == EventoItem.id)
        .join(Etapa, Etapa.id == EventoItem.etapa_id)
        .where(Etapa.orden == orden_origen)
    )
    if excluir:
        consulta = consulta.where(EventoItem.item_id.not_in(excluir))
    return list(db.scalars(consulta.order_by(EventoItem.item_id).limit(cantidad)))


def _validar_metodos(db: Session, datos: AvanceIn) -> None:
    """Rechaza el pedido si alguna línea nombra un método que no existe."""
    pedidos = {linea.metodo_id for linea in datos.items if linea.metodo_id is not None}
    if not pedidos:
        return
    existentes = set(
        db.scalars(select(MetodoEsterilizacion.id).where(MetodoEsterilizacion.id.in_(pedidos)))
    )
    faltantes = sorted(pedidos - existentes)
    if faltantes:
        raise ErrorDeAvance(f"El método {faltantes[0]} no existe")


def _elegir_items(db: Session, datos: AvanceIn) -> list[tuple[int, int | None]]:
    """Pares (id del ítem, método) de los ítems que avanzan.

    Cada línea toma los más antiguos que no hayan tomado las anteriores. El orden
    de las líneas es fijo (material y método) para que el resultado sea siempre el mismo.
    """
    elegidos: list[tuple[int, int | None]] = []
    ya_elegidos: set[int] = set()
    for linea in sorted(datos.items, key=lambda x: (x.material_id, x.metodo_id or 0)):
        ids = _items_en_espera(
            db, linea.material_id, datos.etapa_orden - 1, linea.cantidad, ya_elegidos
        )
        if len(ids) < linea.cantidad:
            material = db.get(Material, linea.material_id)
            nombre = material.nombre if material else f"id {linea.material_id}"
            raise ErrorDeAvance(
                f"{nombre}: se pidieron {linea.cantidad} unidades y solo hay {len(ids)} "
                "esperando en la etapa anterior"
            )
        ya_elegidos.update(ids)
        elegidos.extend((item_id, linea.metodo_id) for item_id in ids)
    return elegidos


def _asignar_metodos(db: Session, elegidos: list[tuple[int, int | None]]) -> None:
    """Guarda en cada ítem el método elegido al empacar (en lavado no hay método)."""
    por_metodo: dict[int, list[int]] = defaultdict(list)
    for item_id, metodo_id in elegidos:
        if metodo_id is not None:
            por_metodo[metodo_id].append(item_id)
    for metodo_id, item_ids in por_metodo.items():
        db.execute(update(Item).where(Item.id.in_(item_ids)).values(metodo_id=metodo_id))


def registrar_avance(db: Session, operador: Operador, datos: AvanceIn) -> int:
    """Pasa ítems a Lavado o a Empaque, con un evento firmado por cada uno.

    Todo ocurre en una transacción: si algo falla, no queda nada. Devuelve la
    cantidad de ítems avanzados. Lanza ErrorDeAvance o ErrorDeFlujo si una regla
    no se cumple.
    
    En Empaque también se asigna el método de cada ítem.
    """
    etapa = db.scalar(select(Etapa).where(Etapa.orden == datos.etapa_orden))
    if etapa is None:  # error de configuración, no del usuario
        raise RuntimeError(f"Falta la etapa {datos.etapa_orden} en el catálogo")

    _validar_metodos(db, datos)
    elegidos = _elegir_items(db, datos)
    item_ids = [item_id for item_id, _ in elegidos]
    validar_avance_varios(db, item_ids, datos.etapa_orden)

    try:
        db.add_all(
            [
                EventoItem(
                    item_id=item_id,
                    etapa_id=etapa.id,
                    operador_id=operador.id,
                    observacion=datos.observacion,
                    solo_desinfeccion=datos.solo_desinfeccion,
                )
                for item_id in item_ids
            ]
        )
        
        _asignar_metodos(db, elegidos)
        
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ErrorDeAvance(
            "Alguno de los ítems ya fue avanzado por otro operador: vuelva a intentarlo"
        ) from error
    except Exception:
        db.rollback()
        raise

    return len(item_ids)


def listar_pendientes(db: Session, etapa_orden: int) -> list[dict]:
    """Material que espera para pasar a la etapa indicada, por servicio y material.

    Usa el mismo criterio que registrar_avance: ítems cuyo último evento es de la
    etapa anterior. Es una consulta de solo lectura.
    """
    ultimos = _ultimo_evento_por_item()
    filas = db.execute(
        select(
            Servicio.id.label("servicio_id"),
            Servicio.nombre.label("servicio"),
            Material.id.label("material_id"),
            Material.nombre.label("material"),
            func.count(Item.id).label("cantidad"),
        )
        .select_from(EventoItem)
        .join(ultimos, ultimos.c.id == EventoItem.id)
        .join(Etapa, Etapa.id == EventoItem.etapa_id)
        .join(Item, Item.id == EventoItem.item_id)
        .join(Recepcion, Recepcion.id == Item.recepcion_id)
        .join(Servicio, Servicio.id == Recepcion.servicio_id)
        .join(Material, Material.id == Item.material_id)
        .where(Etapa.orden == etapa_orden - 1)
        .group_by(Servicio.id, Servicio.nombre, Material.id, Material.nombre)
        .order_by(Servicio.nombre, Material.nombre)
    ).mappings()
    return [dict(fila) for fila in filas]