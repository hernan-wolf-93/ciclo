"""ABM de servicios y materiales (tarjeta 5, RF1). Corren contra ciclo_test.

Alta, modificación, baja y reactivación por PATCH (baja lógica), duplicados,
validaciones y permisos: solo administradores modifican; cualquier usuario con
sesión consulta. Todos los datos son ficticios.
"""

import pytest
from sqlalchemy import select

from app.api.deps import obtener_operador_actual
from app.main import app
from app.models import Material, Operador, Rol, Servicio

CLAVES_SERVICIO_ADMIN = {"id", "nombre", "externo", "dias_aireacion", "activo"}
CLAVES_MATERIAL_ADMIN = {"id", "nombre", "codigo", "nombre_alternativo", "activo"}


@pytest.fixture
def con_admin(cliente_pg, db_pg):
    """Cliente con sesión de un administrador principal ficticio."""
    rol = db_pg.scalar(select(Rol).where(Rol.nombre == "Administrador principal"))
    admin = Operador(numero_operador="T-ADM1", contrasena_hash="hash-de-prueba", rol_id=rol.id)
    db_pg.add(admin)
    db_pg.commit()
    app.dependency_overrides[obtener_operador_actual] = lambda: admin
    return cliente_pg


def _detalle(respuesta) -> str:
    """Mensaje de error: texto de la regla o el primero de pydantic."""
    detalle = respuesta.json()["detail"]
    return detalle if isinstance(detalle, str) else detalle[0]["msg"]


def _ids(respuesta) -> set[int]:
    return {fila["id"] for fila in respuesta.json()}


# ===========================================================================
# Permisos
# ===========================================================================


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("post", "/servicios", {"nombre": "Servicio de prueba"}),
        ("patch", "/servicios/1", {"activo": False}),
        ("get", "/servicios?incluir_inactivos=true", None),
        ("post", "/materiales", {"nombre": "Material de prueba"}),
        ("patch", "/materiales/1", {"activo": False}),
        ("get", "/materiales?incluir_inactivos=true", None),
    ],
)
def test_sin_token_responde_401(cliente_pg, metodo, ruta, cuerpo):
    respuesta = cliente_pg.request(metodo, ruta, json=cuerpo)
    assert respuesta.status_code == 401


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("post", "/servicios", {"nombre": "Servicio de prueba"}),
        ("patch", "/servicios/1", {"activo": False}),
        ("get", "/servicios?incluir_inactivos=true", None),
        ("post", "/materiales", {"nombre": "Material de prueba"}),
        ("patch", "/materiales/1", {"activo": False}),
        ("get", "/materiales?incluir_inactivos=true", None),
    ],
)
def test_operador_sin_rol_de_administrador_responde_403(con_sesion, metodo, ruta, cuerpo):
    respuesta = con_sesion.request(metodo, ruta, json=cuerpo)
    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "No tiene permiso para realizar esta acción"


def test_operador_sigue_consultando_los_activos(con_sesion):
    assert con_sesion.get("/servicios").status_code == 200
    assert con_sesion.get("/materiales").status_code == 200


# ===========================================================================
# Servicios
# ===========================================================================


def test_alta_de_servicio_con_valores_por_defecto(con_admin, db_pg):
    respuesta = con_admin.post("/servicios", json={"nombre": "  Servicio de prueba Norte  "})

    assert respuesta.status_code == 201
    creado = respuesta.json()
    assert set(creado) == CLAVES_SERVICIO_ADMIN
    assert (creado["nombre"], creado["externo"], creado["dias_aireacion"], creado["activo"]) == (
        "Servicio de prueba Norte", False, 3, True,
    )
    assert db_pg.get(Servicio, creado["id"]) is not None
    # Aparece en la consulta que usan las pantallas de operación
    assert creado["id"] in _ids(con_admin.get("/servicios"))


