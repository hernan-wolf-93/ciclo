from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    numero_operador: str = Field(min_length=1, max_length=20)
    contrasena: str = Field(min_length=1)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class OperadorOut(BaseModel):
    id: int
    numero_operador: str
    rol: str