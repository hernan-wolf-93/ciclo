"""Consultas nuevas de la migración 0010: Bowie-Dick del día, servicios compatibles
por método e intento del reproceso. Corren contra ciclo_test con "ahora" fijo."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import ControlBowieDick, Equipo, Etapa, EventoItem, Item, MetodoEsterilizacion, Recepcion, Servicio
from app.services.bowie_dick import hay_bowie_dick_aprobado_hoy, inicio_del_dia
from app.services.compatibilidad import validar_servicios_compatibles
from app.services.flujo import ErrorDeFlujo
from app.services.reproceso import siguiente_intento

# 22/11/2026 15:00 en Tucumán (18:00 UTC)
AHORA = datetime(2026, 11, 22, 18, 0, tzinfo=timezone.utc)


@pytest.fixture
def autoclave(db_pg):
    return db_pg.scalar(select(Equipo).where(Equipo.nombre == "Autoclave 1"))


def _control(db, equipo, operador, fecha, resultado):
    db.add(
        ControlBowieDick(
            equipo_id=equipo.id, operador_id=operador.id, fecha_hora=fecha, resultado=resultado,
            observacion="Hoja con el centro más claro" if resultado == "fallido" else None,
        )
    )
    db.flush()


# ---------------------------------------------------------------------------
# Bowie-Dick
# ---------------------------------------------------------------------------


def test_el_dia_es_el_de_tucuman():
    # 01:00 UTC del 23/11 todavía es el 22/11 a las 22:00 en Tucumán
    assert inicio_del_dia(datetime(2026, 11, 23, 1, 0, tzinfo=timezone.utc)).date().day == 22


def test_sin_control_no_hay_aprobado(db_pg, autoclave):
    assert not hay_bowie_dick_aprobado_hoy(db_pg, autoclave.id, AHORA)


def test_aprobado_hoy(db_pg, autoclave, operador):
    _control(db_pg, autoclave, operador, AHORA - timedelta(hours=8), "aprobado")  # 07:00 en Tucumán
    assert hay_bowie_dick_aprobado_hoy(db_pg, autoclave.id, AHORA)


def test_aprobado_ayer_no_cuenta(db_pg, autoclave, operador):
    _control(db_pg, autoclave, operador, AHORA - timedelta(hours=16), "aprobado")  # 23:00 del día anterior
    assert not hay_bowie_dick_aprobado_hoy(db_pg, autoclave.id, AHORA)


def test_aprobado_de_otro_equipo_no_cuenta(db_pg, autoclave, operador):
    otro = db_pg.scalar(select(Equipo).where(Equipo.nombre == "Autoclave 2"))
    _control(db_pg, otro, operador, AHORA - timedelta(hours=2), "aprobado")
    assert not hay_bowie_dick_aprobado_hoy(db_pg, autoclave.id, AHORA)


def test_cuenta_el_ultimo_control_del_dia(db_pg, autoclave, operador):
    _control(db_pg, autoclave, operador, AHORA - timedelta(hours=8), "aprobado")
    _control(db_pg, autoclave, operador, AHORA - timedelta(hours=2), "fallido")
    assert not hay_bowie_dick_aprobado_hoy(db_pg, autoclave.id, AHORA)
    _control(db_pg, autoclave, operador, AHORA - timedelta(hours=1), "aprobado")
    assert hay_bowie_dick_aprobado_hoy(db_pg, autoclave.id, AHORA)


def test_control_posterior_a_ahora_no_cuenta(db_pg, autoclave, operador):
    _control(db_pg, autoclave, operador, AHORA + timedelta(hours=1), "aprobado")
    assert not hay_bowie_dick_aprobado_hoy(db_pg, autoclave.id, AHORA)


# ---------------------------------------------------------------------------
# Servicios compatibles según el método
# ---------------------------------------------------------------------------


def _ids(db, *nombres):
    return {db.scalar(select(Servicio.id).where(Servicio.nombre == n)) for n in nombres}


def _metodo_id(db, nombre):
    return db.scalar(select(MetodoEsterilizacion.id).where(MetodoEsterilizacion.nombre == nombre))


def test_neo_y_uti_no_van_juntos_en_oxido_de_etileno(db_pg):
    with pytest.raises(ErrorDeFlujo, match="Neonatología y Unidad de Terapia Intensiva"):
        validar_servicios_compatibles(
            db_pg, _ids(db_pg, "Neonatología", "Unidad de Terapia Intensiva", "Quirófano"),
            _metodo_id(db_pg, "Óxido de etileno"),
        )


@pytest.mark.parametrize("metodo", ["Calor húmedo", "Calor seco"])
def test_neo_y_uti_van_juntos_en_autoclave_y_estufa(db_pg, metodo):
    validar_servicios_compatibles(
        db_pg, _ids(db_pg, "Neonatología", "Unidad de Terapia Intensiva"), _metodo_id(db_pg, metodo)
    )  # no debe lanzar nada


def test_un_solo_servicio_siempre_es_compatible(db_pg):
    validar_servicios_compatibles(db_pg, _ids(db_pg, "Neonatología"), _metodo_id(db_pg, "Óxido de etileno"))


# ---------------------------------------------------------------------------
# Intento del reproceso
# ---------------------------------------------------------------------------


def test_siguiente_intento(db_pg, operador, servicio, materiales):
    recepcion = Recepcion(servicio_id=servicio.id, completo=True)
    db_pg.add(recepcion)
    db_pg.flush()
    item = Item(recepcion_id=recepcion.id, material_id=materiales[0].id)
    db_pg.add(item)
    db_pg.flush()
    assert siguiente_intento(db_pg, item.id) == 1  # sin historial

    empaque = db_pg.scalar(select(Etapa.id).where(Etapa.orden == 3))
    db_pg.add(EventoItem(item_id=item.id, etapa_id=empaque, operador_id=operador.id))
    db_pg.flush()
    assert siguiente_intento(db_pg, item.id) == 2

    db_pg.add(EventoItem(item_id=item.id, etapa_id=empaque, operador_id=operador.id, intento=2))
    db_pg.flush()
    assert siguiente_intento(db_pg, item.id) == 3