def test_alta_de_centro_externo_con_dias_de_aireacion(con_admin):
    respuesta = con_admin.post(
        "/servicios", json={"nombre": "Centro externo de prueba", "externo": True, "dias_aireacion": 7}
    )
    assert respuesta.status_code == 201
    assert (respuesta.json()["externo"], respuesta.json()["dias_aireacion"]) == (True, 7)


@pytest.mark.parametrize("nombre", ["Quirófano", "quirófano", "  QUIRÓFANO "])
def test_alta_de_servicio_con_nombre_repetido_responde_409(con_admin, nombre):
    respuesta = con_admin.post("/servicios", json={"nombre": nombre})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya existe un servicio con ese nombre"


@pytest.mark.parametrize(
    ("cuerpo", "mensaje"),
    [
        ({"nombre": "Servicio de prueba", "dias_aireacion": -1}, "Los días de aireación no pueden ser negativos"),
        ({"nombre": "Servicio de prueba", "dias_aireacion": 366}, "Los días de aireación pueden ser hasta 365"),
        ({"nombre": "   "}, "El nombre es obligatorio"),
        ({"nombre": "S" * 101}, "El nombre puede tener hasta 100 caracteres"),
    ],
)
def test_alta_de_servicio_con_datos_invalidos_responde_422(con_admin, cuerpo, mensaje):
    respuesta = con_admin.post("/servicios", json=cuerpo)
    assert respuesta.status_code == 422
    assert mensaje in _detalle(respuesta)


def test_alta_de_servicio_con_cero_dias_de_aireacion_se_acepta(con_admin):
    respuesta = con_admin.post("/servicios", json={"nombre": "Servicio de prueba", "dias_aireacion": 0})
    assert respuesta.status_code == 201


def test_alta_de_servicio_con_campo_desconocido_responde_422(con_admin):
    assert con_admin.post("/servicios", json={"nombre": "Servicio de prueba", "id": 5}).status_code == 422


def test_modificacion_de_servicio(con_admin):
    servicio = con_admin.post("/servicios", json={"nombre": "Servicio de prueba"}).json()

    respuesta = con_admin.patch(
        f"/servicios/{servicio['id']}",
        json={"nombre": "Servicio de prueba modificado", "externo": True, "dias_aireacion": 10},
    )

    assert respuesta.status_code == 200
    modificado = respuesta.json()
    assert (modificado["nombre"], modificado["externo"], modificado["dias_aireacion"]) == (
        "Servicio de prueba modificado", True, 10,
    )


def test_sanatorio_generico_toma_su_nombre_real_al_instalar(con_admin, db_pg):
    """RESPUESTAS-SERVICIO.md: los nombres reales se cargan desde el ABM (acá, uno ficticio)."""
    sanatorio = db_pg.scalar(select(Servicio).where(Servicio.nombre == "Sanatorio privado A"))

    respuesta = con_admin.patch(f"/servicios/{sanatorio.id}", json={"nombre": "Sanatorio de prueba del Sur"})

    assert respuesta.status_code == 200
    assert respuesta.json()["externo"] is True  # el resto de los datos no cambia


def test_modificar_solo_mayusculas_del_propio_nombre_se_acepta(con_admin):
    servicio = con_admin.post("/servicios", json={"nombre": "Servicio de prueba"}).json()
    respuesta = con_admin.patch(f"/servicios/{servicio['id']}", json={"nombre": "SERVICIO DE PRUEBA"})
    assert respuesta.status_code == 200


def test_modificar_servicio_con_nombre_de_otro_responde_409(con_admin):
    servicio = con_admin.post("/servicios", json={"nombre": "Servicio de prueba"}).json()
    respuesta = con_admin.patch(f"/servicios/{servicio['id']}", json={"nombre": "neonatología"})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya existe un servicio con ese nombre"


