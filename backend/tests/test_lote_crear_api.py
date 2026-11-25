"""POST /lotes: cargar un equipo de esterilización con el material empacado."""

from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.models import Etapa, EventoItem, Item, Lote
from app.models.catalogos import Equipo, MetodoEsterilizacion, Programa, Servicio

CLAVES = {"id", "numero", "equipo_id", "programa_id", "inicio", "total_items"}


def _kit(db, nombre_metodo):
    """Método, un equipo activo y un programa de ese método."""
    metodo = db.scalar(
        select(MetodoEsterilizacion).where(MetodoEsterilizacion.nombre == nombre_metodo)
    )
    equipo = db.scalar(
        select(Equipo)
        .where(Equipo.metodo_id == metodo.id, Equipo.activo.is_(True))
        .order_by(Equipo.id)
        .limit(1)
    )
    programa = db.scalar(
        select(Programa).where(Programa.metodo_id == metodo.id).order_by(Programa.id).limit(1)
    )
    return SimpleNamespace(metodo=metodo, equipo=equipo, programa=programa)


@pytest.fixture
def autoclave(db_pg):
    return _kit(db_pg, "Calor húmedo")


@pytest.fixture
def estufa(db_pg):
    return _kit(db_pg, "Calor seco")


@pytest.fixture
def oxido(db_pg):
    return _kit(db_pg, "Óxido de etileno")


def _cuerpo(kit, *lineas, numero=1, **cambios):
    """Cada línea es (servicio, material, cantidad)."""
    cuerpo = {
        "equipo_id": kit.equipo.id,
        "programa_id": kit.programa.id,
        "numero": numero,
        "lineas": [
            {"servicio_id": s.id, "material_id": m.id, "cantidad": c} for s, m, c in lineas
        ],
    }
    cuerpo.update(cambios)
    return cuerpo


def _bowie(cliente, kit, resultado="aprobado", observacion=None):
    cuerpo = {"resultado": resultado}
    if observacion:
        cuerpo["observacion"] = observacion
    respuesta = cliente.post(f"/equipos/{kit.equipo.id}/bowie-dick", json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text


def _contar(db, modelo):
    return db.scalar(select(func.count()).select_from(modelo))


def _servicio(db, nombre):
    return db.scalar(select(Servicio).where(Servicio.nombre == nombre))


# --- Acceso ---------------------------------------------------------------

def test_sin_token_responde_401(cliente_pg, estufa, servicio, materiales):
    r = cliente_pg.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 1)))

    assert r.status_code == 401


# --- Creación ---------------------------------------------------------------

def test_crea_el_lote_y_firma_cada_item(
    con_sesion, db_pg, operador, estufa, servicio, materiales, empacar
):
    ids = empacar(servicio, materiales[0], estufa.metodo, 3)

    r = con_sesion.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 3), numero=57))

    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert set(cuerpo) == CLAVES
    assert (cuerpo["numero"], cuerpo["equipo_id"], cuerpo["programa_id"], cuerpo["total_items"]) == (
        57,
        estufa.equipo.id,
        estufa.programa.id,
        3,
    )
    lote = db_pg.get(Lote, cuerpo["id"])
    assert lote.operador_id == operador.id
    assert lote.resultado is None and lote.fin is None
    assert set(db_pg.scalars(select(Item.id).where(Item.lote_id == lote.id))) == set(ids)
    eventos = list(db_pg.scalars(select(EventoItem).where(EventoItem.lote_id == lote.id)))
    assert {e.item_id for e in eventos} == set(ids)
    assert {e.operador_id for e in eventos} == {operador.id}
    assert db_pg.scalar(select(Etapa.orden).where(Etapa.id == eventos[0].etapa_id)) == 4


def test_el_operador_sale_del_token_y_no_del_cuerpo(
    con_sesion, db_pg, operador, estufa, servicio, materiales, empacar
):
    empacar(servicio, materiales[0], estufa.metodo, 1)
    cuerpo = _cuerpo(estufa, (servicio, materiales[0], 1), operador_id=999999)

    r = con_sesion.post("/lotes", json=cuerpo)

    assert r.status_code == 201
    assert db_pg.get(Lote, r.json()["id"]).operador_id == operador.id


