# 11_correos

Dos procesos encadenados:

1. Copia todos los archivos Excel (`.xlsx`/`.xlsm`/`.xls`) de la carpeta
   **`Control Correos Chile`** del sitio SharePoint **`BPO`** hacia la
   carpeta **`14 CORREOS`** (dentro de `BPOCHIPE`) del sitio SharePoint
   **`ReportingFractalia`**.
2. Consolida las hojas `Registro`/`Bandejas` de todos esos archivos y las
   carga en SQL Server, `CL_MOVIL` en `172.17.0.162`.

**`python main.py` corre ambos pasos, en orden.** Es el único archivo
ejecutable en la raíz del proyecto; el resto del código vive en
`src/correos/` (ver "Estructura").

No recorre subcarpetas: `Control Correos Chile` tiene una subcarpeta
`Macros_Coordinadores` con macros `.bas` de los coordinadores que
explícitamente **no** forma parte de esta copia.

## Por qué existe

`BPO` y `ReportingFractalia` son sitios en **tenants de Microsoft Entra
distintos**. El endpoint de copia asíncrona nativo de Graph (`POST
/drives/.../copy`) solo copia dentro del mismo tenant/token, así que no
sirve aquí. En su lugar, cada archivo se **descarga** con el token de `BPO`
y se **sube** (reemplazando si ya existe) con el token de
`ReportingFractalia` — mismo patrón que ya usa
`02_ventas/copiar_funnel_ventas.py` para copiar `FUNNEL VENTAS V2.xlsx`
entre los mismos dos tenants.

## Estructura

`main.py` es el único archivo ejecutable en la raíz. Todo lo demás vive en
`src/correos/` ("src layout", mismo patrón que `02_ventas`/`08_cartera`):
`cargar_correos.py`/`verificar_copia.py` siguen siendo ejecutables por su
cuenta (ver "Uso"), solo que desde esa carpeta -- útil para reintentar una
sola etapa sin repetir todo el proceso.

```
11_correos/
├── main.py                         # unico punto de entrada en la raiz: copia + consolida + carga
├── src/correos/
│   ├── copiar_correos.py            # listar .xlsx del origen, descargar y subir uno por uno
│   ├── verificar_copia.py            # auditoria posterior: compara columnas de 'Registro'/'Bandejas'
│   ├── cargar_correos.py              # ejecutable: consolida y carga a SQL Server (CL_MOVIL)
│   ├── consolidar.py                  # leer/filtrar/validar 'Registro'/'Bandejas', convertir fechas
│   ├── db.py                          # DatabaseGateway (execute_script_rowcount, truncate_table, bulk_insert)
│   ├── mappings.py                    # tablas/columnas destino en CL_MOVIL
│   ├── sharepoint_client.py          # SharePointClient: resolve_site/drive/folder, list_excel_files, download_file, upload_file
│   ├── sharepoint_auth.py            # get_graph_token (OAuth2 client credentials)
│   ├── config.py                     # .env -> Settings (credenciales SharePoint + SQL Server)
│   ├── exceptions.py
│   └── logging_setup.py               # logs/correos_<timestamp>.log, un archivo por corrida
├── infra/sql/02_create_tables.sql   # DDL provisional de TBL_CORREO_REGISTRO/TBL_CORREO_BANDEJAS
├── pyproject.toml                   # pythonpath = ["src/correos"], para tests e imports
└── tests/unit/
```

## Configuración

Copiar `.env.example` a `.env` y completar:

- `SOURCE_TENANT_ID` / `SOURCE_CLIENT_ID` / `SOURCE_CLIENT_SECRET`: App
  Registration del tenant **`BPO`** (permiso `Sites.Selected` sobre
  `/sites/BPO`).
- `TENANT_ID` / `CLIENT_ID` / `CLIENT_SECRET`: App Registration del tenant
  **`ReportingFractalia`** (permiso `Sites.Selected` sobre
  `/sites/ReportingFractalia`).

Ambos pares de credenciales ya existen y están probados en
`02_ventas/.env` (mismos tenants, mismo sitio de origen `BPO`).

- `DB_SERVER` / `DB_NAME` (`CL_MOVIL`) / `DB_USER` / `DB_PASSWORD`: SQL
  Server `172.17.0.162`, destino de `cargar_correos.py`. Mismo login
  `mparedes` ya usado contra ese servidor en `02_ventas`/`04_usuarios`
  (bases `CL_USUARIOS`/`CL_DATA`). Probado en vivo (con VPN conectada).
