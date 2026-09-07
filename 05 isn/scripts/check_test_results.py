"""
Valida los 4 casos de borde de sample_data/Reporte_Contactos_Salesforce_BI_test.csv
directamente contra el resultado real en la base de prueba (no necesita una
corrida de SSIS). Correr después de:

    cp infra/.env.test .env
    python main.py --saltar isn

Uso:
    python scripts/check_test_results.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from config import settings
from db import get_engine

FALLAS: list[str] = []


def _check(condicion: bool, mensaje: str) -> None:
    if condicion:
        print(f"  OK: {mensaje}")
    else:
        print(f"  FALLA: {mensaje}")
        FALLAS.append(mensaje)


def main() -> int:
    engine = get_engine(settings.db_database_analisis)
    contactos = pd.read_sql("SELECT * FROM dbo.TBL_CONTACTOS_AUTORIZADOS_CHILE", engine)
    numeros = pd.read_sql("SELECT * FROM dbo.TBL_CONTACTOS_AUTORIZADOS_CHILE_NUMEROS", engine)
    contactos = contactos.set_index("ID CONTACTO")

    print("Caso 1 (fila normal):")
    fila = contactos.loc["CASO_001"]
    _check(fila["TELÉFONO"] == "222000001", "TELÉFONO sin cambios")

    print("Caso 2 (limpieza de sufijo '.0'):")
    fila = contactos.loc["CASO_002"]
    _check(fila["TELÉFONO"] == "222000002", f"TELÉFONO sin '.0' (quedó: {fila['TELÉFONO']!r})")
    _check(fila["MÓVIL"] == "911111112", f"MÓVIL sin '.0' (quedó: {fila['MÓVIL']!r})")

    print("Caso 3 (True/False -> 1/0):")
    fila = contactos.loc["CASO_003"]
    _check(int(fila["ACCESO PLATINO"]) == 1, "ACCESO PLATINO = 1 (desde 'True')")
    _check(int(fila["REPRESENTANTE LEGAL"]) == 0, "REPRESENTANTE LEGAL = 0 (desde 'False')")

    print("Caso 4 (sin teléfono ni móvil):")
    fila = contactos.loc["CASO_004"]
    _check(pd.isna(fila["TELÉFONO"]), "TELÉFONO nulo")
    _check(pd.isna(fila["MÓVIL"]), "MÓVIL nulo")

    print("Deduplicación en TBL_CONTACTOS_AUTORIZADOS_CHILE_NUMEROS:")
    telefonos = set(numeros["telefono"])
    esperados = {"222000001", "911111111", "222000002", "911111112"}
    _check(telefonos == esperados, f"números distintos esperados {esperados}, se obtuvo {telefonos}")
    _check(len(numeros) == len(esperados), f"sin duplicados (911111111 aparece en 2 contactos): {len(numeros)} filas")

    print()
    if FALLAS:
        print(f"{len(FALLAS)} verificación(es) fallaron.")
        return 1
    print("Todas las verificaciones pasaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
