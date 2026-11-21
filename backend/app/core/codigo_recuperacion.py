"""Código de recuperación de contraseña: reglas puras, sin base de datos."""

import secrets

# Sin 0, O, 1 ni I: el código se dicta o se copia a mano.
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
LARGO_CODIGO = 8
MINUTOS_VIGENCIA = 30  # provisorio, a validar con el servicio


def generar_codigo() -> str:
    """Código aleatorio generado con el módulo secrets (apto para seguridad)."""
    return "".join(secrets.choice(ALFABETO) for _ in range(LARGO_CODIGO))