def test_toma_los_mas_antiguos_y_deja_el_resto(
    con_sesion, db_pg, estufa, servicio, materiales, empacar
):
    ids = empacar(servicio, materiales[0], estufa.metodo, 3)

    r = con_sesion.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 2)))

    assert r.status_code == 201
    cargados = set(db_pg.scalars(select(Item.id).where(Item.lote_id == r.json()["id"])))
    assert cargados == set(ids[:2])
    resto = con_sesion.get(f"/equipos/{estufa.equipo.id}/pendientes").json()
    assert [
        (f["material_id"], f["cantidad"]) for f in resto if f["servicio_id"] == servicio.id
    ] == [(materiales[0].id, 1)]


def test_la_propuesta_de_numero_continua_el_ultimo_lote(
    con_sesion, estufa, servicio, materiales, empacar
):
    empacar(servicio, materiales[0], estufa.metodo, 1)
    con_sesion.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 1), numero=57))

    r = con_sesion.get(f"/equipos/{estufa.equipo.id}/proximo-numero")

    assert r.json()["numero"] == 58


def test_el_numero_puede_repetirse(con_sesion, estufa, servicio, materiales, empacar):
    empacar(servicio, materiales[0], estufa.metodo, 2)

    primero = con_sesion.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 1), numero=5))
    segundo = con_sesion.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 1), numero=5))

    assert (primero.status_code, segundo.status_code) == (201, 201)
    assert primero.json()["id"] != segundo.json()["id"]


# --- Equipo y programa -----------------------------------------------------

def test_programa_de_otro_metodo_se_rechaza(
    con_sesion, db_pg, estufa, autoclave, servicio, materiales, empacar
):
    empacar(servicio, materiales[0], estufa.metodo, 1)
    cuerpo = _cuerpo(estufa, (servicio, materiales[0], 1), programa_id=autoclave.programa.id)
    antes = _contar(db_pg, Lote)

    r = con_sesion.post("/lotes", json=cuerpo)

    assert r.status_code == 422
    assert "programa" in r.json()["detail"].lower()
    assert _contar(db_pg, Lote) == antes


def test_programa_inexistente_se_rechaza(con_sesion, estufa, servicio, materiales, empacar):
    empacar(servicio, materiales[0], estufa.metodo, 1)

    r = con_sesion.post(
        "/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 1), programa_id=999999)
    )

    assert r.status_code == 422
    assert r.json()["detail"] == "No existe el programa 999999"


def test_equipo_inexistente_responde_404(con_sesion, estufa, servicio, materiales):
    r = con_sesion.post(
        "/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 1), equipo_id=999999)
    )

    assert r.status_code == 404
    assert r.json()["detail"] == "No existe el equipo 999999"


def test_equipo_dado_de_baja_se_rechaza(
    con_sesion, db_pg, estufa, servicio, materiales, empacar
):
    empacar(servicio, materiales[0], estufa.metodo, 1)
    estufa.equipo.activo = False
    db_pg.commit()

    r = con_sesion.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 1)))

    assert r.status_code == 422
    assert "baja" in r.json()["detail"]


# --- Bowie-Dick -------------------------------------------------------------

def test_autoclave_sin_bowie_dick_hoy_se_rechaza(
    con_sesion, db_pg, autoclave, servicio, materiales, empacar
):
    empacar(servicio, materiales[0], autoclave.metodo, 1)
    antes = _contar(db_pg, Lote)

    r = con_sesion.post("/lotes", json=_cuerpo(autoclave, (servicio, materiales[0], 1)))

    assert r.status_code == 422
    assert "Bowie-Dick" in r.json()["detail"]
    assert _contar(db_pg, Lote) == antes


def test_autoclave_con_bowie_dick_aprobado_crea_el_lote(
    con_sesion, autoclave, servicio, materiales, empacar
):
    empacar(servicio, materiales[0], autoclave.metodo, 1)
    _bowie(con_sesion, autoclave)

    r = con_sesion.post("/lotes", json=_cuerpo(autoclave, (servicio, materiales[0], 1)))

    assert r.status_code == 201, r.text


def test_autoclave_con_el_ultimo_bowie_dick_fallido_se_rechaza(
    con_sesion, autoclave, servicio, materiales, empacar
):
    empacar(servicio, materiales[0], autoclave.metodo, 1)
    _bowie(con_sesion, autoclave)
    _bowie(con_sesion, autoclave, "fallido", "Repetir el control")

    r = con_sesion.post("/lotes", json=_cuerpo(autoclave, (servicio, materiales[0], 1)))

    assert r.status_code == 422
    assert "Bowie-Dick" in r.json()["detail"]


