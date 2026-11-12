from fastapi import FastAPI

app = FastAPI(
    title="CICLO",
    description="Sistema de gestión y trazabilidad de esterilización",
)


@app.get("/salud")
def salud():
    """Comprueba que el servidor está funcionando."""
    return {"estado": "ok"}