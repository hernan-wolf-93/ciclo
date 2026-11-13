from fastapi import FastAPI

from app.api import auth, recepciones

app = FastAPI(
    title="CICLO",
    description="Sistema de gestión y trazabilidad de esterilización",
)

app.include_router(auth.router)
app.include_router(recepciones.router)

@app.get("/salud")
def salud():
    """Comprueba que el servidor está funcionando."""
    return {"estado": "ok"}