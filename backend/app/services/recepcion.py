from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Etapa, EventoItem, Item, Material, Operador, Recepcion, Servicio
from app.schemas.recepcion import RecepcionIn

ORDEN_ETAPA_RECEPCION = 1


class ErrorDeRecepcion(Exception):
    """Una regla de negocio no se cumple. El router la responde como 422."""


def _validar_catalogos(db: Session, datos: RecepcionIn) -> None:
    servicio = db.get(Servicio, datos.servicio_id)
    if servicio is None or not servicio.activo:
        raise ErrorDeRecepcion("El servicio de origen no existe o está dado de baja")

    pedidos = {linea.material_id for linea in datos.items}
    activos = set(
        db.scalars(select(Material.id).where(Material.id.in_(pedidos), Material.activo.is_(True)))
    )
    faltantes = sorted(pedidos - activos)
    if faltantes:
        raise ErrorDeRecepcion(f"Materiales inexistentes o dados de baja: {faltantes}")


def registrar_recepcion(db: Session, operador: Operador, datos: RecepcionIn) -> tuple[Recepcion, int]:
    """Registra una recepción: un ítem por unidad y su evento de Recepción firmado.

    Todo ocurre en una transacción: si algo falla, no queda nada. Devuelve la
    recepción y la cantidad total de ítems creados.
    """
    _validar_catalogos(db, datos)

    etapa = db.scalar(select(Etapa).where(Etapa.orden == ORDEN_ETAPA_RECEPCION))
    if etapa is None:  # error de configuración, no del usuario
        raise RuntimeError("Falta la etapa de Recepción en el catálogo")

    try:
        recepcion = Recepcion(
            servicio_id=datos.servicio_id,
            completo=datos.completo,
            servicio_avisado=datos.servicio_avisado,
            observacion=datos.observacion,
            urgente=datos.urgente,
        )
        db.add(recepcion)
        db.flush()  # para conocer recepcion.id

        items = [
            Item(recepcion_id=recepcion.id, material_id=linea.material_id)
            for linea in datos.items
            for _ in range(linea.cantidad)
        ]
        db.add_all(items)
        db.flush()  # para conocer el id de cada ítem

        db.add_all(
            [EventoItem(item_id=item.id, etapa_id=etapa.id, operador_id=operador.id) for item in items]
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return recepcion, len(items)