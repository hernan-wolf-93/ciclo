"""Lecturas de catálogo (servicios, materiales, equipos y programas) y propuesta
de número de lote. Corren contra ciclo_test: los catálogos vienen de las migraciones."""

import pytest
from sqlalchemy import select

from app.api.deps import obtener_operador_actual
from app.main import app
from app.models import Lote
from app.models.catalogos import Equipo, Material, MetodoEsterilizacion, Programa, Servicio


@pytest.fixture
def con_sesion(cliente_pg, operador):
    """Cliente con sesión iniciada. Reemplaza solo la identificación del operador;
    cliente_pg limpia los reemplazos al terminar."""
    app.dependency_overrides[obtener_operador_actual] = lambda: operador
    return cliente_pg


def _equipo_con_programa(db_pg, nombre="Equipo de prueba"):
    metodo = db_pg.scalars(select(MetodoEsterilizacion).order_by(MetodoEsterilizacion.id)).first()
    equipo = Equipo(nombre=nombre, metodo_id=metodo.id)
    programa = Programa(nombre=f"Programa de {nombre}", metodo_id=metodo.id)
    db_pg.add_all([equipo, programa])
    db_pg.commit()
    return equipo, programa


def _agregar_lote(db_pg, equipo, programa, operador, numero):
    db_pg.add(Lote(numero=numero, equipo_id=equipo.id, programa_id=programa.id, operador_id=operador.id))
    db_pg.commit()


# --- Acceso ---------------------------------------------------------------

@pytest.mark.parametrize(
    "ruta",
    ["/servicios", "/materiales", "/equipos", "/programas", "/equipos/1/proximo-numero"],
)
def test_sin_token_responde_401(cliente_pg, ruta):
    assert cliente_pg.get(ruta).status_code == 401


# --- Catálogos ------------------------------------------------------------

def test_servicios_solo_activos_con_dias_de_aireacion(con_sesion, db_pg):
    db_pg.add(Servicio(nombre="Servicio de prueba inactivo", activo=False))
    db_pg.commit()

    respuesta = con_sesion.get("/servicios")

    assert respuesta.status_code == 200
    filas = respuesta.json()
    esperados = db_pg.scalars(
        select(Servicio).where(Servicio.activo.is_(True)).order_by(Servicio.nombre)
    ).all()
    assert [f["id"] for f in filas] == [s.id for s in esperados]
    assert all(set(f) == {"id", "nombre", "dias_aireacion"} for f in filas)


def test_materiales_solo_activos_con_codigo_y_nombre_alternativo(con_sesion, db_pg):
    db_pg.add_all(
        [
            Material(nombre="Material de prueba inactivo", activo=False),
            Material(nombre="Material de prueba sin código"),
            Material(
                nombre="Material de prueba con dos nombres",
                codigo="ZZ9",
                nombre_alternativo="Nombre de cirugía de prueba",
            ),
        ]
    )
    db_pg.commit()

    respuesta = con_sesion.get("/materiales")

    assert respuesta.status_code == 200
    filas = respuesta.json()
    esperados = db_pg.scalars(
        select(Material).where(Material.activo.is_(True)).order_by(Material.nombre)
    ).all()
    assert [f["id"] for f in filas] == [m.id for m in esperados]
    assert all(set(f) == {"id", "nombre", "codigo", "nombre_alternativo"} for f in filas)
    por_nombre = {f["nombre"]: f for f in filas}
    assert "Material de prueba inactivo" not in por_nombre
    assert por_nombre["Material de prueba sin código"]["codigo"] is None
    con_dos = por_nombre["Material de prueba con dos nombres"]
    assert (con_dos["codigo"], con_dos["nombre_alternativo"]) == ("ZZ9", "Nombre de cirugía de prueba")


