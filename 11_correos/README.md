# 11_correos

Dos procesos encadenados:

1. Copia todos los archivos Excel (`.xlsx`/`.xlsm`/`.xls`) de la carpeta
   **`Control Correos Chile`** del sitio SharePoint **`BPO`** hacia la
   carpeta **`14 CORREOS`** (dentro de `BPOCHIPE`) del sitio SharePoint
   **`ReportingFractalia`**.
2. Consolida las hojas `Registro`/`Bandejas` de todos esos archivos y las
   carga en SQL Server, `CL_MOVIL` en `172.17.0.162` (capa **bronze**).
3. Construye la capa **silver** (`TBL_CORREO_REGISTRO_SILVER`) leyendo
   bronze y agregando columnas derivadas (ver "Estructura medallion").
4. Construye la capa **gold** (modelo estrella en el esquema `gold`) desde
   silver, y valida que cuadre.

**`python main.py` corre los cuatro pasos, en orden.** Es el único archivo
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
│   ├── cargar_correos.py              # ejecutable: consolida y carga a SQL Server (CL_MOVIL) -- bronze
│   ├── cargar_silver.py               # ejecutable: bronze -> silver (por periodo o --completo)
│   ├── consolidar.py                  # leer/filtrar/validar 'Registro'/'Bandejas', convertir fechas
│   ├── silver.py                      # reglas ASUNTO_AGRUPADO + carga de TBL_CORREO_REGISTRO_SILVER
│   ├── cargar_gold.py                 # ejecutable: silver -> gold (por periodo o --completo)
│   ├── gold.py                        # modelo estrella: dimensiones (MERGE) + FACT_MENSAJE + validacion
│   ├── db.py                          # DatabaseGateway (fetch_dataframe, execute_script_rowcount, truncate_table, bulk_insert)
│   ├── mappings.py                    # tablas/columnas destino en CL_MOVIL, reglas de ASUNTO_AGRUPADO
│   ├── sharepoint_client.py          # SharePointClient: resolve_site/drive/folder, list_excel_files, download_file, upload_file
│   ├── sharepoint_auth.py            # get_graph_token (OAuth2 client credentials)
│   ├── config.py                     # .env -> Settings (credenciales SharePoint + SQL Server)
│   ├── exceptions.py
│   └── logging_setup.py               # logs/correos_<timestamp>.log, un archivo por corrida
├── infra/sql/02_create_tables.sql   # DDL provisional de TBL_CORREO_REGISTRO/TBL_CORREO_BANDEJAS (bronze)
├── infra/sql/03_create_silver.sql   # DDL de TBL_CORREO_REGISTRO_SILVER (silver)
├── infra/sql/04_create_gold.sql     # DDL del esquema [gold]: DIM_* + FACT_MENSAJE
├── pyproject.toml                   # pythonpath = ["src/correos"], para tests e imports
└── tests/unit/
```

## Estructura medallion

| Capa | Tabla (`CL_MOVIL.dbo`) | Contenido |
|---|---|---|
| Bronze | `TBL_CORREO_REGISTRO`, `TBL_CORREO_BANDEJAS` | Hojas `Registro`/`Bandejas` tal cual + `ORIGEN` (nombre del `.xlsx`) |
| Silver | `TBL_CORREO_REGISTRO_SILVER` | Columnas de `TBL_CORREO_REGISTRO` **menos** los cálculos del Excel + `ASUNTO_AGRUPADO` |
| Gold | esquema `gold`: `FACT_MENSAJE` + `DIM_FECHA`, `DIM_BANDEJA`, `DIM_TIPO`, `DIM_ASUNTO_AGRUPADO` | Modelo estrella (ver abajo) |

`EsPrimeraEntrada`, `TieneRespuesta`, `Tiempo_Primera_Respuesta_Horas`,
`Tiempo_Respuesta_Horas` y `Estado` **quedan solo en bronze**: los calcula la
macro del Excel y no son confiables (ej. ~1.110.900 h en 3.832 salidas = el
tiempo desde la fecha 0 de Excel cuando no encuentra la entrada; primeras
respuestas negativas; `Estado` siempre vacío).

Silver se construye **leyendo bronze**, nunca los `.xlsx`. Se carga por el
mismo periodo que bronze (`DELETE` + `INSERT` del rango), o completa con
`python src/correos/cargar_silver.py --completo` (hay que hacerlo tras
cambiar las reglas, para recalcular lo ya cargado).

`ASUNTO_AGRUPADO` sale de `Asunto` con estas reglas (`mappings.REGLAS_ASUNTO_AGRUPADO`),
**en orden**, gana la primera que calza, sin distinguir mayúsculas ni tildes:

1. **REBOTE**: contiene `delivery status notification`, `notificacion de estado de entrega`,
   `no entregable:` o `undelivered mail returned to sender`. Va primero porque un rebote
   cita el asunto original (`No entregable: Actualización de correo de contacto…`).
2. **PRESENTACIÓN**: contiene `actualizacion de correo de contacto` o `presentacion`
   como **palabra completa** (`representación` o `presentaciones` no cuentan).
3. **PRUEBA**: contiene `prueba`.
4. **PROMO**: contiene `promo` (cubre `PROMOSEPTIEMBRE`, `PROMOSETIEMBRE`, `PROMO SEPTIEMBRE`, `PROMOCIONES`…).

Si no calza ninguna, queda `NULL`.

### Gold: modelo estrella

```
                  gold.DIM_FECHA
                        │
