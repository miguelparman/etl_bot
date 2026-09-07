# Cartera — Migración SSIS → Python

Migración a Python (arquitectura Clean/Layered) del paquete SSIS
`CL_Proc_Carga_Cartera.dtsx`: carga mensual/periódica de la cartera de
clientes vigente (Chile) desde un Excel mantenido manualmente hacia SQL
Server, con reclasificación de estado (`NUEVO` / `SE MANTIENE` / `REINGRESO`)
contra el histórico acumulado.

## Arquitectura

```
app/
├── domain/            # Modelos (Periodo, ResultadoPipeline) y excepciones puras
├── application/        # Puertos (interfaces) + los 4 pasos del proceso + el orquestador
│   ├── ports.py          # Protocols: DatabaseGateway, SpreadsheetReader
│   ├── mappings.py        # Columnas/tablas/anchos de truncamiento (constantes de negocio)
│   ├── sql.py             # Sentencias T-SQL migradas literalmente de cada Execute SQL Task
│   ├── extraction.py      # Extracción: Origen Excel + Conversión de datos + Columna derivada
│   ├── validation.py      # Validación: tarea 'VALIDA' (4 controles de calidad)
│   ├── transformation.py  # Transformación: CARGA DNI, ACTUALIZA STATUS, LIMITA CLIENTES, LIMPIA TEMPORAL
│   ├── load.py            # Carga: truncados, inserciones y copia entre bases de datos
│   └── pipeline.py        # CarteraPipeline: orquesta los 4 pasos en el orden del Control Flow original
└── infrastructure/     # Implementaciones concretas de los puertos
    ├── config.py          # Carga de '.env' -> Settings (sin credenciales embebidas)
    ├── db.py               # Fábrica de conexiones pyodbc (una por Connection Manager OLE DB)
    ├── sqlserver_gateway.py # Implementa DatabaseGateway sobre pyodbc
    ├── spreadsheet_reader.py # Implementa SpreadsheetReader sobre pandas/openpyxl
    └── logging_setup.py

main.py   # CLI + composition root: arma infrastructure/ e inyecta en CarteraPipeline
```

Regla de dependencia: `main.py` e `infrastructure/` dependen de `application/`;
`application/` depende de `domain/`; `domain/` no depende de nada. El
orquestador (`pipeline.py`) y los 4 pasos (`extraction.py`, `validation.py`,
`transformation.py`, `load.py`) solo conocen los `Protocol` definidos en
`ports.py`, nunca las clases concretas de `infrastructure/`.

## Proceso original (Control Flow de `CL_Proc_Carga_Cartera.dtsx`)

3 Sequence Containers encadenados "On Success", sin ramas condicionales:

```
CARGA CARTERA TEMPORAL   TRUNCA TABLA -> Data Flow (Excel -> TBL_CARTERA) -> CARGA DNI -> VALIDA
        |
        v
CARGA CARTERA ACTUAL     TRUNCA TABLA -> Data Flow (TBL_CARTERA -> TBL_CARTERA_ACTUAL)
        |
        v
HISTORICO CARTERA        ACTUALIZA STATUS -> LIMITA CLIENTES -> LIMPIA TEMPORAL -> CARGA
```

- **Excel de origen**: `CARTERA_FRACTALIA.xlsx`, hoja `Hoja1` (mantenido
  manualmente por el equipo comercial).
- **Bases de datos** (mismo servidor SQL Server, 2 Connection Managers OLE DB
  distintos en el `.dtsx` original): `CL_TEMPORALES` (staging, tabla
  `TBL_CARTERA`) y `CL_CARTERA` (`TBL_CARTERA_ACTUAL`, `TBL_HISTORIAL_CARTERA`).
- **Lectura de solo lectura, cross-database**: `CL_DATA.dbo.TBL_PLACES`
  (maestro de asesores/ejecutivos), consultada desde la conexión de
  `CL_TEMPORALES` con nombre de 3 partes — debe estar en el mismo servidor.

## Requisitos

