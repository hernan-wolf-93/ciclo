"""Consultas de solo lectura sobre los catálogos."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalogos import Equipo, Material, MetodoEsterilizacion, Programa, Servicio
from app.services.numeracion_lote import EquipoInexistente


def listar_servicios(db: Session) -> list[dict]:
    filas = db.execute(
        select(Servicio.id, Servicio.nombre, Servicio.dias_aireacion)
        .where(Servicio.activo.is_(True))
        .order_by(Servicio.nombre)
    ).mappings()
    return [dict(fila) for fila in filas]


def listar_materiales(db: Session) -> list[dict]:
    filas = db.execute(
        select(Material.id, Material.nombre, Material.codigo, Material.nombre_alternativo)
        .where(Material.activo.is_(True))
        .order_by(Material.nombre)
    ).mappings()
    return [dict(fila) for fila in filas]


def listar_equipos(db: Session) -> list[dict]:
    filas = db.execute(
        select(
            Equipo.id,
            Equipo.nombre,
            Equipo.metodo_id,
            MetodoEsterilizacion.nombre.label("metodo"),
        )
        .join(MetodoEsterilizacion, MetodoEsterilizacion.id == Equipo.metodo_id)
        .where(Equipo.activo.is_(True))
        .order_by(Equipo.nombre)
    ).mappings()
    return [dict(fila) for fila in filas]


def listar_programas(db: Session, equipo_id: int | None = None) -> list[dict]:
    """Programas de esterilización. Con equipo_id, solo los del método de ese equipo."""
    consulta = select(
        Programa.id,
        Programa.nombre,
        Programa.metodo_id,
        Programa.temperatura_c,
        Programa.tiempo_esterilizacion_min,
        Programa.tiempo_secado_min,
        Programa.tiempo_desgasificacion_min,
        Programa.vacio_bar,
        Programa.vapor_bar,
        Programa.pulsos,
    ).order_by(Programa.nombre)
    if equipo_id is not None:
        equipo = db.get(Equipo, equipo_id)
        if equipo is None:
            raise EquipoInexistente(f"No existe el equipo {equipo_id}")
        consulta = consulta.where(Programa.metodo_id == equipo.metodo_id)
    return [dict(fila) for fila in db.execute(consulta).mappings()]


def listar_metodos(db: Session) -> list[dict]:
    filas = db.execute(
        select(MetodoEsterilizacion.id, MetodoEsterilizacion.nombre).order_by(
            MetodoEsterilizacion.nombre
        )
    ).mappings()
    return [dict(fila) for fila in filas]