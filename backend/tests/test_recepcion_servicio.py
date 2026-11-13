import pytest
from sqlalchemy import func, select

from app.models import Etapa, EventoItem, Item, Recepcion
from app.schemas.recepcion import RecepcionIn
from app.services.recepcion import ErrorDeRecepcion, registrar_recepcion


def _contar(db, modelo):
    return db.scalar(select(func.count()).select_from(modelo))


def test_registra_recepcion_con_items_y_eventos(db_pg, operador, servicio, materiales):
    datos = RecepcionIn(
        servicio_id=servicio.id,
        items=[
            {"material_id": materiales[0].id, "cantidad": 2},
            {"material_id": materiales[1].id, "cantidad": 3},
        ],
        completo=True,
    )
    recepcion, total = registrar_recepcion(db_pg, operador, datos)

    assert total == 5
    assert recepcion.fecha_hora is not None
    items = list(db_pg.scalars(select(Item).where(Item.recepcion_id == recepcion.id)))
    assert sorted(i.material_id for i in items) == sorted(
        [materiales[0].id] * 2 + [materiales[1].id] * 3
    )
    assert all(i.metodo_id is None and i.lote_id is None and i.entrega_id is None for i in items)

    eventos = list(db_pg.scalars(select(EventoItem).where(EventoItem.item_id.in_([i.id for i in items]))))
    etapa_recepcion = db_pg.scalar(select(Etapa.id).where(Etapa.orden == 1))
    assert len(eventos) == 5
    assert {e.operador_id for e in eventos} == {operador.id}
    assert {e.etapa_id for e in eventos} == {etapa_recepcion}
    assert {e.lote_id for e in eventos} == {None}


def test_guarda_incompleta_y_urgente(db_pg, operador, servicio, materiales):
    datos = RecepcionIn(
        servicio_id=servicio.id,
        items=[{"material_id": materiales[0].id, "cantidad": 1}],
        completo=False,
        servicio_avisado=True,
        observacion="Falta una pinza",
        urgente=True,
    )
    recepcion, _ = registrar_recepcion(db_pg, operador, datos)
    assert recepcion.completo is False
    assert recepcion.servicio_avisado is True
    assert recepcion.observacion == "Falta una pinza"
    assert recepcion.urgente is True


def test_rechaza_servicio_inexistente(db_pg, operador, materiales):
    datos = RecepcionIn(
        servicio_id=999999, items=[{"material_id": materiales[0].id, "cantidad": 1}], completo=True
    )
    with pytest.raises(ErrorDeRecepcion, match="servicio de origen"):
        registrar_recepcion(db_pg, operador, datos)


def test_rechaza_servicio_dado_de_baja(db_pg, operador, servicio, materiales):
    servicio.activo = False
    db_pg.commit()
    datos = RecepcionIn(
        servicio_id=servicio.id, items=[{"material_id": materiales[0].id, "cantidad": 1}], completo=True
    )
    with pytest.raises(ErrorDeRecepcion, match="servicio de origen"):
        registrar_recepcion(db_pg, operador, datos)


def test_rechaza_material_inexistente(db_pg, operador, servicio):
    datos = RecepcionIn(
        servicio_id=servicio.id, items=[{"material_id": 999999, "cantidad": 1}], completo=True
    )
    with pytest.raises(ErrorDeRecepcion, match="Materiales"):
        registrar_recepcion(db_pg, operador, datos)


def test_rechaza_material_dado_de_baja(db_pg, operador, servicio, materiales):
    materiales[1].activo = False
    db_pg.commit()
    datos = RecepcionIn(
        servicio_id=servicio.id,
        items=[
            {"material_id": materiales[0].id, "cantidad": 1},
            {"material_id": materiales[1].id, "cantidad": 1},
        ],
        completo=True,
    )
    antes = _contar(db_pg, Recepcion)
    with pytest.raises(ErrorDeRecepcion, match="Materiales"):
        registrar_recepcion(db_pg, operador, datos)
    assert _contar(db_pg, Recepcion) == antes  # una línea mala no deja la recepción a medias


def test_si_falla_a_mitad_no_queda_nada(db_pg, operador, servicio, materiales, monkeypatch):
    def falla(**_):
        raise RuntimeError("fallo simulado")

    # Rompe la creación de eventos, cuando la recepción y los ítems ya están insertados.
    monkeypatch.setattr("app.services.recepcion.EventoItem", falla)
    datos = RecepcionIn(
        servicio_id=servicio.id, items=[{"material_id": materiales[0].id, "cantidad": 3}], completo=True
    )
    recepciones, items = _contar(db_pg, Recepcion), _contar(db_pg, Item)

    with pytest.raises(RuntimeError):
        registrar_recepcion(db_pg, operador, datos)

    assert _contar(db_pg, Recepcion) == recepciones
    assert _contar(db_pg, Item) == items