@pytest.mark.parametrize(
    ("cuerpo", "mensaje"),
    [
        ({}, "Hay que indicar al menos un cambio"),
        ({"nombre": None}, "El campo nombre no puede quedar vacío"),
        ({"dias_aireacion": -3}, "Los días de aireación no pueden ser negativos"),
    ],
)
def test_modificar_servicio_con_datos_invalidos_responde_422(con_admin, cuerpo, mensaje):
    servicio = con_admin.post("/servicios", json={"nombre": "Servicio de prueba"}).json()
    respuesta = con_admin.patch(f"/servicios/{servicio['id']}", json=cuerpo)
    assert respuesta.status_code == 422
    assert mensaje in _detalle(respuesta)


def test_modificar_servicio_inexistente_responde_404(con_admin):
    respuesta = con_admin.patch("/servicios/999999", json={"activo": False})
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No existe el servicio 999999"


def test_baja_y_reactivacion_de_servicio(con_admin, db_pg):
    servicio = con_admin.post("/servicios", json={"nombre": "Servicio de prueba"}).json()

    baja = con_admin.patch(f"/servicios/{servicio['id']}", json={"activo": False})
    assert baja.status_code == 200 and baja.json()["activo"] is False
    # Baja lógica: la fila sigue en la base
    assert db_pg.get(Servicio, servicio["id"]) is not None
    assert servicio["id"] not in _ids(con_admin.get("/servicios"))
    completos = {f["id"]: f for f in con_admin.get("/servicios?incluir_inactivos=true").json()}
    assert completos[servicio["id"]]["activo"] is False

    alta = con_admin.patch(f"/servicios/{servicio['id']}", json={"activo": True})
    assert alta.status_code == 200 and alta.json()["activo"] is True
    assert servicio["id"] in _ids(con_admin.get("/servicios"))


def test_lista_completa_de_servicios_para_el_abm(con_admin, db_pg):
    respuesta = con_admin.get("/servicios", params={"incluir_inactivos": True})

    assert respuesta.status_code == 200
    filas = respuesta.json()
    assert all(set(f) == CLAVES_SERVICIO_ADMIN for f in filas)
    assert _ids(respuesta) == {s.id for s in db_pg.scalars(select(Servicio))}
    assert any(not f["activo"] for f in filas)  # "Otro" quedó inactivo en la 0010
    assert any(f["externo"] for f in filas)


# ===========================================================================
# Materiales
# ===========================================================================


def test_alta_de_material_normaliza_el_codigo(con_admin, db_pg):
    respuesta = con_admin.post(
        "/materiales",
        json={"nombre": "Material de prueba", "codigo": " x 98 ", "nombre_alternativo": "Nombre de cirugía de prueba"},
    )

    assert respuesta.status_code == 201
    creado = respuesta.json()
    assert set(creado) == CLAVES_MATERIAL_ADMIN
    assert (creado["codigo"], creado["nombre_alternativo"], creado["activo"]) == (
        "X98", "Nombre de cirugía de prueba", True,
    )
    assert db_pg.get(Material, creado["id"]).codigo == "X98"
    # Aparece en GET /materiales, el que usan Lavado y Empaque
    assert creado["id"] in _ids(con_admin.get("/materiales"))


def test_alta_de_materiales_sin_codigo(con_admin):
    """El código es opcional y puede faltar en varios materiales."""
    a = con_admin.post("/materiales", json={"nombre": "Material de prueba A", "codigo": "   "})
    b = con_admin.post("/materiales", json={"nombre": "Material de prueba B"})
    assert (a.status_code, b.status_code) == (201, 201)
    assert a.json()["codigo"] is None and b.json()["codigo"] is None


def test_alta_de_material_con_nombre_repetido_responde_409(con_admin):
    con_admin.post("/materiales", json={"nombre": "Material de prueba"})
    respuesta = con_admin.post("/materiales", json={"nombre": "MATERIAL DE PRUEBA"})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya existe un material con ese nombre"


def test_alta_de_material_con_codigo_repetido_responde_409(con_admin):
    con_admin.post("/materiales", json={"nombre": "Material de prueba A", "codigo": "X98"})
    respuesta = con_admin.post("/materiales", json={"nombre": "Material de prueba B", "codigo": "x98"})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya existe un material con ese código"


