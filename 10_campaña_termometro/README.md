# ETL Campaña Termómetro — migración desde SSIS

Migración del paquete `SSIS_CL_Campaña_Termometro.dtsx` a Python.

## Arquitectura

Se usó un enfoque híbrido a propósito:

- **Python** reemplaza los Data Flows (lectura de Excel/CSV, transformaciones simples, carga a SQL Server).
- **SQL parametrizado** reemplaza los Execute SQL Task, incluyendo el `INSERT` final con joins y `ROW_NUMBER()`. No se reimplementó esa lógica en pandas a propósito: es lógica de conjunto (window functions + joins condicionados por fecha) que SQL Server resuelve mejor, y reescribirla en pandas habría sido el punto de mayor riesgo de introducir bugs sutiles.

Esto es más una migración **SSIS → Python + SQL Server** que una migración 100% a pandas, y es la recomendación general para paquetes con lógica pesada en el motor de base de datos.

## Estructura

```
etl_termometro/
├── config.py            # variables de entorno (reemplaza Connection Managers + variables SSIS)
├── db.py                 # conexión y ejecución SQL
├── pipeline.py            # orquestación (reemplaza el Control Flow)
├── main.py                # punto de entrada / CLI
├── extractors/            # reemplazan los *Source components
│   ├── excel_extractor.py
│   └── csv_extractor.py
├── transformers/           # reemplazan Derived Column / Data Convert
│   ├── clientes.py
│   ├── detractores.py
│   └── encuestas.py
├── loaders/                # reemplazan OLE DB Destination
│   └── sql_loader.py
└── sql/                     # reemplazan los Execute SQL Task
    ├── delete_periodo_sf.sql
    ├── delete_fuera_rango.sql
    ├── update_estado.sql
    ├── update_peso.sql
    ├── delete_periodo_evaluacion.sql
    └── insert_final.sql
```

## Cómo correrlo

```bash
pip install -r requirements.txt
cp .env.example .env   # y completar credenciales/rutas reales
python main.py --periodo 202607 --fecha-inicio 2026-07-01 --fecha-fin 2026-07-31
```

Requiere el driver ODBC de SQL Server instalado en el sistema (`ODBC Driver 18 for SQL Server` o el que corresponda).

## ✅ Verificado contra los archivos reales (ACTUAL_.xlsx y Reporte_termometros_v2.csv)

- **Nombres de columna del Excel `DB` y `DB_DETRACTOR`**: coinciden exactamente con lo esperado (`RUT_DV`, `NOMCLI`, `SEGME`, `NOM_SM`, `NOM_SUP`, `TENTA_FO`, `PERIODO`, `RUT_SIN_DV`). Sin cambios necesarios.
- **`TENTA_FO` (Excel) vs `[TENTA FO]` (SQL final)**: confirmado que el Excel usa guion bajo (`TENTA_FO`). Sigue pendiente confirmar si la tabla `TBL_CAMPAÑA_TERMOMETRO_SOURCE` en SQL Server tiene la columna con guion bajo o con espacio — si no calzan, el `INSERT` final fallará o traerá `NULL` en esa columna. Verificar con:
  ```sql
  SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'TBL_CAMPAÑA_TERMOMETRO_SOURCE';
  ```
- **Encoding del CSV**: `cp1252` estricto **falla** (byte inválido `0x8d` en el archivo real). Se cambió el default a `latin-1`, que sí lee el archivo completo. Vale la pena preguntarle a quien exporta el reporte de Salesforce si puede generarlo en UTF-8 para evitar esta ambigüedad a futuro.
- **Formato de fecha**: confirmado `DD-MM-AAAA` con guiones (ej. `23-07-2026`). El código ya usa `dayfirst=True`, que lo interpreta bien.
- **`Promedio del termómetro` usa coma decimal** (ej. `"10,00"`, `"6,77"`), no punto. Esto **no estaba contemplado en la primera versión del código** y se corrigió — sin el fix, toda esa columna se habría cargado como `NULL`.
- **Nombres reales de columna del CSV vs. lo asumido inicialmente**: el CSV usa puntos y dos puntos (`"11. Satisfacción general"`, `"Plan de acción: Caso"`), pero el SQL final referencia la tabla intermedia con esos caracteres reemplazados por espacio doble en dos casos puntuales (`"No  identificación fiscal"`, `"Plan de acción  Caso"`). Ya está mapeado en `transformers/encuestas.py` (`RENAME_MAP`).
- **Bug de datos corregido**: la primera versión usaba `astype(str)` para castear a texto, lo que convierte celdas vacías en el string literal `"nan"` en vez de dejarlas nulas. Se cambió a dtype `"string"` (nullable) en los tres transformadores.
- **Hallazgo extra, no es un bug**: en el Excel de ejemplo, `NOMCLI`, `SEGME`, `NOM_SM` y `NOM_SUP` vienen vacíos — pero no afecta el resultado final, porque el `INSERT` final realmente toma esos datos desde el cruce con `CL_CARTERA.TBL_HISTORIAL_CARTERA`, no desde estas columnas del Excel.

