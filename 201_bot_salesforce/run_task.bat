@echo off
REM Wrapper para ejecutar la automatizacion sin consola visible, pensado
REM para ser llamado desde el Programador de tareas de Windows.
REM
REM %~dp0 se expande a la carpeta donde vive este .bat (con barra final),
REM asi que el "cd /d" garantiza que .env, config/reports.py y
REM playwright/.auth/ se resuelvan sin importar el directorio de trabajo
REM que use la tarea programada.
cd /d "%~dp0"
pythonw.exe main.py