@pytest.mark.parametrize(
    ("cuerpo", "mensaje"),
    [
        ({"nombre": "Material de prueba", "codigo": "ABCDEFGHIJK"}, "El código puede tener hasta 10 caracteres"),
        ({"nombre": ""}, "El nombre es obligatorio"),
        ({"nombre": "Material de prueba", "nombre_alternativo": "N" * 101},
         "El nombre alternativo puede tener hasta 100 caracteres"),
    ],
)
def test_alta_de_material_con_datos_invalidos_responde_422(con_admin, cuerpo, mensaje):
    respuesta = con_admin.post("/materiales", json=cuerpo)
    assert respuesta.status_code == 422
    assert mensaje in _detalle(respuesta)


def test_modificacion_de_material_y_borrado_de_campos_opcionales(con_admin):
    material = con_admin.post(
        "/materiales", json={"nombre": "Material de prueba", "codigo": "X98", "nombre_alternativo": "Otro nombre"}
    ).json()

    cambio = con_admin.patch(f"/materiales/{material['id']}", json={"nombre": "Material de prueba 2", "codigo": "x 99"})
    assert cambio.status_code == 200
    assert (cambio.json()["nombre"], cambio.json()["codigo"]) == ("Material de prueba 2", "X99")

    borrado = con_admin.patch(f"/materiales/{material['id']}", json={"codigo": None, "nombre_alternativo": None})
    assert borrado.status_code == 200
    assert (borrado.json()["codigo"], borrado.json()["nombre_alternativo"]) == (None, None)


def test_modificar_material_con_codigo_de_otro_responde_409(con_admin):
    con_admin.post("/materiales", json={"nombre": "Material de prueba A", "codigo": "X98"})
    b = con_admin.post("/materiales", json={"nombre": "Material de prueba B"}).json()
    respuesta = con_admin.patch(f"/materiales/{b['id']}", json={"codigo": "X98"})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "Ya existe un material con ese código"


def test_modificar_material_inexistente_responde_404(con_admin):
    respuesta = con_admin.patch("/materiales/999999", json={"activo": False})
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "No existe el material 999999"


def test_modificar_material_sin_cambios_responde_422(con_admin):
    material = con_admin.post("/materiales", json={"nombre": "Material de prueba"}).json()
    respuesta = con_admin.patch(f"/materiales/{material['id']}", json={})
    assert respuesta.status_code == 422
    assert "Hay que indicar al menos un cambio" in _detalle(respuesta)


def test_baja_y_reactivacion_de_material(con_admin, db_pg):
    material = con_admin.post("/materiales", json={"nombre": "Material de prueba"}).json()

    baja = con_admin.patch(f"/materiales/{material['id']}", json={"activo": False})
    assert baja.status_code == 200 and baja.json()["activo"] is False
    assert db_pg.get(Material, material["id"]) is not None
    # Lavado y Empaque (GET /materiales) dejan de verlo; el ABM lo sigue viendo
    assert material["id"] not in _ids(con_admin.get("/materiales"))
    assert material["id"] in _ids(con_admin.get("/materiales?incluir_inactivos=true"))

    alta = con_admin.patch(f"/materiales/{material['id']}", json={"activo": True})
    assert alta.status_code == 200 and alta.json()["activo"] is True
    assert material["id"] in _ids(con_admin.get("/materiales"))


def test_lista_completa_de_materiales_para_el_abm(con_admin, db_pg):
    db_pg.add(Material(nombre="Material de prueba inactivo", activo=False))
    db_pg.commit()

    respuesta = con_admin.get("/materiales", params={"incluir_inactivos": True})

    assert respuesta.status_code == 200
    assert all(set(f) == CLAVES_MATERIAL_ADMIN for f in respuesta.json())
    assert _ids(respuesta) == {m.id for m in db_pg.scalars(select(Material))}
