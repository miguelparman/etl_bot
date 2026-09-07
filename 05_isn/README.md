# ETL SSIS_CL_ISN → Python

Migración funcional del paquete SSIS `SSIS_CL_ISN.dtsx` a Python, manteniendo
SQL Server como destino de datos. Ver el análisis completo de la migración
(mapa de flujo, matriz de equivalencias, riesgos) en la conversación/documento
de diseño; este README cubre la operación del proyecto ya migrado.

## 1. Objetivo

Reemplazar el runtime propietario de SSIS por un ETL en Python + tecnologías
open source, preservando byte a byte la lógica de negocio SQL del paquete
original (18 LEFT JOIN de `TBL_ISN_SF`, reglas de `MOTIVO DE RETIRO`, dedup por
RUT, etc.), reduciendo la dependencia de Microsoft Integration Services.

## 2. Arquitectura

```
Contenedor de secuencias (paralelo)
    ├─ DELETE ENVIOS_CONSOLIDADO (LOCAL)
    ├─ Rebuild tablas auxiliares (TERMOMETRO / CCAA)
    ├─ Load aux_contacto (CSV → TBL_ISN_SF_AUX_CONTACTO)
    └─ Load aux_cliente  (CSV → TBL_ISN_SF_AUX_CLIENTE)
        │
        ▼
SECUENCIA NUEVA (secuencial)
    SF → histórico SF → TBL_ISN_PRE → histórico PRE
        │
        ├───────────────┬───────────────┐
        ▼               ▼
    TBL_ISN         TBL_ISN_CALIDAD
    (export CSV)    (carga a CL_CALIDAD)
```

Toda la lógica de negocio pesada (los 18 `LEFT JOIN`, las reglas `CASE`, los
`ROW_NUMBER`) se ejecuta **tal cual** contra SQL Server vía SQL parametrizado
(`sql/*.sql`), no se reescribió en Polars/Pandas: los 4 Data Flow Tasks del
paquete original eran, en la práctica, pases directos sin transformación
compleja (ver `sql/06_create_tbl_isn_sf.sql` para la única query realmente
compleja). Polars se usa solo donde el original hacía I/O de archivos: leer
los 2 CSV de insumo y escribir/leer el CSV de exportación.

- **Orquestación**: `main.py`, Python puro (sin Airflow/Prefect — no se
  justifica para ~20 pasos sin backfill ni ramas dinámicas).
- **SQL**: `SQLAlchemy` + `pyodbc` (`fast_executemany=True`).
- **Archivos**: `polars` para CSV, `shutil` para copiar/archivar.
- **Paralelismo**: `concurrent.futures.ThreadPoolExecutor` reproduce los dos
  grupos de tareas que en el `.dtsx` original no tenían restricciones de
  precedencia entre sí (por lo tanto corrían en paralelo).

## 3. Requisitos

- Python 3.12+
- ODBC Driver 18 for SQL Server (o el que definas en `DB_DRIVER`)
- Acceso de red al servidor SQL Server, con un login que tenga permisos de
  lectura/escritura en `CL_ISN`, `CL_CALIDAD`, `CL_ANALISIS`, `CL_VISTAS`,
  `CL_CARTERA`, `CL_CAMPAÑAS`, `BBDD_GENERAL` (todas las bases que la query de
  `TBL_ISN_SF` cruza con nombres de 3 partes)

## 4. Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 5. Configuración

```bash
copy .env.example .env
```

Editar `.env` con tus credenciales y rutas reales (nunca commitear `.env`).

## 6. Variables de entorno

Ver `.env.example` para el listado completo y comentarios de cada variable
(servidor/base de datos, rutas de archivos, ventana de fechas, logging).

**Importante — `FECHA_INICIO` / `FECHA_FIN`**: en el `.dtsx` original estas
eran variables con un valor **fijo** grabado en el diseñador (no una expresión
dinámica tipo `GETDATE()-1`). Este proyecto por defecto usa "ayer" si no se
especifican ni por `.env` ni por CLI — **confirma con el dueño del proceso si
ese es el comportamiento correcto en producción**.

## 7. Ejecución

```bash
python main.py
python main.py --fecha-inicio 2026-08-14 --fecha-fin 2026-08-14
```

Código de salida `0` = éxito, `1` = error (para schedulers).

## 8. Estructura del proyecto

```
SSIS_CL_ISN_python/
├── main.py                      # Punto de entrada (equivalente al Control Flow del .dtsx)
├── src/
│   ├── config/settings.py      # Equivalente a Connection Managers + Variables
│   ├── database/connection.py  # Engine SQLAlchemy, ejecución de scripts .sql
│   ├── extract/                # Flat file source + OLE DB source
│   ├── transform/type_casts.py # Componente "Conversión de datos" (TBL_ISN_ENVIOS_CONSOLIDADOS)
│   ├── load/sqlserver.py       # OLE DB Destination (fast load)
│   ├── pipeline/                # Un módulo por contenedor/secuencia del .dtsx
│   ├── logging_setup/logger.py
│   └── utils/audit.py          # Conteos de auditoría
├── sql/                        # Cada Execute SQL Task / query de Data Flow, verbatim
├── tests/
├── logs/
├── .env.example
├── requirements.txt
├── Dockerfile
└── README.md
```

