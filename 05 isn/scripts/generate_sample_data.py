"""
Genera un CSV sintético de contactos (mismo esquema de 19 columnas que
Reporte_Contactos_Salesforce_BI.csv, confirmado contra el archivo real) con
casos de borde para poder correr y validar el pipeline sin datos reales.

Uso:
    python scripts/generate_sample_data.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

OUT_DIR = BASE_DIR / "sample_data"

# Cabecera real del CSV de producción (con puntos, no con los dos espacios
# que declara el .dtsx -- ver contactos/columns.py). El extractor mapea por
# posición, así que el texto exacto de la cabecera no importa para el
# pipeline, pero se usa el real para que el archivo sintético sea fiel.
CABECERA = [
    "No. identificación fiscal",
    "Nombre del cliente",
    "Segmento Global",
    "Subsegmento local",
    "Número de documento",
    "Nombre",
    "Apellidos",
    "Cargo",
    "Teléfono",
    "Móvil",
    "Correo electrónico",
    "Autorizaciones funcionales",
    "Acceso a Portal Platino",
    "Representante legal",
    "Fecha de creación",
    "Fecha de la última modificación",
    "Creado por",
    "Última modificación por",
    "Id. de contacto",
]

FILAS = [
    # Caso 1: fila normal.
    [
        "11111111", "CLIENTE UNO SPA", "(TGS) Negocios", "Medianas Empresas", "11111111",
        "Juan", "Perez", "Gerente", "222000001", "911111111", "juan.perez@example.com",
        "", "1", "0", "04-12-2017", "10-01-2025", "Creador Uno", "Modificador Uno", "CASO_001",
    ],
    # Caso 2: MÓVIL/TELÉFONO con sufijo ".0" -- prueba update_limpiar_telefonos.sql.
    [
        "22222222", "CLIENTE DOS SPA", "(TGS) Negocios", "Medianas Empresas", "22222222",
        "Ana", "Diaz", "Analista", "222000002.0", "911111112.0", "ana.diaz@example.com",
        "", "0", "1", "05-01-2018", "11-02-2025", "Creador Dos", "Modificador Dos", "CASO_002",
    ],
    # Caso 3: mismo teléfono que el caso 1 (MÓVIL) -- prueba que
    # TBL_CONTACTOS_AUTORIZADOS_CHILE_NUMEROS deduplique.
    [
        "33333333", "CLIENTE TRES SPA", "(TGS) Negocios", "Pequeñas Empresas", "33333333",
        "Luis", "Soto", "Técnico", "", "911111111", "luis.soto@example.com",
        "Cobranza", "True", "False", "06-02-2019", "12-03-2025", "Creador Tres", "Modificador Tres", "CASO_003",
    ],
    # Caso 4: sin TELÉFONO ni MÓVIL -- no debe aportar filas a _NUMEROS.
    [
        "44444444", "CLIENTE CUATRO SPA", "(TGS) Negocios", "Grandes Empresas", "44444444",
        "María", "Núñez", "Administrativa", "", "", "maria.nunez@example.com",
        "", "0", "0", "07-03-2020", "13-04-2025", "Creador Cuatro", "Modificador Cuatro", "CASO_004",
    ],
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    destino = OUT_DIR / "Reporte_Contactos_Salesforce_BI_test.csv"
    with open(destino, "w", newline="", encoding="latin-1") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(CABECERA)
        writer.writerows(FILAS)
    print(f"OK: {len(FILAS)} filas sintéticas escritas en {destino}")


if __name__ == "__main__":
    main()
