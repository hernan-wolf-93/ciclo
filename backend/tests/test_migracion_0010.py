"""Migración 0010: datos confirmados por el servicio (docs/RESPUESTAS-SERVICIO.md).

Corren contra ciclo_test, que tiene el esquema y los datos de las migraciones.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    ControlBowieDick,
    Equipo,
    Etapa,
    EventoItem,
    Item,
    Lote,
    Material,
    MetodoEsterilizacion,
    Programa,
    Recepcion,
    Servicio,
    ServicioIncompatible,
)


def _servicios(db):
    return {s.nombre: s for s in db.scalars(select(Servicio))}


def _metodo(db, nombre):
    return db.scalar(select(MetodoEsterilizacion).where(MetodoEsterilizacion.nombre == nombre))


# ---------------------------------------------------------------------------
# Servicios
# ---------------------------------------------------------------------------


def test_servicios_renombrados_conservan_su_fila(db_pg):
    # Los ids cambian entre máquinas: no se comparan con valores fijos. Se comprueba que
    # la fila renombrada es la original (anterior a los servicios que agrega la 0010).
    servicios = _servicios(db_pg)
    assert "Guardia" not in servicios and "Consultorios" not in servicios
    primer_agregado = servicios["Guardia Pediátrica"].id
    assert servicios["Guardia Mayor"].id < primer_agregado
    assert servicios["Consultorios Externos"].id < primer_agregado


def test_servicios_del_hospital_completos_y_activos(db_pg):
    servicios = _servicios(db_pg)
    hospital = [
        "Quirófano", "Neonatología", "Unidad de Terapia Intensiva", "Guardia Mayor", "Guardia Pediátrica",
        "Enfermería", "SIA", "U.T.P.R.", "Ala 2", "Ala 3", "Ala 4 Ginecología", "Sala 1", "Sala 2",
        "Sala 5", "Sala 6", "Sala 7", "Consultorios Externos",
    ]
    for nombre in hospital:
        assert servicios[nombre].activo and not servicios[nombre].externo, nombre
    assert servicios["Pediatría"].activo  # queda activo hasta confirmar su planilla
    assert not servicios["Otro"].activo


def test_centros_externos_marcados(db_pg):
    externos = {s.nombre for s in db_pg.scalars(select(Servicio).where(Servicio.externo.is_(True)))}
    assert externos == {
        "Aguilares", "Monteros", "Alberdi", "Área Programática",
        "Sanatorio privado A", "Sanatorio privado B", "Sanatorio privado C",
    }


def test_dias_de_aireacion_por_servicio(db_pg):
    servicios = _servicios(db_pg)
    assert servicios["Neonatología"].dias_aireacion == 10
    assert servicios["Pediatría"].dias_aireacion == 7
    assert servicios["Guardia Pediátrica"].dias_aireacion == 7
    otros = [s for n, s in servicios.items() if n not in ("Neonatología", "Pediatría", "Guardia Pediátrica")]
    assert {s.dias_aireacion for s in otros} == {3}


# ---------------------------------------------------------------------------
# Métodos y programas
# ---------------------------------------------------------------------------


def test_metodos_aireacion_y_vencimiento(db_pg):
    valores = {
        m.nombre: (m.requiere_aireacion, m.vencimiento_dias) for m in db_pg.scalars(select(MetodoEsterilizacion))
    }
    assert valores == {
        "Calor húmedo": (False, 90),
        "Calor seco": (False, 90),
        "Óxido de etileno": (True, 365),
    }


@pytest.mark.parametrize(
    ("nombre", "metodo", "valores"),
    [
        ("Instrumental 134 °C", "Calor húmedo", (134, 20, 30, None, Decimal("-0.75"), Decimal("1.00"), 1)),
        ("Textil 134 °C", "Calor húmedo", (134, 10, 10, None, Decimal("-0.75"), Decimal("1.00"), 2)),
        ("Termolábil 121 °C", "Calor húmedo", (121, 20, 20, None, Decimal("-0.75"), Decimal("0.80"), 2)),
        ("Líquidos 121 °C", "Calor húmedo", (121, 20, 0, None, Decimal("-0.40"), Decimal("0.00"), 0)),
        ("Priones 134 °C", "Calor húmedo", (134, 60, 20, None, Decimal("-0.75"), Decimal("1.00"), 2)),
        ("A 160 °C", "Calor seco", (160, 120, None, None, None, None, None)),
        ("B 170 °C", "Calor seco", (170, 90, None, None, None, None, None)),
        ("C 180 °C", "Calor seco", (180, 60, None, None, None, None, None)),
        ("P programable", "Calor seco", (None, None, None, None, None, None, None)),
        ("Ciclo caliente 55 °C", "Óxido de etileno", (55, 180, None, 720, None, None, None)),
    ],
)
def test_programas_con_sus_valores_y_su_metodo(db_pg, nombre, metodo, valores):
    programa = db_pg.scalar(select(Programa).where(Programa.nombre == nombre))
    assert programa is not None, nombre
    assert programa.metodo_id == _metodo(db_pg, metodo).id
    obtenidos = (
        programa.temperatura_c, programa.tiempo_esterilizacion_min, programa.tiempo_secado_min,
        programa.tiempo_desgasificacion_min, programa.vacio_bar, programa.vapor_bar, programa.pulsos,
    )
    assert obtenidos == valores


def test_gomas_quedo_como_termolabil_en_la_misma_fila(db_pg):
    assert db_pg.scalar(select(Programa).where(Programa.nombre == "Gomas 121 °C")) is None
    termolabil = db_pg.scalar(select(Programa.id).where(Programa.nombre == "Termolábil 121 °C"))
    liquidos = db_pg.scalar(select(Programa.id).where(Programa.nombre == "Líquidos 121 °C"))
    # Sin ids fijos: la fila renombrada es anterior a los programas que agrega la 0010
    assert termolabil < liquidos
    assert db_pg.scalar(select(Programa).where(Programa.nombre == "Termolábil 121 °C")).metodo_id == _metodo(
        db_pg, "Calor húmedo"
    ).id


# ---------------------------------------------------------------------------
# Incompatibilidad, material "Otros", ítem y lote
# ---------------------------------------------------------------------------


def test_neo_uti_incompatibles_solo_en_oxido_de_etileno(db_pg):
    servicios = _servicios(db_pg)
    filas = list(db_pg.scalars(select(ServicioIncompatible)))
    assert [(f.servicio_a_id, f.servicio_b_id, f.metodo_id) for f in filas] == [
        (servicios["Neonatología"].id, servicios["Unidad de Terapia Intensiva"].id, _metodo(db_pg, "Óxido de etileno").id)
    ]


def test_material_otros_y_campos_nuevos_del_item(db_pg, servicio):
    otros = db_pg.scalar(select(Material).where(Material.nombre == "Otros"))
    assert otros is not None and otros.activo
    recepcion = Recepcion(servicio_id=servicio.id, completo=True)
    db_pg.add(recepcion)
    db_pg.flush()
    item = Item(recepcion_id=recepcion.id, material_id=otros.id, descripcion="Bandeja de prueba", cantidad_piezas=12)
    db_pg.add(item)
    db_pg.flush()
    assert (item.descripcion, item.cantidad_piezas) == ("Bandeja de prueba", 12)


def test_cantidad_de_piezas_tiene_que_ser_positiva(db_pg, servicio, materiales):
    recepcion = Recepcion(servicio_id=servicio.id, completo=True)
    db_pg.add(recepcion)
    db_pg.flush()
    with pytest.raises(IntegrityError, match="ck_item_cantidad_piezas_positiva"):
        with db_pg.begin_nested():
            db_pg.add(Item(recepcion_id=recepcion.id, material_id=materiales[0].id, cantidad_piezas=0))
            db_pg.flush()


def test_lote_guarda_numero_de_ciclo(db_pg, operador):
    equipo = db_pg.scalar(select(Equipo).where(Equipo.nombre == "Autoclave 1"))
    programa = db_pg.scalar(select(Programa).where(Programa.nombre == "Textil 134 °C"))
    lote = Lote(numero=1, equipo_id=equipo.id, programa_id=programa.id, operador_id=operador.id, numero_ciclo="1187")
    db_pg.add(lote)
    db_pg.flush()
    db_pg.refresh(lote)
    assert lote.numero_ciclo == "1187"


# ---------------------------------------------------------------------------
# evento_item: unicidad (item, etapa, lote, intento)
# ---------------------------------------------------------------------------


def _item_recibido(db, operador, servicio, material):
    recepcion = Recepcion(servicio_id=servicio.id, completo=True)
    db.add(recepcion)
    db.flush()
    item = Item(recepcion_id=recepcion.id, material_id=material.id)
    db.add(item)
    db.flush()
    return item


def _etapa(db, orden):
    return db.scalar(select(Etapa.id).where(Etapa.orden == orden))


def test_misma_etapa_dos_veces_con_el_mismo_intento_se_rechaza(db_pg, operador, servicio, materiales):
    item = _item_recibido(db_pg, operador, servicio, materiales[0])
    db_pg.add(EventoItem(item_id=item.id, etapa_id=_etapa(db_pg, 3), operador_id=operador.id))
    db_pg.flush()
    with pytest.raises(IntegrityError, match="uq_evento_item_etapa_lote_intento"):
        with db_pg.begin_nested():
            db_pg.add(EventoItem(item_id=item.id, etapa_id=_etapa(db_pg, 3), operador_id=operador.id))
            db_pg.flush()


def test_reempaque_con_intento_2_se_acepta(db_pg, operador, servicio, materiales):
    item = _item_recibido(db_pg, operador, servicio, materiales[0])
    db_pg.add(EventoItem(item_id=item.id, etapa_id=_etapa(db_pg, 3), operador_id=operador.id))
    db_pg.add(EventoItem(item_id=item.id, etapa_id=_etapa(db_pg, 3), operador_id=operador.id, intento=2))
    db_pg.flush()
    intentos = sorted(e.intento for e in db_pg.scalars(select(EventoItem).where(EventoItem.item_id == item.id)))
    assert intentos == [1, 2]


def test_reesterilizacion_actual_sigue_con_intento_1(db_pg, operador, servicio, materiales):
    """Dos Esterilización con lotes distintos e intento 1: como antes de la 0010."""
    equipo = db_pg.scalar(select(Equipo).where(Equipo.nombre == "Autoclave 1"))
    programa = db_pg.scalar(select(Programa).where(Programa.metodo_id == equipo.metodo_id).order_by(Programa.id))
    lotes = []
    for numero in (1, 2):
        lote = Lote(numero=numero, equipo_id=equipo.id, programa_id=programa.id, operador_id=operador.id)
        db_pg.add(lote)
        db_pg.flush()
        lotes.append(lote)
    item = _item_recibido(db_pg, operador, servicio, materiales[0])
    for lote in lotes:
        db_pg.add(EventoItem(item_id=item.id, etapa_id=_etapa(db_pg, 4), operador_id=operador.id, lote_id=lote.id))
    db_pg.flush()
    eventos = list(db_pg.scalars(select(EventoItem).where(EventoItem.item_id == item.id)))
    assert [e.intento for e in eventos] == [1, 1]


# ---------------------------------------------------------------------------
# control_bowie_dick
# ---------------------------------------------------------------------------


def test_bowie_dick_fallido_requiere_motivo(db_pg, operador):
    equipo = db_pg.scalar(select(Equipo).where(Equipo.nombre == "Autoclave 1"))
    with pytest.raises(IntegrityError, match="ck_bowie_dick_fallido_requiere_motivo"):
        with db_pg.begin_nested():
            db_pg.add(ControlBowieDick(equipo_id=equipo.id, operador_id=operador.id, resultado="fallido"))
            db_pg.flush()


def test_bowie_dick_resultado_valido(db_pg, operador):
    equipo = db_pg.scalar(select(Equipo).where(Equipo.nombre == "Autoclave 1"))
    with pytest.raises(IntegrityError, match="ck_bowie_dick_resultado_valido"):
        with db_pg.begin_nested():
            db_pg.add(ControlBowieDick(equipo_id=equipo.id, operador_id=operador.id, resultado="dudoso"))
            db_pg.flush()