# --- Elección de ítems ------------------------------------------------------

def test_pedir_mas_de_lo_disponible_rechaza_todo_el_pedido(
    con_sesion, db_pg, estufa, servicio, materiales, empacar
):
    empacar(servicio, materiales[0], estufa.metodo, 1)
    empacar(servicio, materiales[1], estufa.metodo, 1)
    antes = _contar(db_pg, Lote)

    r = con_sesion.post(
        "/lotes",
        json=_cuerpo(estufa, (servicio, materiales[0], 1), (servicio, materiales[1], 5)),
    )

    assert r.status_code == 422
    assert "solo hay 1" in r.json()["detail"]
    assert _contar(db_pg, Lote) == antes
    assert db_pg.scalar(select(func.count()).select_from(Item).where(Item.lote_id.is_not(None))) == 0


def test_material_empacado_para_otro_metodo_no_esta_disponible(
    con_sesion, estufa, autoclave, servicio, materiales, empacar
):
    empacar(servicio, materiales[0], autoclave.metodo, 1)

    r = con_sesion.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 1)))

    assert r.status_code == 422
    assert "solo hay 0" in r.json()["detail"]


@pytest.mark.parametrize("resultado", ["aprobado", None], ids=["aprobado", "en curso"])
def test_items_de_un_lote_aprobado_o_en_curso_no_se_cargan_de_nuevo(
    con_sesion, cargar_lote, estufa, servicio, materiales, empacar, resultado
):
    ids = empacar(servicio, materiales[0], estufa.metodo, 2)
    cargar_lote(estufa.equipo, ids, resultado=resultado)

    r = con_sesion.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 2), numero=2))

    assert r.status_code == 422
    assert "solo hay 0" in r.json()["detail"]


def test_reesterilizacion_de_un_lote_fallido(
    con_sesion, db_pg, cargar_lote, estufa, servicio, materiales, empacar
):
    ids = empacar(servicio, materiales[0], estufa.metodo, 2)
    anterior = cargar_lote(estufa.equipo, ids, resultado="fallido", numero=1)

    r = con_sesion.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 2), numero=2))

    assert r.status_code == 201, r.text
    nuevo = r.json()["id"]
    assert set(db_pg.scalars(select(Item.id).where(Item.lote_id == nuevo))) == set(ids)
    for item_id in ids:
        lotes = set(
            db_pg.scalars(
                select(EventoItem.lote_id).where(
                    EventoItem.item_id == item_id, EventoItem.lote_id.is_not(None)
                )
            )
        )
        assert lotes == {anterior.id, nuevo}


# --- Servicios incompatibles -----------------------------------------------

def test_neonatologia_y_uti_no_se_mezclan_en_oxido_de_etileno(
    con_sesion, db_pg, oxido, materiales, empacar
):
    neo = _servicio(db_pg, "Neonatología")
    uti = _servicio(db_pg, "Unidad de Terapia Intensiva")
    empacar(neo, materiales[0], oxido.metodo, 1)
    empacar(uti, materiales[0], oxido.metodo, 1)

    r = con_sesion.post(
        "/lotes", json=_cuerpo(oxido, (neo, materiales[0], 1), (uti, materiales[0], 1))
    )

    assert r.status_code == 422
    assert "mismo lote" in r.json()["detail"]


def test_neonatologia_y_uti_si_pueden_ir_juntos_en_estufa(
    con_sesion, db_pg, estufa, materiales, empacar
):
    neo = _servicio(db_pg, "Neonatología")
    uti = _servicio(db_pg, "Unidad de Terapia Intensiva")
    empacar(neo, materiales[0], estufa.metodo, 1)
    empacar(uti, materiales[0], estufa.metodo, 1)

    r = con_sesion.post(
        "/lotes", json=_cuerpo(estufa, (neo, materiales[0], 1), (uti, materiales[0], 1))
    )

    assert r.status_code == 201, r.text


# --- Cuerpo inválido --------------------------------------------------------

def test_cuerpo_invalido_responde_422_y_no_guarda(
    con_sesion, db_pg, estufa, servicio, materiales, empacar
):
    empacar(servicio, materiales[0], estufa.metodo, 1)
    antes = _contar(db_pg, Lote)

    r = con_sesion.post("/lotes", json=_cuerpo(estufa, (servicio, materiales[0], 1), numero=0))

    assert r.status_code == 422
    assert _contar(db_pg, Lote) == antes