# ETL Chile — Ventas & Señalizaciones

Migración a Python (arquitectura Clean/Layered) de dos paquetes SSIS:

| Paquete SSIS original | Pipeline Python |
|---|---|
| `CROSS 0101 SSIS_CL_Senalizaciones.dtsx` | `SenalizacionesPipeline` |
| `CROSS 0102 SSIS_CL_Ventas.dtsx` | `VentasPipeline` |

El paquete de Señalizaciones invocaba, vía **Execute Process Task**, un script
Python externo (`Ch_Senhalizaciones.py`, en `02_Cross/`) que descargaba un CSV
publicado de Google Sheets. Esa dependencia se migró como adaptador de
infraestructura: [`google_sheets_csv_downloader.py`](src/etl_chile/infrastructure/external/google_sheets_csv_downloader.py).

## Arquitectura

```
src/etl_chile/
├── domain/            # Modelos y excepciones puras, sin dependencias externas
├── application/        # Casos de uso (pipelines) + puertos (interfaces)
│   ├── ports/           # Protocols: DatabaseGateway, SpreadsheetReader, FlatFileReader, CsvDownloader
│   └── use_cases/       # SenalizacionesPipeline, VentasPipeline, SQL y mapeos de columnas
├── infrastructure/     # Implementaciones concretas de los puertos
│   ├── db/               # SQLAlchemy + pyodbc (SQL Server)
│   ├── files/             # pandas/openpyxl (Excel, CSV)
│   └── external/          # Descarga CSV desde Google Sheets
└── presentation/        # CLI + composition root (inyección de dependencias)
```

Regla de dependencia: `presentation` e `infrastructure` dependen de
`application`; `application` depende de `domain`; `domain` no depende de nada.
Los pipelines (`application/use_cases`) sólo conocen los `Protocol` definidos
en `application/ports`, nunca las clases concretas de `infrastructure`.

### Decisión de diseño: `TBL_FUNNEL_SENHALIZACIONES_DNI`

Ambos paquetes `.dtsx` originales truncan y recargan la tabla
`TBL_FUNNEL_SENHALIZACIONES_DNI` con el mismo Data Flow (misma hoja Excel,
mismas columnas). Aquí se extrajo una sola vez como caso de uso reutilizable:
[`dni_senalizaciones_sync.py`](src/etl_chile/application/use_cases/dni_senalizaciones_sync.py).

## Requisitos

- Python 3.11+
- [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server) instalado en el equipo
- Acceso de red al servidor SQL Server `172.17.0.162` y a los archivos Excel/CSV de red (rutas `D:\IRISCENE ENGINEERING CORPORATION SLU\...`)

## Instalación (VS Code)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
copy .env.example .env
```

Edite `.env` con la contraseña real de `mparedes` y, si aplica, ajuste las
rutas de red y la URL de exportación CSV de Google Sheets (ver
`.env.example`).

Abra la carpeta en VS Code — `.vscode/settings.json` ya deja los imports de
`src/` resueltos para el analizador e IntelliSense, y `.vscode/launch.json`
trae 3 configuraciones de depuración listas (Señalizaciones, Ventas, Todos).

## Ejecución

El orden respeta al del proyecto SSIS original: primero
`CROSS 0101 SSIS_CL_Senalizaciones.dtsx`, después `CROSS 0102 SSIS_CL_Ventas.dtsx`.

```bash
python main.py senalizaciones
python main.py ventas
python main.py all
```

`ventas`/`all` usan la fecha de corte declarada en `VAR_FECHA` (`.env`);
`--fecha YYYY-MM-DD` es opcional y, si se pasa, la sobreescribe puntualmente
para esa ejecución:

```bash
python main.py ventas --fecha 2026-08-01
```

### Parámetros/Variables del proyecto SSIS original

Se conservó la declaración de Parameters/Variables de
`CROSS 0102 SSIS_CL_Ventas.dtsx` tal como está en el `.dtsx` (ver
`PackageParameters` en [`config/settings.py`](src/etl_chile/config/settings.py)),
declarada en `.env`:

| Variable `.env` | Origen SSIS | Uso |
|---|---|---|
| `PARAM_PERIODO` | Project Parameter `Periodo` (DT_I4) | No se usa en ningún SQL/expresión del `.dtsx` original — vestigial, se conserva por fidelidad. |
| `VAR_FECHA` | Package Variable `User::Fecha` (DT_DATE) | Fecha de corte real, usada por el pipeline de Ventas. En el `.dtsx` original la inyectaba el scheduler que lo invocaba (`dtexec /Set \Package.Variables[User::Fecha].Value=...`); acá se declara en `.env` y puede sobreescribirse con `--fecha`. |
| `VAR_FEC` | Package Variable `User::Fec` (DT_I4) | No se usa en ninguna parte del `.dtsx` original — vestigial, se conserva por fidelidad. |

## Tests

```bash
pytest
```

Los tests usan *fakes* de los puertos (`tests/unit/fakes.py`), por lo que no
requieren base de datos ni archivos Excel reales.

## Notas de fidelidad con los paquetes SSIS originales

- Los separadores `GO` de los Execute SQL Task multi-batch se eliminaron;
  cada sentencia se ejecuta por separado (`GO` no es SQL válido para
  ODBC/OLE DB, sólo lo entienden SSMS/sqlcmd).
- El stored procedure `SP_FUNNEL_SENHALIZACIONES` se invoca vía `EXEC`, tal
  como en el paquete original — su lógica interna no se reimplementó en
  Python porque no forma parte del `.dtsx`.
- El parámetro de proyecto `Periodo` y la variable `User::Fec` del paquete de
  Ventas estaban definidos pero sin uso en el `.dtsx` original (vestigiales);
  no se migraron.
- La columna de destino `MÚMERO DEL CUAL LLAMA` está mal escrita en la tabla
  SQL original (falta la "N" de "NÚMERO"); se conserva así para no romper
  compatibilidad con la tabla existente.
- La columna `TOTAL INGRESADO` de `TBL_FUNNEL_SENHALIZACIONES` nunca se
  pobló en el paquete original (el Flat File Source no seleccionaba esa
  columna del CSV); se mantiene sin mapear.
- Las validaciones estrictas `FailComponent` de los componentes "Data
  Conversion" de SSIS no se replican: los casts de tipo son permisivos
  (`errors="coerce"` → valor nulo en vez de abortar la carga).