gold.DIM_TIPO ── gold.FACT_MENSAJE ── gold.DIM_BANDEJA
                        │
             gold.DIM_ASUNTO_AGRUPADO
```

- **`FACT_MENSAJE`** — 1 fila por mensaje. Claves `FECHA_KEY` (AAAAMMDD,
  fecha **local** Perú/Bogotá), `BANDEJA_KEY`, `TIPO_KEY`,
  `ASUNTO_AGRUPADO_KEY`; atributos `ID_MENSAJE`, `CONVERSATION_ID`, `ASUNTO`,
  `CONTACTO`, `FECHA_HORA_UTC`, `FECHA_HORA_LOCAL`, `HORA_LOCAL`; medida
  `CANTIDAD` (= 1, para contar).
- **`DIM_FECHA`** — calendario por años completos (se extiende solo cuando
  llegan datos de un año nuevo), nombres en español, semana ISO, lunes = 1.
- **`DIM_BANDEJA`** — bandeja, asesor (1:1), `COORDINADOR` (nombre del
  `.xlsx` sin `Registro_` ni extensión), `ORIGEN` y última revisión
  entrada/salida (de `TBL_CORREO_BANDEJAS`). Se sobrescribe sin historial.
- **`DIM_TIPO`** — Entrada / Salida. **`DIM_ASUNTO_AGRUPADO`** — los grupos
  de las reglas.

Cada dimensión (salvo `DIM_FECHA`) tiene un miembro de **clave 0 con
descripción vacía**: un valor `NULL` en silver apunta ahí (p. ej. los asuntos
sin grupo), así las claves foráneas nunca quedan `NULL`.

Las dimensiones **nunca se truncan** (claves estables); `FACT_MENSAJE` se
carga por periodo igual que bronze/silver, o completa con
`python src/correos/cargar_gold.py --completo`. Al final se valida que
`FACT_MENSAJE` tenga las mismas filas que silver y ninguna sin bandeja/tipo;
si no cuadra, `main.py`/`cargar_gold.py` terminan con código `1`.

Tras cambiar reglas: `cargar_silver.py --completo` y luego
`cargar_gold.py --completo`.

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
  `TBL_CORREO_REGISTRO` (UTC, sobre `FechaHora_UTC_Texto`). Solo fecha
  (`FECHA_INICIO=2026-09-01`, `FECHA_FIN=2026-09-30`) = días completos, con
  `FECHA_FIN` incluido entero; con hora (`2026-09-01T00:00:00`) = inicio
  inclusivo, fin exclusivo. Permite correr `cargar_correos.py` sin
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
