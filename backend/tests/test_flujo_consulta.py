import pytest
from sqlalchemy import select

from app.models import Equipo, Etapa, EventoItem, Item, Lote, Programa, Recepcion
from app.services.flujo import ErrorDeFlujo, situacion_del_item, validar_avance


@pytest.fixture
def item(db_pg, operador, servicio, materiales):
    """Ítem recién recibido, con su evento de Recepción como lo crea el servicio real."""
    recepcion = Recepcion(servicio_id=servicio.id, completo=True)
    db_pg.add(recepcion)
    db_pg.flush()
    nuevo = Item(recepcion_id=recepcion.id, material_id=materiales[0].id)
    db_pg.add(nuevo)
    db_pg.flush()
    _evento(db_pg, nuevo, operador, 1)
    return nuevo


@pytest.fixture
def autoclave(db_pg):
    equipo = db_pg.scalar(select(Equipo).where(Equipo.nombre == "Autoclave 1"))
    programa = db_pg.scalar(select(Programa).where(Programa.metodo_id == equipo.metodo_id))
    return equipo, programa


def _evento(db, item, operador, orden, lote=None):
    etapa = db.scalar(select(Etapa).where(Etapa.orden == orden))
    db.add(
        EventoItem(
            item_id=item.id,
            etapa_id=etapa.id,
            operador_id=operador.id,
            lote_id=lote.id if lote else None,
        )
    )
    db.flush()


def _lote(db, operador, autoclave, numero=1, resultado=None):
    equipo, programa = autoclave
    lote = Lote(
        numero=numero,
        equipo_id=equipo.id,
        programa_id=programa.id,
        operador_id=operador.id,
        resultado=resultado,
        observacion="Indicador biológico positivo" if resultado == "fallido" else None,
    )
    db.add(lote)
    db.flush()
    return lote


def _hasta_esterilizacion(db, item, operador, lote):
    _evento(db, item, operador, 2)
    _evento(db, item, operador, 3)
    _evento(db, item, operador, 4, lote)


def test_item_recien_recibido(db_pg, item):
    situacion = situacion_del_item(db_pg, item.id)
    assert (situacion.orden_etapa, situacion.resultado_ultimo_lote) == (1, None)


def test_item_avanzado_sin_lote(db_pg, operador, item):
    _evento(db_pg, item, operador, 2)
    _evento(db_pg, item, operador, 3)
    situacion = situacion_del_item(db_pg, item.id)
    assert (situacion.orden_etapa, situacion.resultado_ultimo_lote) == (3, None)


def test_lote_en_curso(db_pg, operador, item, autoclave):
    _hasta_esterilizacion(db_pg, item, operador, _lote(db_pg, operador, autoclave))
    situacion = situacion_del_item(db_pg, item.id)
    assert (situacion.orden_etapa, situacion.resultado_ultimo_lote) == (4, None)


def test_lote_aprobado(db_pg, operador, item, autoclave):
    _hasta_esterilizacion(db_pg, item, operador, _lote(db_pg, operador, autoclave, resultado="aprobado"))
    assert situacion_del_item(db_pg, item.id).resultado_ultimo_lote == "aprobado"


def test_lote_fallido(db_pg, operador, item, autoclave):
    _hasta_esterilizacion(db_pg, item, operador, _lote(db_pg, operador, autoclave, resultado="fallido"))
    assert situacion_del_item(db_pg, item.id).resultado_ultimo_lote == "fallido"


def test_reesterilizacion_toma_el_ultimo_lote(db_pg, operador, item, autoclave):
    fallido = _lote(db_pg, operador, autoclave, numero=1, resultado="fallido")
    nuevo = _lote(db_pg, operador, autoclave, numero=2)  # en curso
    _hasta_esterilizacion(db_pg, item, operador, fallido)
    _evento(db_pg, item, operador, 4, nuevo)

    # Todos los eventos comparten fecha_hora (misma transacción): por eso se ordena por id.
    eventos = list(db_pg.scalars(select(EventoItem).where(EventoItem.item_id == item.id)))
    assert len({e.fecha_hora for e in eventos}) == 1

    situacion = situacion_del_item(db_pg, item.id)
    assert (situacion.orden_etapa, situacion.resultado_ultimo_lote) == (4, None)


def test_item_sin_historial(db_pg):
    with pytest.raises(ErrorDeFlujo, match="no existe"):
        situacion_del_item(db_pg, 999999)


def test_validar_avance_lote_fallido_permite_reesterilizar(db_pg, operador, item, autoclave):
    _hasta_esterilizacion(db_pg, item, operador, _lote(db_pg, operador, autoclave, resultado="fallido"))
    validar_avance(db_pg, item.id, 4)  # no debe lanzar nada


def test_validar_avance_lote_fallido_no_va_a_almacen(db_pg, operador, item, autoclave):
    _hasta_esterilizacion(db_pg, item, operador, _lote(db_pg, operador, autoclave, resultado="fallido"))
    with pytest.raises(ErrorDeFlujo, match="fallido"):
        validar_avance(db_pg, item.id, 5)


def test_validar_avance_lote_aprobado_va_a_almacen(db_pg, operador, item, autoclave):
    _hasta_esterilizacion(db_pg, item, operador, _lote(db_pg, operador, autoclave, resultado="aprobado"))
    validar_avance(db_pg, item.id, 5)  # no debe lanzar nada