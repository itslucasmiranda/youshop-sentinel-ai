# YouShop Sentinel AI

Local prototype for studying creator commission integrity. The API is built with
FastAPI and the landing page is in Brazilian Portuguese.

## Run on Windows

Open this folder in VS Code. In its PowerShell terminal, run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn sentinel.main:app --host 127.0.0.1
```

Select `.venv\Scripts\python.exe` as the Python interpreter in VS Code.
Open [the local interface](http://127.0.0.1:8000/) or check
[`GET /health`](http://127.0.0.1:8000/health) for HTTP 200 and
`{"status":"ok"}`. The health endpoint checks API liveness.