## 9. Logging

Log dual (consola + `logs/ssis_cl_isn.log`), formato:

```
2026-08-19 02:00:01 INFO ETL iniciado (rango 2026-08-18..2026-08-18)
2026-08-19 02:00:05 INFO TBL_ISN_SF_AUX_CONTACTO recargada: 812 filas
2026-08-19 02:00:09 INFO TBL_ISN_SF reconstruida para el rango 2026-08-18..2026-08-18
2026-08-19 02:00:12 INFO isn.csv exportado (1204 filas) en D:\...\isn.csv
2026-08-19 02:00:12 INFO Duración total: 11.3s
2026-08-19 02:00:12 INFO ETL finalizado correctamente
```

## 10. Manejo de errores

El `.dtsx` original **no tenía Event Handlers ni Checkpoints**: cualquier
tarea que fallara abortaba todo el paquete. Este proyecto replica ese
comportamiento (fail-fast): cualquier excepción se registra con
`logger.exception` (incluye traceback) y el proceso termina con código `1`.
No hay reintentos automáticos ni continuación parcial, igual que el original.

Casos cubiertos explícitamente (ver `src/transform/type_casts.py`):
conversión numérica fallida y truncado de `SUBSEGMENTO` > 20 caracteres
**fallan** en vez de coercionar/truncar silenciosamente, tal como hacía el
componente "Conversión de datos" original (`FailComponent`).

## 11. Pruebas

```bash
pytest
```

Cubre: los casts críticos de `type_casts.py` (incluyendo los casos de fallo
que deben replicar `FailComponent`), el parseo de scripts SQL multi-lote
(`GO`), y las convenciones de nombres de archivo (`New_name_file`).

No hay pruebas de integración contra SQL Server real en este repo (requieren
credenciales); usar `sql/validacion_paridad.sql` durante el cutover (ver
sección 14).

## 12. Despliegue

- **Local / on-prem**: `pip install -r requirements.txt` + Task
  Scheduler/SQL Server Agent llamando `python main.py` (ver sección 13).
- **Contenedor**: `docker build -t etl-ssis-cl-isn .` — el `Dockerfile` instala
  el driver ODBC de Microsoft (es el único componente MS que queda, porque el
  destino sigue siendo SQL Server, no se está migrando la base).

## 13. Scheduler

| Opción | Recomendación |
|---|---|
| Windows Task Scheduler | **Recomendado.** Ya disponible, sin overhead nuevo, apto para 1 job diario simple |
| SQL Server Agent | Alternativa válida si ya administras jobs ahí; sigue siendo Microsoft pero no es SSIS |
| Cron (Linux/contenedor) | Si el ETL corre en Docker/Linux |
| Airflow / Prefect / Dagster | **No se recomienda aquí**: sobre-ingeniería para ~20 pasos sin backfill, sin DAGs dinámicos, sin necesidad de UI de reintentos por tarea |
| GitHub Actions / Azure DevOps | Útil solo si ya tienes runners con acceso de red al SQL Server; normalmente no es el caso para ETLs on-prem |

Dado el objetivo explícito de reducir dependencia de Microsoft, **Windows
Task Scheduler** ejecutando `python main.py` es la opción más simple y
proporcional a la complejidad real del proceso.

## 14. Troubleshooting

| Síntoma | Causa probable |
|---|---|
| `RuntimeError: Falta la variable de entorno...` | `.env` incompleto, revisar `.env.example` |
| Error de login SQL Server | Credenciales rotadas — el `.dtsx` original tenía la contraseña cifrada con DPAPI del perfil de Windows del autor original y **no es extraíble**; hay que solicitar credenciales nuevas |
| `ConversionError` en `load_envios_consolidado` | Datos de origen con `FECHA_EVENTO`/`Número del caso` no numéricos, o `SUBSEGMENTO` > 20 caracteres — igual que en SSIS, esto debe corregirse en el dato de origen, no silenciarse en el código |
| Encoding raro en `isn.csv` | Verificar que el consumidor final siga esperando CP1252 con `;` como separador (igual que el original) |
| Permisos insuficientes en alguna base (`CL_ANALISIS`, `CL_VISTAS`, etc.) | El login de `.env` necesita permisos en las 7 bases que cruza `sql/06_create_tbl_isn_sf.sql` |

## Fuera de alcance (confirmar con negocio)

Los Connection Managers `ISN MEDALLIA`, `ISN MEDALLIA V2`, `OJT.xlsx`,
`PROMOTORES.xlsx`, `CLIENTES DETRACTORES CALIDAD.xlsx` y las variantes sin
`_v2` de los CSV de aux_cliente/aux_contacto están **declarados en el `.dtsx`
original pero no son usados por ningún Data Flow o tarea** — no se migraron.
Las tablas `TBL_ISN_OJT`, `TBL_CLIENTES_DETRACTORES_CALIDAD` y
`TBL_ISN_PROMOTOR` sí se **leen** dentro del JOIN de `TBL_ISN_SF`, por lo que
deben seguir siendo pobladas por el proceso que corresponda (otro paquete
SSIS o este mismo en una versión no capturada en este archivo).
