from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import obtener_db, obtener_operador_actual
from app.core.seguridad import crear_token
from app.models import Operador
from app.schemas.auth import LoginIn, OperadorOut, TokenOut
from app.services.auth import autenticar

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, db: Annotated[Session, Depends(obtener_db)]):
    """Ingreso con número de operador y contraseña. Devuelve un token."""
    operador = autenticar(db, datos.numero_operador, datos.contrasena)
    if operador is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Número de operador o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(access_token=crear_token(operador.id))


@router.get("/me", response_model=OperadorOut)
def quien_soy(operador: Annotated[Operador, Depends(obtener_operador_actual)]):
    """Devuelve el operador que hace el pedido. Sirve para comprobar el token."""
    return OperadorOut(
        id=operador.id,
        numero_operador=operador.numero_operador,
        rol=operador.rol.nombre,
    )