## ✅ Esquema confirmado contra SQL Server real (INFORMATION_SCHEMA.COLUMNS)

- **`TBL_CAMPAÑA_TERMOMETRO_SOURCE`**: confirmado que la columna es `TENTA FO` (con espacio). El Excel trae `TENTA_FO` (guion bajo) — ya se renombra en `transformers/clientes.py`. La tabla también tiene `SUB_SEGME`, que se deja `NULL` a propósito (el SQL final la toma de `CL_CARTERA`, no de este Excel).
- **`TBL_CAMPAÑA_TERMOMETRO_SF_TEMP`**: confirmado que **5 columnas del CSV no existen en la tabla** (`Nombre del cliente`, `Subsegmento local`, `Supervisor Nivel 2`, `Plan de acción: Plan de acción`, `Plan de acción: Estado`) — ya se excluyen de la carga en `transformers/encuestas.py`. También se confirmó que `Plan de acción: Creado por` **sí** mantiene los dos puntos (no se sanitiza, a diferencia de `Plan de acción  Caso` que sí lleva doble espacio). `Estado` y `Peso` existen en la tabla pero se dejan fuera de la carga inicial a propósito, porque se calculan después con los pasos `UPDATE ESTADO` / `UPDATE PESO`.
- Con esto, **los dos puntos pendientes del checklist anterior quedan cerrados**. El código ya devuelve exactamente el mismo set de columnas (mismos nombres) que existen en ambas tablas destino — verificado programáticamente contra los archivos fuente reales.

## ⚠️ Lo único que sigue pendiente

1. **Password de la conexión SQL**: el `.dtsx` original no trae contraseña en texto plano (probablemente usa Windows Auth o un Package Configuration externo). Define cómo se maneja el secreto en este entorno — nunca commitear `.env` con credenciales reales.
2. **Prueba de paridad**: antes de apagar el paquete SSIS, correr ambos contra el mismo periodo y comparar el `TBL_CAMPAÑA_TERMOMETRO` resultante (conteo de filas y checksum/hash de columnas clave) hasta tener 100% de coincidencia.

## Prueba de paridad (comparar contra el SSIS original)

Como `TBL_CAMPAÑA_TERMOMETRO` se sobrescribe en cada corrida, la comparación se
hace en dos pasos: se saca una "foto" del resultado después de cada corrida, y
luego se comparan esas dos fotos.

```bash
# 1. Corre el paquete SSIS original para el periodo a validar (como siempre lo has hecho)

# 2. Saca la foto del resultado del SSIS
python -m parity.snapshot --periodo 202607 --etiqueta ssis

# 3. Corre el pipeline Python para el mismo periodo
python main.py --periodo 202607 --fecha-inicio 2026-07-01 --fecha-fin 2026-07-31

# 4. Saca la foto del resultado del Python
python -m parity.snapshot --periodo 202607 --etiqueta python

# 5. Compara ambas fotos
python -m parity.compare --periodo 202607 --base ssis --nuevo python
```

El comando de comparación:
- Empareja las filas por `RUT` + `PERIODO`.
- Reporta filas que solo están en un lado (faltantes o de más).
- Reporta, columna por columna, cuántas filas tienen un valor distinto.
- Tolera diferencias mínimas de redondeo en `Prom 11.` y `Prom 14.` (±0.01) para no generar falsos positivos por precisión decimal.
- Genera un reporte detallado en `parity/snapshots/<periodo>_diff_report.md` con ejemplos concretos de cada diferencia.
- Termina con código de salida `0` si todo coincide, o `1` si hay diferencias — útil para integrarlo a un pipeline de CI/CD más adelante.

Se recomienda correr esta prueba contra 2-3 periodos distintos (incluyendo alguno con casos raros: clientes sin encuesta, RUTs duplicados, encuestas fuera de rango) antes de apagar el paquete SSIS definitivamente.