- `FECHA_INICIO` / `FECHA_FIN`: periodo por defecto de la carga de
  `TBL_CORREO_REGISTRO` (UTC ISO-8601, sobre `FechaHora_UTC_Texto` --
  inicio inclusivo, fin exclusivo). Permite correr `cargar_correos.py` sin
  argumentos (útil para un schedule automatizado); `--fecha-inicio`/
  `--fecha-fin` en la línea de comandos tienen prioridad sobre `.env` si se
  pasan.

### Antes de la primera carga

`TBL_CORREO_REGISTRO`/`TBL_CORREO_BANDEJAS` **no existían** en `CL_MOVIL` --
ya se crearon (con VPN conectada) corriendo una vez:

```
sqlcmd -S 172.17.0.162 -d CL_MOVIL -i infra/sql/02_create_tables.sql
```

**Ya validado en vivo** (2026-09-22, con VPN conectada): tablas creadas,
primera carga completa (10.215 filas en `TBL_CORREO_REGISTRO`, 138 en
`TBL_CORREO_BANDEJAS`) y una segunda corrida del mismo periodo confirmó que
no duplica (borra e inserta las mismas 10.215 filas). Dos ajustes que salieron
de esa prueba real:

- `Contacto` se ensanchó a `NVARCHAR(MAX)` -- puede traer varias direcciones
  separadas por `;`, no un solo correo (superaba los 255 caracteres).
- `db.py` reintenta sin `fast_executemany` si pyodbc falla con
  "right truncation": ese modo estima el buffer de cada columna a partir de
  las primeras filas del lote, y con `Asunto`/`Contacto` (`NVARCHAR(MAX)`,
  longitud muy variable entre filas) puede quedarse corto.

El esquema es una estimación basada en los datos reales inspeccionados (no
en `INFORMATION_SCHEMA` del servidor). Usa `IF OBJECT_ID(...) IS NULL`
(nunca `DROP`), así que correrlo de nuevo no toca nada si las tablas ya
existen. Si algún tipo real difiere, ajustar ahí.

## Uso

```
python main.py
```

Un archivo que falla al copiarse **no detiene el resto**: queda registrado
en el log (`logs/correos_<timestamp>.log`, un archivo por corrida) y
`main.py` termina con código de salida `1` si hubo al menos un fallo, `0` si
todos los archivos se copiaron.

### Verificar la copia

```
python src/correos/verificar_copia.py
```

Compara, para cada `.xlsx`, las columnas de las hojas `Registro` y
`Bandejas` entre origen y destino. **No** compara el contenido de las filas
ni el hash de bytes: los `Registro_*.xlsx` son controles de bandeja **en
vivo** (las macros `ActualizarControlBandejas_*.bas` los reescriben
continuamente durante la jornada), así que su contenido cambia entre una
descarga y otra aunque la copia haya funcionado bien — lo único que debe
mantenerse estable es la estructura (hojas/columnas).

### Consolidar y cargar a SQL Server

Ya la corre `main.py` automáticamente después de la copia. Para reintentar
solo esta etapa (por ejemplo, si la copia ya funcionó y solo falló la carga)
se puede correr por separado:

```
python src/correos/cargar_correos.py --fecha-inicio 2026-09-01T00:00:00 --fecha-fin 2026-09-22T00:00:00
```

O, sin argumentos, usando `FECHA_INICIO`/`FECHA_FIN` de `.env`:

```
python src/correos/cargar_correos.py
```

Lee todos los `.xlsx` de `14 CORREOS`, consolida `Registro`/`Bandejas` de
forma independiente (nunca se mezclan) y carga:

- **`TBL_CORREO_REGISTRO`**: carga por **periodo**. `--fecha-inicio`
  (inclusivo) / `--fecha-fin` (exclusivo) acotan un rango UTC sobre
  `FechaHora_UTC_Texto`. Solo se **elimina e inserta** ese rango -- otros
  periodos ya cargados no se tocan. Repetir la misma corrida no duplica
  filas (se vuelve a borrar e insertar el mismo periodo).
- **`TBL_CORREO_BANDEJAS`**: siempre **reemplazo completo** (`TRUNCATE` +
  `INSERT` de todo lo consolidado), sin filtro de fecha -- no tiene un campo
  de control de periodo, y cada archivo trae el estado *actual* de sus
  bandejas, no un historial.

Cada hoja `Registro` es una plantilla pre-formateada a 5000 filas: solo una
fracción tiene datos reales (el resto tiene `Bandeja` vacío) y se descarta
antes de consolidar. Un archivo con una hoja o columna faltante se omite
(se registra el motivo) sin detener el resto. Antes de insertar se
deduplica defensivamente por `ID_Mensaje` (no se observaron duplicados en
los datos reales, pero una re-ejecución no debería poder introducirlos).

## Tests

```
python -m pytest tests/
```
