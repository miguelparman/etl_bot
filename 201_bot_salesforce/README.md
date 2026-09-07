# Automatización Salesforce → SharePoint

Descarga informes de Salesforce (Lightning), los sube a una carpeta de SharePoint vía Microsoft Graph, y además copia cada archivo a una carpeta local/de red adicional. Usa Playwright para Salesforce y OAuth2 Client Credentials para Graph.

## Configuración inicial

1. `pip install -r requirements.txt`
2. `playwright install chromium`
3. Copia `.env.example` a `.env` y completa los valores reales (nunca subir `.env` a Git).

## Primera ejecución (login manual)

La primera vez, y cada vez que Salesforce vuelva a exigir MFA, hace falta completar el login a mano:

1. Pon `HEADLESS=false` en `.env`.
2. Ejecuta `python main.py`.
3. Se abrirá una ventana de Chrome: completa usuario/contraseña y aprueba el MFA en Salesforce Authenticator (o introduce el PIN si lo pide).
4. La sesión queda guardada en `playwright/.auth/sf_state.json` para las siguientes ejecuciones.

## Ejecuciones siguientes

Con una sesión válida guardada, puedes poner `HEADLESS=true` y ejecutar `python main.py` sin que se abra ninguna ventana. El bot procesa todos los informes de `config/reports.py` (o los primeros `MAX_REPORTS` si lo defines), copia cada CSV a `LOCAL_COPY_DIR` y lo sube a SharePoint, y muestra un resumen final. Los logs quedan en `logs/`.

Variables útiles para pruebas: `MAX_REPORTS` (limita cuántos informes procesar), `DRY_RUN=true` (exporta y valida, pero no copia ni sube a ningún lado, ni autentica contra Graph).

## Copia local/de red adicional

Además de subir cada informe a SharePoint, el bot lo copia a `LOCAL_COPY_DIR` (por defecto `D:\IRISCENE ENGINEERING CORPORATION SLU\BPO - Insumos\Chile\SEGUIMIENTO`, configurable en `.env` si cambia de equipo). Es una entrega **secundaria**: si esa carpeta no está disponible (por ejemplo, una unidad de red desconectada), el error queda registrado pero no impide que el informe se suba igualmente a SharePoint ni que se sigan procesando los demás informes. Respeta `OVERWRITE_EXISTING` igual que SharePoint.

## Limitación importante: MFA y ejecución desatendida

**Si la sesión de Salesforce guardada expira y Salesforce vuelve a exigir MFA, una ejecución completamente desatendida (Task Scheduler) no podrá continuar** hasta que una persona complete el login manualmente (paso "Primera ejecución" de arriba). Esto es intencional: el bot nunca intenta automatizar, saltarse o interceptar el MFA. Si una ejecución programada falla, lo primero a revisar es si la sesión expiró.

## Ejecución programada (Windows Task Scheduler)

El archivo `run_task.bat` ya deja listo el arranque sin consola (usa `pythonw.exe`, fija el directorio de trabajo, y con `HEADLESS=true` no abre ninguna ventana). Para programarlo:

1. Asegúrate de que `.env` tiene `HEADLESS=true` y de que ya existe una sesión guardada válida (sección anterior).
2. Abre el **Programador de tareas** de Windows → *Crear tarea básica*.
3. **Desencadenador**: por ejemplo, "Semanalmente" → Lunes a Viernes, 06:00 AM.
4. **Acción**: "Iniciar un programa".
   - Programa/script: la ruta completa a `run_task.bat` (por ejemplo `D:\Miguel Paredes\Desarrollo\02. PYTHON\bot\run_task.bat`).
   - "Iniciar en" (opcional, `run_task.bat` ya lo resuelve solo): la carpeta `bot\`.
5. En las propiedades de la tarea:
   - "Ejecutar tanto si el usuario inició sesión como si no" — solo funciona de forma confiable con `HEADLESS=true` y una sesión ya guardada; si la sesión expira, la tarea fallará por timeout (ver limitación de arriba), no se quedará colgada para siempre gracias a `MANUAL_LOGIN_TIMEOUT_MINUTES`.
   - Marca "Ejecutar con los privilegios más altos" solo si tu entorno lo requiere; normalmente no hace falta.
6. Guarda la tarea. Revisa `logs/bot_YYYYMMDD.log` tras la primera ejecución programada para confirmar que corrió bien.

Si algo falla durante el arranque antes de que exista cualquier log normal (por ejemplo, un `.env` mal configurado), el detalle queda en `logs/startup_error.log`.

## Destino distinto por informe (opcional)

Por defecto, todos los informes van a la misma subcarpeta de SharePoint y a la misma carpeta local (configuradas globalmente). Si un informe puntual necesita ir a otro lado, agrega `sharepoint_folder_path` y/o `local_copy_dir` a su entrada en `config/reports.py` (ver comentario de ejemplo ahí mismo). El site y la biblioteca de SharePoint (`ReportingFractalia` / `Data Reporting`) siempre son los mismos — solo cambia la subcarpeta final.

## Estructura del proyecto

```
bot/
├── app/
│   ├── config.py           # Carga y valida .env
│   ├── logger.py           # Logging a consola + archivo, redacta secretos
│   ├── salesforce/         # Login/MFA, sesión, exportación de informes
│   ├── sharepoint/         # Auth Graph, resolución de site/drive/carpeta, subida
│   └── services/           # Orquestador, reintentos, copia local adicional
├── config/reports.py       # Catálogo de informes (agregar aquí, sin tocar código)
├── downloads/ logs/ screenshots/ playwright/.auth/   # Datos locales (no versionados)
├── run_task.bat            # Wrapper para Task Scheduler (pythonw.exe, sin consola)
└── main.py                 # Punto de entrada
```