def test_equipos_activos_con_su_metodo(con_sesion, db_pg):
    metodo = db_pg.scalars(select(MetodoEsterilizacion).order_by(MetodoEsterilizacion.id)).first()
    db_pg.add(Equipo(nombre="Equipo de prueba inactivo", metodo_id=metodo.id, activo=False))
    db_pg.commit()

    respuesta = con_sesion.get("/equipos")

    assert respuesta.status_code == 200
    filas = respuesta.json()
    esperados = db_pg.execute(
        select(Equipo.id, MetodoEsterilizacion.nombre.label("metodo"))
        .join(MetodoEsterilizacion, MetodoEsterilizacion.id == Equipo.metodo_id)
        .where(Equipo.activo.is_(True))
        .order_by(Equipo.nombre)
    ).all()
    assert [(f["id"], f["metodo"]) for f in filas] == [(e.id, e.metodo) for e in esperados]
    assert all(set(f) == {"id", "nombre", "metodo_id", "metodo"} for f in filas)


# --- Programas ------------------------------------------------------------

def test_programas_de_un_equipo_son_solo_los_de_su_metodo(con_sesion, db_pg):
    equipo = db_pg.scalars(select(Equipo).where(Equipo.activo.is_(True)).order_by(Equipo.id)).first()
    otro_metodo = db_pg.scalars(
        select(MetodoEsterilizacion).where(MetodoEsterilizacion.id != equipo.metodo_id)
    ).first()
    db_pg.add_all(
        [
            Programa(nombre="Programa de prueba del mismo método", metodo_id=equipo.metodo_id),
            Programa(nombre="Programa de prueba de otro método", metodo_id=otro_metodo.id),
        ]
    )
    db_pg.commit()

    respuesta = con_sesion.get("/programas", params={"equipo_id": equipo.id})

    assert respuesta.status_code == 200
    filas = respuesta.json()
    assert {f["metodo_id"] for f in filas} == {equipo.metodo_id}
    nombres = {f["nombre"] for f in filas}
    assert "Programa de prueba del mismo método" in nombres
    assert "Programa de prueba de otro método" not in nombres
    assert all(set(f) == {"id", "nombre", "metodo_id"} for f in filas)


def test_programas_sin_filtro_devuelve_los_de_todos_los_metodos(con_sesion, db_pg):
    respuesta = con_sesion.get("/programas")

    assert respuesta.status_code == 200
    assert {f["id"] for f in respuesta.json()} == {p.id for p in db_pg.scalars(select(Programa))}


def test_programas_de_un_equipo_inexistente_responde_404(con_sesion):
    respuesta = con_sesion.get("/programas", params={"equipo_id": 999999})

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No existe el equipo 999999"


def test_programas_con_equipo_id_invalido_responde_422(con_sesion):
    assert con_sesion.get("/programas", params={"equipo_id": 0}).status_code == 422


# --- Propuesta del número de lote ----------------------------------------

def test_proximo_numero_de_un_equipo_sin_lotes_es_1(con_sesion, db_pg):
    equipo, _ = _equipo_con_programa(db_pg)

    respuesta = con_sesion.get(f"/equipos/{equipo.id}/proximo-numero")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"equipo_id": equipo.id, "numero": 1}


def test_proximo_numero_continua_el_ultimo_lote(con_sesion, db_pg, operador):
    equipo, programa = _equipo_con_programa(db_pg)
    _agregar_lote(db_pg, equipo, programa, operador, 41)

    assert con_sesion.get(f"/equipos/{equipo.id}/proximo-numero").json()["numero"] == 42


def test_proximo_numero_reinicia_despues_de_999(con_sesion, db_pg, operador):
    equipo, programa = _equipo_con_programa(db_pg)
    _agregar_lote(db_pg, equipo, programa, operador, 999)

    assert con_sesion.get(f"/equipos/{equipo.id}/proximo-numero").json()["numero"] == 1


def test_proximo_numero_es_por_equipo(con_sesion, db_pg, operador):
    equipo_a, programa_a = _equipo_con_programa(db_pg, "Equipo de prueba A")
    equipo_b, _ = _equipo_con_programa(db_pg, "Equipo de prueba B")
    _agregar_lote(db_pg, equipo_a, programa_a, operador, 500)

    assert con_sesion.get(f"/equipos/{equipo_b.id}/proximo-numero").json()["numero"] == 1


def test_proximo_numero_de_un_equipo_inexistente_responde_404(con_sesion):
    respuesta = con_sesion.get("/equipos/999999/proximo-numero")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No existe el equipo 999999"