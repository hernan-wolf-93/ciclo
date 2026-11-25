from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class LineaLoteIn(BaseModel):
    servicio_id: int = Field(gt=0)
    material_id: int = Field(gt=0)
    # El máximo de 500 es provisorio, igual que en recepción y avance.
    cantidad: int = Field(ge=1, le=500)


class LoteIn(BaseModel):
    equipo_id: int = Field(gt=0)
    programa_id: int = Field(gt=0)
    # Lo escribe el operador en el equipo; el sistema solo lo propone (1 a 999, se repite).
    numero: int = Field(ge=1, le=999)
    lineas: list[LineaLoteIn] = Field(min_length=1)

    @model_validator(mode="after")
    def sin_lineas_repetidas(self):
        claves = [(linea.servicio_id, linea.material_id) for linea in self.lineas]
        if len(claves) != len(set(claves)):
            raise ValueError(
                "Un servicio y un material no pueden repetirse en dos líneas: sume las cantidades"
            )
        return self


class LoteCreadoOut(BaseModel):
    id: int
    numero: int
    equipo_id: int
    programa_id: int
    inicio: datetime
    total_items: int
    
    
class CierreLoteIn(BaseModel):
    # Contador del equipo, que el operador copia del panel. Se guarda como texto
    # (lote.numero_ciclo es String(20)): el tope son los 20 dígitos de la columna.
    numero_ciclo: int = Field(ge=1, le=10**20 - 1)
    resultado: Literal["aprobado", "fallido"]
    observacion: str | None = None

    @model_validator(mode="after")
    def fallido_requiere_motivo(self):
        if self.observacion is not None:
            self.observacion = self.observacion.strip() or None
        if self.resultado == "fallido" and self.observacion is None:
            raise ValueError("Un lote fallido necesita el motivo en la observación")
        return self


class LoteCerradoOut(BaseModel):
    id: int
    numero: int
    resultado: Literal["aprobado", "fallido"]
    fin: datetime
    numero_ciclo: str
    observacion: str | None
    
    
class FallaPosteriorIn(BaseModel):
    # Tope provisorio contra textos absurdos.
    motivo: str = Field(max_length=1000)

    @field_validator("motivo")
    @classmethod
    def motivo_no_vacio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("El motivo no puede estar vacío")
        return valor


class FallaPosteriorOut(BaseModel):
    id: int
    numero: int
    resultado: Literal["aprobado", "fallido"]
    observacion: str | None
    falla_posterior_en: datetime
    marcado_por: str  # N.º de operador de quien la marcó