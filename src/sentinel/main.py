from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .api import router

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    title="YouShop Sentinel AI",
    description="Protótipo local para análise de comissões.",
)
app.include_router(router)


STATIC = Path(__file__).with_name("static")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/docs", include_in_schema=False)
def docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json", title="Documentação · YouShop Sentinel AI",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon-32x32.png",
        swagger_ui_parameters={"validatorUrl": None},
    )


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/redoc", include_in_schema=False)
def reference() -> RedirectResponse:
    return RedirectResponse("/docs")


@app.get("/health", summary="Verificar disponibilidade da API")
def health() -> dict[str, str]:
    return {"status": "ok"}
