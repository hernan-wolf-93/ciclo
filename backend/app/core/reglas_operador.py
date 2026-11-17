"""Reglas de validación de las credenciales de un operador.

Un solo lugar, para que la API y el script de terminal usen las mismas reglas.
"""

LARGO_MAXIMO_NUMERO = 20  # coincide con la columna operador.numero_operador
LARGO_MINIMO_CONTRASENA = 8  # provisorio, a validar con el servicio
LARGO_MAXIMO_CONTRASENA = 128  # evita pedidos absurdos al calcular el hash


def numero_valido(numero: str) -> bool:
    """Entre 1 y 20 caracteres y sin espacios. El formato final falta validarlo con el servicio."""
    return 1 <= len(numero) <= LARGO_MAXIMO_NUMERO and not any(c.isspace() for c in numero)