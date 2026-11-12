from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import obtener_db
from app.core.seguridad import crear_token
from app.schemas.auth import LoginIn, TokenOut
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