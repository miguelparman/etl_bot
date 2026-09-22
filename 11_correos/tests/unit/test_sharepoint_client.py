"""Test de list_excel_files(): unica logica nueva de sharepoint_client.py
(el resto -- resolve_site/drive/folder, download_file, upload_file -- es el
mismo codigo ya probado en produccion por 02_ventas/copiar_funnel_ventas.py).
Ignora subcarpetas y archivos no-Excel, y sigue la paginacion de Graph."""

from __future__ import annotations

from sharepoint_client import SharePointClient


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200
        self.ok = True

    def json(self) -> dict:
        return self._payload


def test_ignora_subcarpetas_y_archivos_no_excel(monkeypatch):
    payload = {
        "value": [
            {"name": "Macros_Coordinadores", "folder": {}},
            {"name": "Registro_A.xlsx", "file": {}},
            {"name": "notas.txt", "file": {}},
            {"name": "Registro_B.XLSX", "file": {}},
        ]
    }
    monkeypatch.setattr("sharepoint_client.requests.get", lambda *a, **kw: _FakeResponse(payload))

    cliente = SharePointClient(token="fake", timeout_ms=1000)
    nombres = cliente.list_excel_files("drive-1", "Control Correos Chile")

    assert nombres == ["Registro_A.xlsx", "Registro_B.XLSX"]


def test_sigue_la_paginacion(monkeypatch):
    pagina_1 = {"value": [{"name": "A.xlsx", "file": {}}], "@odata.nextLink": "https://siguiente-pagina"}
    pagina_2 = {"value": [{"name": "B.xlsx", "file": {}}]}
    respuestas = iter([pagina_1, pagina_2])
    monkeypatch.setattr("sharepoint_client.requests.get", lambda *a, **kw: _FakeResponse(next(respuestas)))

    cliente = SharePointClient(token="fake", timeout_ms=1000)
    nombres = cliente.list_excel_files("drive-1", "Control Correos Chile")

    assert nombres == ["A.xlsx", "B.xlsx"]
