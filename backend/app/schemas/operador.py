from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.reglas_operador import (
    LARGO_MAXIMO_CONTRASENA,
    LARGO_MAXIMO_NUMERO,
    LARGO_MINIMO_CONTRASENA,
    numero_valido,
)


class OperadorAltaIn(BaseModel):
    numero_operador: str = Field(min_length=1, max_length=LARGO_MAXIMO_NUMERO)
    contrasena: str = Field(min_length=LARGO_MINIMO_CONTRASENA, max_length=LARGO_MAXIMO_CONTRASENA)
    rol_id: int

    @field_validator("numero_operador")
    @classmethod
    def sin_espacios(cls, valor: str) -> str:
        if not numero_valido(valor):
            raise ValueError("El número de operador no puede tener espacios")
        return valor


class OperadorAdminOut(BaseModel):
    """Lo que ve un administrador de un operador. Nunca incluye la contraseña ni su hash."""

    id: int
    numero_operador: str
    rol: str
    activo: bool
    
class RolOut(BaseModel):
    id: int
    nombre: str
    
class OperadorModificarIn(BaseModel):
    """Cambios permitidos sobre un operador. El número de operador no se modifica."""

    model_config = ConfigDict(extra="forbid")  # un campo desconocido (ej. el número) da 422

    rol_id: int | None = None
    activo: bool | None = None

    @model_validator(mode="after")
    def al_menos_un_cambio(self):
        if self.rol_id is None and self.activo is None:
            raise ValueError("Hay que indicar al menos un cambio: rol_id o activo")
        return self