from pydantic import BaseModel, ConfigDict, field_validator, model_validator

# Límites de las columnas (models/catalogos.py) y regla del servicio
LARGO_MAXIMO_NOMBRE = 100
LARGO_MAXIMO_CODIGO = 10
DIAS_AIREACION_MAXIMO = 365  # tope para frenar errores de tipeo; hoy el mayor es 10


class ServicioOut(BaseModel):
    id: int
    nombre: str
    dias_aireacion: int


class MaterialOut(BaseModel):
    id: int
    nombre: str
    codigo: str | None
    nombre_alternativo: str | None


class EquipoOut(BaseModel):
    id: int
    nombre: str
    metodo_id: int
    metodo: str


class ProgramaOut(BaseModel):
    id: int
    nombre: str
    metodo_id: int
    temperatura_c: float | None
    tiempo_esterilizacion_min: int | None
    tiempo_secado_min: int | None
    tiempo_desgasificacion_min: int | None
    vacio_bar: float | None
    vapor_bar: float | None
    pulsos: int | None


class ProximoNumeroOut(BaseModel):
    equipo_id: int
    numero: int


class MetodoOut(BaseModel):
    id: int
    nombre: str


# ---------------------------------------------------------------------------
# ABM de servicios y materiales (solo administradores)
# Las validaciones se escriben a mano para que los mensajes salgan en español.
# ---------------------------------------------------------------------------


class ServicioAdminOut(BaseModel):
    """Servicio completo, para el ABM: incluye externo y el estado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    externo: bool
    dias_aireacion: int
    activo: bool


class MaterialAdminOut(BaseModel):
    """Material completo, para el ABM: incluye el estado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    codigo: str | None
    nombre_alternativo: str | None
    activo: bool


def _nombre(valor: str, que: str = "El nombre") -> str:
    valor = valor.strip()
    if not valor:
        raise ValueError(f"{que} es obligatorio")
    if len(valor) > LARGO_MAXIMO_NOMBRE:
        raise ValueError(f"{que} puede tener hasta {LARGO_MAXIMO_NOMBRE} caracteres")
    return valor


def _dias(valor: int) -> int:
    if valor < 0:
        raise ValueError("Los días de aireación no pueden ser negativos")
    if valor > DIAS_AIREACION_MAXIMO:
        raise ValueError(f"Los días de aireación pueden ser hasta {DIAS_AIREACION_MAXIMO}")
    return valor


def normalizar_codigo(valor: str | None) -> str | None:
    """Código en mayúsculas y sin espacios. Vacío equivale a sin código."""
    if valor is None:
        return None
    valor = "".join(valor.split()).upper()
    if not valor:
        return None
    if len(valor) > LARGO_MAXIMO_CODIGO:
        raise ValueError(f"El código puede tener hasta {LARGO_MAXIMO_CODIGO} caracteres")
    return valor


def _alternativo(valor: str | None) -> str | None:
    if valor is None or not valor.strip():
        return None
    return _nombre(valor, "El nombre alternativo")


class _Entrada(BaseModel):
    # Un campo desconocido (ej. "id") da 422, como en OperadorModificarIn
    model_config = ConfigDict(extra="forbid")


class ServicioAltaIn(_Entrada):
    nombre: str
    externo: bool = False
    dias_aireacion: int = 3  # el valor por defecto de la base ("el resto, 3 días")

    @field_validator("nombre")
    @classmethod
    def _v_nombre(cls, v: str) -> str:
        return _nombre(v)

    @field_validator("dias_aireacion")
    @classmethod
    def _v_dias(cls, v: int) -> int:
        return _dias(v)


class ServicioModificarIn(_Entrada):
    """Cambios sobre un servicio. La baja y la reactivación van por activo."""

    nombre: str | None = None
    externo: bool | None = None
    dias_aireacion: int | None = None
    activo: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _v_nombre(cls, v: str | None) -> str | None:
        return None if v is None else _nombre(v)

    @field_validator("dias_aireacion")
    @classmethod
    def _v_dias(cls, v: int | None) -> int | None:
        return None if v is None else _dias(v)

    @model_validator(mode="after")
    def al_menos_un_cambio(self):
        if not self.model_fields_set:
            raise ValueError("Hay que indicar al menos un cambio")
        for campo in ("nombre", "externo", "dias_aireacion", "activo"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"El campo {campo} no puede quedar vacío")
        return self


class MaterialAltaIn(_Entrada):
    nombre: str
    codigo: str | None = None
    nombre_alternativo: str | None = None

    @field_validator("nombre")
    @classmethod
    def _v_nombre(cls, v: str) -> str:
        return _nombre(v)

    @field_validator("codigo")
    @classmethod
    def _v_codigo(cls, v: str | None) -> str | None:
        return normalizar_codigo(v)

    @field_validator("nombre_alternativo")
    @classmethod
    def _v_alt(cls, v: str | None) -> str | None:
        return _alternativo(v)


class MaterialModificarIn(_Entrada):
    """Cambios sobre un material. codigo y nombre_alternativo se borran mandando null."""

    nombre: str | None = None
    codigo: str | None = None
    nombre_alternativo: str | None = None
    activo: bool | None = None

    @field_validator("nombre")
    @classmethod
    def _v_nombre(cls, v: str | None) -> str | None:
        return None if v is None else _nombre(v)

    @field_validator("codigo")
    @classmethod
    def _v_codigo(cls, v: str | None) -> str | None:
        return normalizar_codigo(v)

    @field_validator("nombre_alternativo")
    @classmethod
    def _v_alt(cls, v: str | None) -> str | None:
        return _alternativo(v)

    @model_validator(mode="after")
    def al_menos_un_cambio(self):
        if not self.model_fields_set:
            raise ValueError("Hay que indicar al menos un cambio")
        for campo in ("nombre", "activo"):
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"El campo {campo} no puede quedar vacío")
        return self
