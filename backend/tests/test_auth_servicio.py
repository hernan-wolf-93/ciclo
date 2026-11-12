from app.services import auth as servicio_auth


def test_credenciales_correctas_devuelven_el_operador(db, crear_operador, contrasena):
    operador = crear_operador()
    resultado = servicio_auth.autenticar(db, "9001", contrasena)
    assert resultado is not None
    assert resultado.id == operador.id


def test_contrasena_incorrecta_se_rechaza(db, crear_operador):
    crear_operador()
    assert servicio_auth.autenticar(db, "9001", "otra-clave") is None


def test_numero_inexistente_se_rechaza(db, contrasena):
    assert servicio_auth.autenticar(db, "9999", contrasena) is None


def test_operador_dado_de_baja_se_rechaza_aunque_la_contrasena_sea_correcta(
    db, crear_operador, contrasena
):
    crear_operador(activo=False)
    assert servicio_auth.autenticar(db, "9001", contrasena) is None


def test_siempre_se_verifica_una_contrasena_aunque_el_numero_no_exista_o_este_de_baja(
    db, crear_operador, contrasena, monkeypatch
):
    # Regla: el tiempo de respuesta no debe revelar qué números existen.
    llamadas = []
    original = servicio_auth.verificar_contrasena

    def espia(clave, hash_guardado):
        llamadas.append(hash_guardado)
        return original(clave, hash_guardado)

    monkeypatch.setattr(servicio_auth, "verificar_contrasena", espia)
    crear_operador(numero="9002", activo=False)

    assert servicio_auth.autenticar(db, "9999", contrasena) is None
    assert len(llamadas) == 1

    llamadas.clear()
    assert servicio_auth.autenticar(db, "9002", contrasena) is None
    assert len(llamadas) == 1