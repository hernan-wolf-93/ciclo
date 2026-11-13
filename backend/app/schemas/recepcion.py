from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class LineaRecepcionIn(BaseModel):
    material_id: int = Field(gt=0)
    # El máximo de 500 es provisorio: evita cargas absurdas por error.
    cantidad: int = Field(ge=1, le=500)


class RecepcionIn(BaseModel):
    servicio_id: int = Field(gt=0)
    items: list[LineaRecepcionIn] = Field(min_length=1)
    completo: bool
    servicio_avisado: bool = False
    observacion: str | None = Field(default=None, max_length=1000)
    urgente: bool = False

    @model_validator(mode="after")
    def validar_reglas(self):
        # Una observación en blanco equivale a no haber escrito nada.
        if self.observacion is not None:
            self.observacion = self.observacion.strip() or None

        ids = [linea.material_id for linea in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Un material no puede repetirse en dos líneas: sume las cantidades")

        if not self.completo:
            if not self.observacion:
                raise ValueError("Si falta una pieza, la observación es obligatoria")
            if not self.servicio_avisado:
                raise ValueError("Si falta una pieza, debe confirmarse el aviso al servicio de origen")
        return self


class RecepcionOut(BaseModel):
    id: int
    servicio_id: int
    fecha_hora: datetime
    total_items: int