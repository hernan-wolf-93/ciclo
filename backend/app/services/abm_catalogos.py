"""ABM de servicios y materiales: reglas de negocio.

La baja es lógica (activo = false): hay recepciones e ítems que referencian estos
registros, así que nunca se borra una fila. Los nombres reales de los sanatorios
privados se cargan desde acá al instalar el sistema (docs/RESPUESTAS-SERVICIO.md).
"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalogos import Material, Servicio
from app.schemas.catalogo import (
    MaterialAltaIn,
    MaterialModificarIn,
    ServicioAltaIn,
    ServicioModificarIn,
)


class ErrorDeCatalogo(Exception):
    """Una regla de negocio no se cumple. El router la responde como 422."""


class Duplicado(ErrorDeCatalogo):
    """Nombre o código repetidos. El router la responde como 409."""


class Inexistente(ErrorDeCatalogo):
    """El registro pedido no existe. El router la responde como 404."""


# --- Consultas ---------------------------------------------------------------


def listar_servicios_admin(db: Session) -> list[Servicio]:
    """Todos los servicios, activos e inactivos, ordenados por nombre."""
    return list(db.scalars(select(Servicio).order_by(Servicio.nombre)))


def listar_materiales_admin(db: Session) -> list[Material]:
    """Todos los materiales, activos e inactivos, ordenados por nombre."""
    return list(db.scalars(select(Material).order_by(Material.nombre)))


# --- Controles de duplicados -------------------------------------------------
# La base exige nombre único pero distingue mayúsculas; acá "quirófano" choca
# con "Quirófano", para que no queden dos registros que parecen el mismo.


def _nombre_en_uso(db: Session, modelo, nombre: str, excepto_id: int | None = None) -> bool:
    consulta = select(modelo.id).where(func.lower(modelo.nombre) == func.lower(nombre))
    if excepto_id is not None:
        consulta = consulta.where(modelo.id != excepto_id)
    return db.scalar(consulta.limit(1)) is not None


def _codigo_en_uso(db: Session, codigo: str, excepto_id: int | None = None) -> bool:
    consulta = select(Material.id).where(Material.codigo == codigo)
    if excepto_id is not None:
        consulta = consulta.where(Material.id != excepto_id)
    return db.scalar(consulta.limit(1)) is not None


def _guardar(db: Session, registro, revisar_duplicados) -> None:
    """Confirma los cambios. Si dos pedidos simultáneos pasaron los controles,
    frena la restricción única de la base y se responde como duplicado."""
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        revisar_duplicados()  # lanza Duplicado si corresponde
        raise error
    except Exception:
        db.rollback()
        raise
    db.refresh(registro)


# --- Servicios -----------------------------------------------------------------


def _revisar_servicio(db: Session, nombre: str | None, excepto_id: int | None = None) -> None:
    if nombre is not None and _nombre_en_uso(db, Servicio, nombre, excepto_id):
        raise Duplicado("Ya existe un servicio con ese nombre")


def crear_servicio(db: Session, datos: ServicioAltaIn) -> Servicio:
    _revisar_servicio(db, datos.nombre)
    nuevo = Servicio(nombre=datos.nombre, externo=datos.externo, dias_aireacion=datos.dias_aireacion)
    db.add(nuevo)
    _guardar(db, nuevo, lambda: _revisar_servicio(db, datos.nombre))
    return nuevo


def modificar_servicio(db: Session, servicio_id: int, datos: ServicioModificarIn) -> Servicio:
    servicio = db.get(Servicio, servicio_id)
    if servicio is None:
        raise Inexistente(f"No existe el servicio {servicio_id}")
    cambios = datos.model_dump(exclude_unset=True)
    _revisar_servicio(db, cambios.get("nombre"), servicio_id)
    for campo, valor in cambios.items():
        setattr(servicio, campo, valor)
    _guardar(db, servicio, lambda: _revisar_servicio(db, cambios.get("nombre"), servicio_id))
    return servicio


# --- Materiales ----------------------------------------------------------------


def _revisar_material(
    db: Session, nombre: str | None, codigo: str | None, excepto_id: int | None = None
) -> None:
    if nombre is not None and _nombre_en_uso(db, Material, nombre, excepto_id):
        raise Duplicado("Ya existe un material con ese nombre")
    if codigo is not None and _codigo_en_uso(db, codigo, excepto_id):
        raise Duplicado("Ya existe un material con ese código")


def crear_material(db: Session, datos: MaterialAltaIn) -> Material:
    _revisar_material(db, datos.nombre, datos.codigo)
    nuevo = Material(nombre=datos.nombre, codigo=datos.codigo, nombre_alternativo=datos.nombre_alternativo)
    db.add(nuevo)
    _guardar(db, nuevo, lambda: _revisar_material(db, datos.nombre, datos.codigo))
    return nuevo


def modificar_material(db: Session, material_id: int, datos: MaterialModificarIn) -> Material:
    material = db.get(Material, material_id)
    if material is None:
        raise Inexistente(f"No existe el material {material_id}")
    cambios = datos.model_dump(exclude_unset=True)
    _revisar_material(db, cambios.get("nombre"), cambios.get("codigo"), material_id)
    for campo, valor in cambios.items():
        setattr(material, campo, valor)
    _guardar(
        db, material, lambda: _revisar_material(db, cambios.get("nombre"), cambios.get("codigo"), material_id)
    )
    return material
