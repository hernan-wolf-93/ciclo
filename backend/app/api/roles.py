from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import exigir_administrador, obtener_db
from app.models import Operador
from app.schemas.operador import RolOut
from app.services.operadores import listar_roles_asignables

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RolOut])
def roles_asignables(
    actor: Annotated[Operador, Depends(exigir_administrador)],
    db: Annotated[Session, Depends(obtener_db)],
):
    """Roles que quien hace el pedido puede asignar al dar de alta a otros."""
    return [RolOut(id=rol.id, nombre=rol.nombre) for rol in listar_roles_asignables(db, actor)]