## Ambiente de pruebas local (Docker + datos sintéticos)

Para poder correr y validar el pipeline sin tocar la base de producción, el
proyecto incluye un SQL Server local en Docker con el mismo esquema
confirmado, más datos 100% sintéticos (no son datos reales de clientes) que
cubren 8 casos de borde de la lógica de negocio.

**Requiere Docker y Docker Compose instalados.** No pude levantar ni probar
este contenedor desde donde armé el proyecto (sin acceso a Docker en ese
entorno) — sí probé toda la lógica de transformación en Python contra los
datos sintéticos generados, pero **la parte de SQL Server (contenedor, script
de arranque, DDL) no quedó verificada en vivo.** Avísame si algo falla al
levantarlo y lo ajustamos.

### Levantar el ambiente

```bash
./scripts/setup_test_env.sh
```

Esto hace, en orden:
1. Levanta un contenedor de SQL Server 2022 (`docker compose`), expuesto en `localhost:14330`.
2. Crea las bases `CL_CAMPAÑAS` y `CL_CARTERA` y todas las tablas involucradas (`infra/sql/02_create_tables.sql`).
3. Genera los archivos sintéticos `sample_data/ACTUAL_test.xlsx` y `sample_data/Reporte_termometros_test.csv`.
4. Carga datos sintéticos de cartera en `CL_CARTERA.TBL_HISTORIAL_CARTERA`.

### Casos de borde incluidos en los datos sintéticos

| RUT | Caso | Resultado esperado |
|---|---|---|
| `11111111-1` | Encuesta normal | `Estado = CAMPAÑA OK` |
| `22222222-2` | Promedio 0, sin comentarios | `Estado = NO RECORRIDO` |
| `33333333-3` | Promedio 0, comentario "SIN CONTACTO" | `Estado = SIN CONTACTO` |
| `44444444-4` | Sin ninguna fila de encuesta | `Estado = NO RECORRIDO` (por ausencia) |
| `55555555-5` | Está en la lista de detractores | `ESTADO DETRACTOR = DETRACTOR` |
| `66666666-6` | Encuesta con fecha fuera del periodo evaluado | Se descarta, `Estado = NO RECORRIDO` |
| `77777777-7` | Dos encuestas (duplicado) | Debe prevalecer la más reciente (`Prom 14. = 9.0`) |
| `88888888-8` | Preguntas 11/14 con texto "No evaluado" | `Prom 11.` y `Prom 14.` deben quedar `NULL` |

### Correr el pipeline contra el ambiente de prueba

```bash
cp infra/.env.test .env
python main.py --periodo 202607 --fecha-inicio 2026-07-01 --fecha-fin 2026-07-31
```

### Validar automáticamente los casos de borde

```bash
python scripts/check_test_results.py --periodo 202607
```

Este script (distinto del módulo `parity/`) no necesita una corrida de SSIS
real: valida directamente que cada uno de los 8 casos de la tabla de arriba
haya quedado como se espera, comparando contra el resultado real en
`TBL_CAMPAÑA_TERMOMETRO`.

### Notas sobre el contenedor

- El script usa `/opt/mssql-tools18/bin/sqlcmd`, que es la ruta en las imágenes
  recientes de `mcr.microsoft.com/mssql/server:2022-latest`. Si tu imagen es
  más antigua y no tiene `sqlcmd` ahí, prueba `/opt/mssql-tools/bin/sqlcmd`
  (sin el `18`) y quita el flag `-C`.
- La contraseña de prueba (`Termometro_Test_2026!`) está solo en
  `infra/docker-compose.yml` e `infra/.env.test` — es exclusivamente para este
  contenedor local, no la reutilices en ningún ambiente real.
- Para limpiar todo: `docker compose -f infra/docker-compose.yml down -v`.

## Notas sobre el manejo de errores

- Si cualquiera de las tres ramas (clientes, detractores, salesforce) falla, el paso final **no se ejecuta** — esto replica el comportamiento de las Precedence Constraints del `.dtsx` original (las tres alimentan al contenedor final, así que si una falla, SSIS tampoco continuaría).
- Los logs se escriben a consola y a `logs/termometro_<timestamp>.log`.
- Pendiente de definir (no estaba explícito en el `.dtsx`): ¿qué pasa si falla una fila específica dentro de la carga? El original no muestra redirección de filas erróneas configurada, así que el comportamiento por defecto (fallar todo el batch) se mantuvo igual en Python.
