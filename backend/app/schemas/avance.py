from typing import Literal

from pydantic import BaseModel, Field, model_validator


class LineaAvanceIn(BaseModel):
    material_id: int = Field(gt=0)
    # El máximo de 500 es provisorio, igual que en recepción.
    cantidad: int = Field(ge=1, le=500)


class AvanceIn(BaseModel):
    etapa_orden: Literal[2, 3]  # 2 = Lavado y secado, 3 = Empaque y rotulación
    items: list[LineaAvanceIn] = Field(min_length=1)
    solo_desinfeccion: bool = False
    observacion: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validar_reglas(self):
        # Una observación en blanco equivale a no haber escrito nada.
        if self.observacion is not None:
            self.observacion = self.observacion.strip() or None

        ids = [linea.material_id for linea in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Un material no puede repetirse en dos líneas: sume las cantidades")

        if self.solo_desinfeccion:
            if self.etapa_orden != 2:
                raise ValueError("Solo el lavado admite la excepción de solo desinfección")
            if not self.observacion:
                raise ValueError("Si solo se desinfecta, la observación es obligatoria")
        return self


class AvanceOut(BaseModel):
    etapa_orden: int
    total_items: int
    solo_desinfeccion: bool
    

class PendienteOut(BaseModel):
    servicio_id: int
    servicio: str
    material_id: int
    material: str
    cantidad: int