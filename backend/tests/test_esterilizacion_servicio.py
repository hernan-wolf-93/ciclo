"""Elección de ítems para cargar un equipo: servicio contra PostgreSQL (ciclo_test)."""

import pytest
from sqlalchemy import select

from app.models.catalogos import Servicio
from app.services.esterilizacion import elegir_items


@pytest.fixture
def dos_servicios(db_pg):
    return list(
        db_pg.scalars(select(Servicio).where(Servicio.activo.is_(True)).order_by(Servicio.id).limit(2))
    )


def test_toma_los_mas_antiguos_del_servicio_y_material_pedidos(
    db_pg, empacar, equipo_de, dos_servicios, materiales, metodos
):
    a, b = dos_servicios
    m1, _ = materiales
    ids_a = empacar(a, m1, metodos[0], 3)
    ids_b = empacar(b, m1, metodos[0], 2)
    equipo = equipo_de(metodos[0])

    assert elegir_items(db_pg, equipo, b.id, m1.id, 2) == ids_b
    assert elegir_items(db_pg, equipo, a.id, m1.id, 2) == ids_a[:2]


def test_saltea_los_items_excluidos(db_pg, empacar, equipo_de, servicio, materiales, metodos):
    ids = empacar(servicio, materiales[0], metodos[0], 3)
    equipo = equipo_de(metodos[0])

    elegidos = elegir_items(db_pg, equipo, servicio.id, materiales[0].id, 3, excluir={ids[0]})

    assert elegidos == ids[1:]


def test_pedir_mas_de_lo_disponible_devuelve_lo_que_hay(
    db_pg, empacar, equipo_de, servicio, materiales, metodos
):
    ids = empacar(servicio, materiales[0], metodos[0], 3)
    equipo = equipo_de(metodos[0])

    assert elegir_items(db_pg, equipo, servicio.id, materiales[0].id, 10) == ids


def test_un_equipo_de_otro_metodo_no_ve_el_material(
    db_pg, empacar, equipo_de, servicio, materiales, metodos
):
    empacar(servicio, materiales[0], metodos[0], 3)

    assert elegir_items(db_pg, equipo_de(metodos[1]), servicio.id, materiales[0].id, 3) == []