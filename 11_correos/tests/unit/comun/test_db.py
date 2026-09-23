"""Test de DatabaseGateway._executemany(): reintenta sin fast_executemany
cuando ese modo falla por 'right truncation' -- pyodbc subestima el buffer
de una columna de longitud muy variable (ej. NVARCHAR(MAX) 'Asunto'/'Contacto')
a partir de las primeras filas del lote. Encontrado con datos reales."""

from __future__ import annotations

import pyodbc
import pytest

from comun.db import DatabaseGateway


class _FakeCursor:
    def __init__(self, fallar_con_fast_executemany: bool) -> None:
        self.fast_executemany = False
        self._fallar_con_fast_executemany = fallar_con_fast_executemany
        self.llamadas: list[bool] = []

    def executemany(self, sql: str, params: list[tuple]) -> None:
        self.llamadas.append(self.fast_executemany)
        if self.fast_executemany and self._fallar_con_fast_executemany:
            raise pyodbc.Error("HY000", "String data, right truncation: length 2678 buffer 510")


def test_reintenta_sin_fast_executemany_ante_right_truncation():
    cursor = _FakeCursor(fallar_con_fast_executemany=True)

    DatabaseGateway._executemany(cursor, "INSERT INTO x VALUES (?)", [("valor",)], "TBL_CORREO_REGISTRO", "dbo")

    assert cursor.llamadas == [True, False]


def test_no_reintenta_ante_otro_tipo_de_error():
    cursor = _FakeCursor(fallar_con_fast_executemany=False)
    cursor.executemany = lambda sql, params: (_ for _ in ()).throw(pyodbc.Error("42000", "otro error"))

    with pytest.raises(pyodbc.Error):
        DatabaseGateway._executemany(cursor, "INSERT INTO x VALUES (?)", [("valor",)], "TBL_CORREO_REGISTRO", "dbo")


def test_no_reintenta_si_fast_executemany_funciona():
    cursor = _FakeCursor(fallar_con_fast_executemany=False)

    DatabaseGateway._executemany(cursor, "INSERT INTO x VALUES (?)", [("valor",)], "TBL_CORREO_REGISTRO", "dbo")

    assert cursor.llamadas == [True]