- Python 3.11+
- [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server)
- Acceso de red al servidor SQL Server y al Excel de origen (ruta de red)

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
```

Edite `.env` con las credenciales reales y, si aplica, ajuste las rutas de
red (ver `.env.example`).

## Ejecución

```bash
python main.py --fecha-inicio 20260827
python main.py                          # usa VAR_FECHA_INICIO de .env
```

## Tests

```bash
pytest
```

Los tests usan *fakes* de los puertos (`tests/unit/fakes.py`), por lo que no
requieren base de datos ni archivo Excel reales. Cubren:

- `test_extraction.py`: truncamiento de columnas (incl. el caso `SEGME`),
  columnas descartadas (`RUTCLI`, `RUT10`), columnas de período agregadas.
- `test_validation.py`: los 4 controles de calidad, y que el pipeline se
  detiene en el primero que falla (mismo comportamiento que el `RAISERROR`
  original).
- `test_load.py`: selección/renombrado de columnas al copiar de staging a
  `TBL_CARTERA_ACTUAL`.
- `test_pipeline.py`: las 3 Sequence Containers se ejecutan en orden y tocan
  las tablas/sentencias esperadas; una validación fallida aborta el pipeline
  antes de `CARGA CARTERA ACTUAL` (equivalente a que SSIS no siga la
  Precedence Constraint "On Success").

## Notas de fidelidad con el paquete SSIS original

- **Credenciales**: los 2 Connection Managers OLE DB (`CL_CARTERA`,
  `CL_TEMPORALES`) tenían password DPAPI-encriptado por usuario/máquina en el
  `.dtsx` — no son recuperables ni se intentó descifrarlas. Se reemplazaron
  por variables de entorno en `.env` (no versionado).
- **`User::Fecha_Inicio` era un valor literal fijo**, no una fórmula: se
  editaba a mano en el paquete original antes de cada corrida. Aquí se
  declara explícitamente en `.env` (`VAR_FECHA_INICIO`) o se pasa con
  `--fecha-inicio`; no se calcula solo.
- **`User::Fecha_Fin`** sí era dinámico (`GETDATE()` como entero `YYYYMMDD`):
  se replica igual en `domain.models.hoy_yyyymmdd()`.
- **Truncamiento de `SEGME` a 30 caracteres**: el componente "Conversión de
  datos" del Data Flow original truncaba `SEGME` a 30 aunque la columna
  destino real admite 255 — se conserva tal cual, aunque parezca un defecto.
- **Bug preexistente en `CARGA DNI`**: la rama `ELSE` de `RUT_SMTRDV`
  reasigna `X0.[RUT_SMTRIO]` en lugar de `X0.[RUT_SMTRDV]`. Se replica
  exactamente el comportamiento actual (ver comentario en `app/application/sql.py`);
  no se corrige salvo que se solicite explícitamente.
- **Validación con corto-circuito**: los 4 controles de la tarea `VALIDA`
  (RUT duplicado, asesor/RUT/nombre no asignado) se evalúan en el mismo
  orden que el `.dtsx` original y el pipeline se detiene en el primero que
  falla, sin evaluar los siguientes — igual que un `RAISERROR` de severidad
  16 abortaba el paquete SSIS.
- **`TBL_HISTORIAL_CARTERA` — esquema no confirmado en el `.dtsx`**: la
  tarea `CARGA` hace un `INSERT` posicional (sin lista de columnas) porque
  esa tabla nunca es destino de un componente Data Flow con metadata
  explícita en el paquete original. **Antes de operar en producción, verificar
  contra el DDL real de SQL Server que el orden de columnas de
  `app/application/sql.CARGA_HISTORICO` coincide con el de la tabla.**
- **Bloques de código muerto** (SQL comentado dentro de `ACTUALIZA STATUS
  TEMP CARTERA` y `LIMITA CLIENTES` en el `.dtsx` original) no se migraron:
  nunca se ejecutaban.
- El paquete original **no tiene** Script Tasks, Script Components,
  Conditional Split, Lookup, Merge Join ni Event Handlers — toda su lógica de
  negocio vive en las 8 sentencias T-SQL y los 2 Data Flows simples descritos
  arriba; no hay nada de eso que migrar.
