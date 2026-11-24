from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BowieDickIn(BaseModel):
    resultado: Literal["aprobado", "fallido"]
    observacion: str | None = Field(default=None, max_length=1000)
    numero_ciclo: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validar_reglas(self):
        # Un texto en blanco equivale a no haber escrito nada.
        if self.observacion is not None:
            self.observacion = self.observacion.strip() or None
        if self.numero_ciclo is not None:
            self.numero_ciclo = self.numero_ciclo.strip() or None
        if self.resultado == "fallido" and not self.observacion:
            raise ValueError("Si el control falló, la observación es obligatoria")
        return self


class BowieDickOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipo_id: int
    fecha_hora: datetime
    resultado: str
    observacion: str | None
    numero_ciclo: str | None


class BowieDickEstadoOut(BaseModel):
    equipo_id: int
    aprobado_hoy: bool