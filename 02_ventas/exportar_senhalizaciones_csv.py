"""Paso 0: descarga las respuestas del formulario de señalizaciones
publicadas en Google Sheets y las sube como 'Señalizaciones.csv' a la
carpeta '07 CROSS' de SharePoint.

'main.py' llama a 'subir_senhalizaciones_csv()' automaticamente antes de
correr el paquete 'senalizaciones' (o 'todos') -- no hace falta correr este
script aparte para eso. Se deja como script standalone (ver 'Uso' abajo)
solo para poder refrescar el CSV a mano sin correr el resto del pipeline.

Reemplaza al Execute Process Task 'Descargar googledrive señalizaciones'
del .dtsx original (`CROSS 0101 SSIS_CL_Senalizaciones.dtsx`), que llamaba
a un script equivalente a este (`Ch_Senhalizaciones.py`, ver
Basurero/02_Cross/) para escribir el CSV en una ruta de red local que el
Flat File Connection Manager del paquete leia despues. Aqui se sube
directamente a SharePoint via Microsoft Graph (mismo destino que lee
main.py) en vez de depender de una ruta de red local sincronizada -- no se
asume que esa ruta exista en el servidor donde corra este script.

Cambios respecto al script original (ver mappings.py, comentario de
CSV_DELIMITER):
    - El CSV de salida se escribe con ';' como delimitador (el original
      usaba ',' por ser el default de csv.writer sin 'delimiter' explicito).
    - Se sube a SharePoint (upload_file) en vez de escribir a un archivo
      local.
    - Se respeta un salto de linea EMBEBIDO dentro de un campo con comillas
      (texto libre multilinea de una respuesta de Google Forms): el script
      original partia la respuesta completa con '.splitlines()' ANTES de
      pasarla a csv.reader, lo que corta ese campo a la mitad como si fuera
      una fila nueva (bug heredado, no intencional). Aqui se le pasa el
      texto completo a csv.reader (via StringIO) para que lo parsee segun
      RFC 4180, y despues cada valor se aplana a una sola linea (el salto
      de linea embebido se reemplaza por un espacio) para que la fila de
      salida siga ocupando una sola linea fisica en el CSV final.
    - Se aplica trim (recorte de espacios al inicio/final) a todos los
      valores de cada fila.
La lectura del CSV publicado de Google Sheets sigue siendo con ',' (asi lo
exporta Google, no se cambia).

Uso:
    python exportar_senhalizaciones_csv.py
"""

from __future__ import annotations

import csv
import logging
import sys
from io import StringIO
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src" / "ventas"))

import mappings
from config import cargar_configuracion
from exceptions import ExtraccionError, VentasError
from logging_setup import CONSOLA, NOMBRE_LOGGER, configurar_logging
from sharepoint.auth import get_graph_token
from sharepoint.client import SharePointClient

logger = logging.getLogger(NOMBRE_LOGGER)


def _normalizar_valor(valor: str) -> str:
    """Aplana un salto de linea embebido dentro del campo (lo reemplaza por
    un espacio, para que la fila de salida ocupe una sola linea fisica) y
    recorta espacios al inicio/final."""
    sin_saltos = valor.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return sin_saltos.strip()


def _generar_csv() -> bytes:
    """Descarga el CSV publicado de Google Sheets y lo re-escribe con ';'
    como delimitador, descartando filas sin DNI (primera columna vacia tras
    el trim) y recortando a las primeras NUM_COLUMNAS_SENHALIZACIONES_CSV
    columnas -- misma logica de filtrado/recorte que el script original,
    mas el manejo de saltos de linea embebidos y el trim (ver _normalizar_valor)."""
    response = requests.get(mappings.URL_GOOGLE_SHEETS_SENHALIZACIONES, timeout=60)
    response.raise_for_status()
    texto = response.content.decode("utf-8")
    # Se le pasa el texto completo a csv.reader (no pre-partido en lineas
    # con '.splitlines()', como hacia el script original) para que un
    # salto de linea EMBEBIDO dentro de un campo con comillas se respete
    # como parte del valor (RFC 4180), en vez de cortarlo como fila nueva.
    lector = csv.reader(StringIO(texto))  # Google exporta con ',' -- no se cambia la lectura.

    buffer = StringIO()
    escritor = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_ALL)
    for fila in lector:
        fila = [_normalizar_valor(campo) for campo in fila[: mappings.NUM_COLUMNAS_SENHALIZACIONES_CSV]]
        if not fila or not fila[0]:
            continue
        escritor.writerow(fila)

    return buffer.getvalue().encode("utf-8")


def subir_senhalizaciones_csv(client: SharePointClient, drive_id: str, folder_path: str) -> int:
    """Descarga el formulario de Google Sheets y sube (reemplazando)
    'Señalizaciones.csv' a 'folder_path', reutilizando un SharePointClient ya
    autenticado contra el tenant destino (mismo que usan los Origen
    Excel/CSV de main.py). Devuelve los bytes subidos. Levanta ExtraccionError
    ante cualquier fallo de red/Graph -- lo que llama a esta funcion decide
    si aborta o no."""
    try:
        logger.info("Descargando formulario de señalizaciones de Google Sheets...")
        contenido = _generar_csv()
        folder_id = client.resolve_folder(drive_id, folder_path)

        logger.info(
            "Subiendo '%s' (%s bytes) hacia carpeta '%s'...",
            mappings.ARCHIVO_SENHALIZACIONES_CSV,
            len(contenido),
            folder_path,
        )
        client.upload_file(drive_id, folder_id, mappings.ARCHIVO_SENHALIZACIONES_CSV, contenido)
        return len(contenido)
    except Exception as exc:
        raise ExtraccionError(f"No se pudo exportar '{mappings.ARCHIVO_SENHALIZACIONES_CSV}': {exc}") from exc


def main() -> int:
    settings = cargar_configuracion(BASE_DIR)
    configurar_logging(settings.log_file)

    try:
        token = get_graph_token(
            settings.sharepoint.tenant_id,
            settings.sharepoint.client_id,
            settings.sharepoint.client_secret,
            settings.sharepoint.timeout_ms,
        )
        client = SharePointClient(token, settings.sharepoint.timeout_ms)
        site_id = client.resolve_site(settings.sharepoint.hostname, settings.sharepoint.site_path)
        drive_id = client.resolve_drive(site_id, settings.sharepoint.drive_name)

        subir_senhalizaciones_csv(client, drive_id, settings.sharepoint.folder_path)

        logger.info("Exportacion completada.", extra=CONSOLA)
        return 0
    except VentasError as exc:
        logger.error("Error de configuracion: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Fallo la exportacion de '%s': %s", mappings.ARCHIVO_SENHALIZACIONES_CSV, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
