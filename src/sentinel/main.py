from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="YouShop Sentinel AI",
    description="Protótipo local para análise de comissões.",
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    return """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouShop Sentinel AI</title>
</head>
<body>
  <main>
    <h1>YouShop Sentinel AI</h1>
    <p>API local em execução.</p>
    <a href="/docs">Documentação interativa da API</a>
  </main>
</body>
</html>"""


@app.get("/health", summary="Verificar disponibilidade da API")
def health() -> dict[str, str]:
    return {"status": "ok"}
