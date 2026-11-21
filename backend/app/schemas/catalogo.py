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


class ProximoNumeroOut(BaseModel):
    equipo_id: int
    numero: int