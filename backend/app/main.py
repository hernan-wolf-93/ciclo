from fastapi import FastAPI

from app.api import auth, avances, catalogos, lotes, operadores, recepciones, roles

from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="CICLO",
    description="Sistema de gestión y trazabilidad de esterilización",
)

app.include_router(auth.router)
app.include_router(operadores.router)
app.include_router(roles.router)
app.include_router(recepciones.router)
app.include_router(avances.router)
app.include_router(lotes.router)
app.include_router(catalogos.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_cors,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/salud")
def salud():
    """Comprueba que el servidor está funcionando."""
    return {"estado": "ok"}