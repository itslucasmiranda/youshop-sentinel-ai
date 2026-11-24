from fastapi import FastAPI
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .api import router

app = FastAPI(
    title="YouShop Sentinel AI",
    description="Protótipo local para análise de comissões.",
)
app.include_router(router)


STATIC = Path(__file__).with_name("static")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health", summary="Verificar disponibilidade da API")
def health() -> dict[str, str]:
    return {"status": "ok"}
