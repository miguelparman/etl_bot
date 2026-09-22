"""Tests de verificar_copia(): compara columnas de 'Registro'/'Bandejas'
entre origen y destino, ignorando el resto del contenido (estos archivos son
controles de bandeja en vivo, ver verificar_copia.py)."""

from __future__ import annotations

import io

import openpyxl

from config import SharePointOrigenSettings
from tests.unit.fakes import FakeSharePointClient
from verificar_copia import verificar_copia

import verificar_copia as verificar_copia_module


def _libro(hojas: dict[str, list[str]]) -> bytes:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for nombre_hoja, columnas in hojas.items():
        ws = wb.create_sheet(nombre_hoja)
        ws.append(columnas)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


_COLUMNAS_REGISTRO = ["Bandeja", "Tipo", "Asesor"]
_COLUMNAS_BANDEJAS = ["Correo_Bandeja", "Asesor"]


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
    monkeypatch.setattr(verificar_copia_module, "get_graph_token", lambda *a, **kw: "token-fake")
    monkeypatch.setattr(verificar_copia_module, "SharePointClient", lambda *a, **kw: cliente_origen)


def test_mismas_columnas_reporta_ok(monkeypatch):
    contenido = _libro({"Registro": _COLUMNAS_REGISTRO, "Bandejas": _COLUMNAS_BANDEJAS})
    cliente_origen = FakeSharePointClient({"Registro_A.xlsx": contenido})
    _patch_cliente_origen(monkeypatch, cliente_origen)
    cliente_destino = FakeSharePointClient({"Registro_A.xlsx": contenido})

    resultados = verificar_copia(_origen_settings(), cliente_destino, "drive-destino", "14 CORREOS")

    assert len(resultados) == 1
    assert resultados[0].ok


def test_columna_distinta_reporta_diferencia(monkeypatch):
    origen_bytes = _libro({"Registro": _COLUMNAS_REGISTRO, "Bandejas": _COLUMNAS_BANDEJAS})
    destino_bytes = _libro({"Registro": _COLUMNAS_REGISTRO + ["Extra"], "Bandejas": _COLUMNAS_BANDEJAS})
    cliente_origen = FakeSharePointClient({"Registro_A.xlsx": origen_bytes})
    _patch_cliente_origen(monkeypatch, cliente_origen)
    cliente_destino = FakeSharePointClient({"Registro_A.xlsx": destino_bytes})

    resultados = verificar_copia(_origen_settings(), cliente_destino, "drive-destino", "14 CORREOS")

    assert not resultados[0].ok
    assert "Registro" in resultados[0].detalle


def test_archivo_ausente_en_destino_reporta_diferencia(monkeypatch):
    origen_bytes = _libro({"Registro": _COLUMNAS_REGISTRO, "Bandejas": _COLUMNAS_BANDEJAS})
    cliente_origen = FakeSharePointClient({"Registro_A.xlsx": origen_bytes})
    _patch_cliente_origen(monkeypatch, cliente_origen)
    cliente_destino = FakeSharePointClient({})  # no tiene 'Registro_A.xlsx'

    resultados = verificar_copia(_origen_settings(), cliente_destino, "drive-destino", "14 CORREOS")

    assert not resultados[0].ok
    assert "destino" in resultados[0].detalle
