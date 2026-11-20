import pytest
from sqlalchemy import event, select

from app.models import Equipo, Etapa, EventoItem, Item, Lote, Programa, Recepcion
from app.services.flujo import (
    ErrorDeFlujo,
    situacion_del_item,
    situaciones_de_items,
    validar_avance,
    validar_avance_varios,
)

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


def _nuevo_item(db, operador, servicio, material):
    """Ítem recién recibido, con su evento de Recepción."""
    recepcion = Recepcion(servicio_id=servicio.id, completo=True)
    db.add(recepcion)
    db.flush()
    nuevo = Item(recepcion_id=recepcion.id, material_id=material.id)
    db.add(nuevo)
    db.flush()
    _evento(db, nuevo, operador, 1)
    return nuevo


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
    
def test_situaciones_de_varios_items(db_pg, operador, servicio, materiales, autoclave):
    recien = _nuevo_item(db_pg, operador, servicio, materiales[0])
    avanzado = _nuevo_item(db_pg, operador, servicio, materiales[0])
    _evento(db_pg, avanzado, operador, 2)
    _evento(db_pg, avanzado, operador, 3)
    fallido = _nuevo_item(db_pg, operador, servicio, materiales[0])
    _hasta_esterilizacion(db_pg, fallido, operador, _lote(db_pg, operador, autoclave, resultado="fallido"))

    situaciones = situaciones_de_items(db_pg, [fallido.id, recien.id, avanzado.id, recien.id])

    assert list(situaciones) == sorted({recien.id, avanzado.id, fallido.id})
    assert (situaciones[recien.id].orden_etapa, situaciones[recien.id].resultado_ultimo_lote) == (1, None)
    assert (situaciones[avanzado.id].orden_etapa, situaciones[avanzado.id].resultado_ultimo_lote) == (3, None)
    assert (situaciones[fallido.id].orden_etapa, situaciones[fallido.id].resultado_ultimo_lote) == (4, "fallido")


def test_situaciones_lista_vacia(db_pg):
    assert situaciones_de_items(db_pg, []) == {}


def test_situaciones_item_inexistente(db_pg, operador, servicio, materiales):
    existente = _nuevo_item(db_pg, operador, servicio, materiales[0])
    with pytest.raises(ErrorDeFlujo, match="999999"):
        situaciones_de_items(db_pg, [existente.id, 999999])


def test_situaciones_usa_una_sola_consulta(db_pg, operador, servicio, materiales):
    items = [_nuevo_item(db_pg, operador, servicio, materiales[0]) for _ in range(3)]
    consultas = []

    def contar(conexion, cursor, statement, parameters, context, executemany):
        consultas.append(statement)

    conexion = db_pg.get_bind()
    event.listen(conexion, "before_cursor_execute", contar)
    try:
        situaciones_de_items(db_pg, [i.id for i in items])
    finally:
        event.remove(conexion, "before_cursor_execute", contar)
    assert len(consultas) == 1


def test_validar_avance_varios_permite_avanzar(db_pg, operador, servicio, materiales):
    items = [_nuevo_item(db_pg, operador, servicio, materiales[0]) for _ in range(2)]
    validar_avance_varios(db_pg, [i.id for i in items], 2)  # no debe lanzar nada


def test_validar_avance_varios_indica_el_item_que_falla(db_pg, operador, servicio, materiales):
    bien = _nuevo_item(db_pg, operador, servicio, materiales[0])
    adelantado = _nuevo_item(db_pg, operador, servicio, materiales[0])
    _evento(db_pg, adelantado, operador, 2)  # ya está en Lavado: no puede volver a pasar a Lavado
    with pytest.raises(ErrorDeFlujo, match=f"Ítem {adelantado.id}"):
        validar_avance_varios(db_pg, [bien.id, adelantado.id], 2)


def test_validar_avance_varios_respeta_el_resultado_del_lote(db_pg, operador, servicio, materiales, autoclave):
    aprobado = _nuevo_item(db_pg, operador, servicio, materiales[0])
    _hasta_esterilizacion(db_pg, aprobado, operador, _lote(db_pg, operador, autoclave, numero=1, resultado="aprobado"))
    fallido = _nuevo_item(db_pg, operador, servicio, materiales[0])
    _hasta_esterilizacion(db_pg, fallido, operador, _lote(db_pg, operador, autoclave, numero=2, resultado="fallido"))
    with pytest.raises(ErrorDeFlujo, match=f"Ítem {fallido.id}.*fallido"):
        validar_avance_varios(db_pg, [aprobado.id, fallido.id], 5)