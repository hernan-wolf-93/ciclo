from pydantic import BaseModel


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