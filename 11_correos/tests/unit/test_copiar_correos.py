"""Tests de copiar_correos(): listar los .xlsx del origen, descargarlos y
subirlos al destino, continuando ante el fallo de un archivo individual."""

from __future__ import annotations

import copiar_correos as copiar_correos_module
from config import SharePointOrigenSettings
from copiar_correos import copiar_correos

from tests.unit.fakes import FakeSharePointClient


def _origen_settings() -> SharePointOrigenSettings:
    return SharePointOrigenSettings(
        tenant_id="tenant-bpo",
        client_id="client-bpo",
        client_secret="secret-bpo",
        hostname="fractaliagroup.sharepoint.com",
        site_path="/sites/BPO",
        folder_path="Control Correos Chile",
    )


def _patch_cliente_origen(monkeypatch, cliente_origen: FakeSharePointClient) -> None:
    """copiar_correos() crea su propio SharePointClient de origen a partir
    del token que devuelve get_graph_token(); se reemplazan ambos simbolos
    en el modulo para que la instancia sea 'cliente_origen'."""
    monkeypatch.setattr(copiar_correos_module, "get_graph_token", lambda *a, **kw: "token-fake")
    monkeypatch.setattr(copiar_correos_module, "SharePointClient", lambda *a, **kw: cliente_origen)


def test_copia_todos_los_archivos_exitosamente(monkeypatch):
    cliente_origen = FakeSharePointClient({"Registro_A.xlsx": b"contenido-a", "Registro_B.xlsx": b"contenido-b"})
    _patch_cliente_origen(monkeypatch, cliente_origen)
    cliente_destino = FakeSharePointClient()

    resultados = copiar_correos(_origen_settings(), cliente_destino, "drive-destino", "folder-destino")

    assert {r.nombre for r in resultados} == {"Registro_A.xlsx", "Registro_B.xlsx"}
    assert all(r.ok for r in resultados)
    assert cliente_destino.subidos == {"Registro_A.xlsx": b"contenido-a", "Registro_B.xlsx": b"contenido-b"}


def test_un_archivo_fallido_no_detiene_el_resto(monkeypatch):
    cliente_origen = FakeSharePointClient({"Registro_A.xlsx": b"contenido-a", "Registro_B.xlsx": b"contenido-b"})
    cliente_origen.fallar_descarga.add("Registro_A.xlsx")
    _patch_cliente_origen(monkeypatch, cliente_origen)
    cliente_destino = FakeSharePointClient()

    resultados = copiar_correos(_origen_settings(), cliente_destino, "drive-destino", "folder-destino")

    por_nombre = {r.nombre: r for r in resultados}
    assert not por_nombre["Registro_A.xlsx"].ok
    assert por_nombre["Registro_B.xlsx"].ok
    assert cliente_destino.subidos == {"Registro_B.xlsx": b"contenido-b"}


def test_no_hay_archivos_excel_en_origen(monkeypatch):
    cliente_origen = FakeSharePointClient({})
    _patch_cliente_origen(monkeypatch, cliente_origen)
    cliente_destino = FakeSharePointClient()

    resultados = copiar_correos(_origen_settings(), cliente_destino, "drive-destino", "folder-destino")

    assert resultados == []
    assert cliente_destino.subidos == {}
