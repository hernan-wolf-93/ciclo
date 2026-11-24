from datetime import datetime

from pydantic import BaseModel, Field, model_validator


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