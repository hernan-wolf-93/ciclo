from pydantic import BaseModel, Field, field_validator

from app.core.reglas_operador import (
    LARGO_MAXIMO_CONTRASENA,
    LARGO_MAXIMO_NUMERO,
    LARGO_MINIMO_CONTRASENA,
)


class RecuperarContrasenaIn(BaseModel):
    numero_operador: str = Field(min_length=1, max_length=LARGO_MAXIMO_NUMERO)
    codigo: str = Field(min_length=1, max_length=32)
    contrasena_nueva: str = Field(min_length=LARGO_MINIMO_CONTRASENA, max_length=LARGO_MAXIMO_CONTRASENA)

    @field_validator("codigo")
    @classmethod
    def normalizar(cls, valor: str) -> str:
        # El código se dicta o se copia a mano: se ignoran espacios y minúsculas.
        return valor.strip().upper()