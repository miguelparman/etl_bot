@echo off
REM Wrapper pensado para ser llamado desde el Programador de tareas de
REM Windows. Usa python.exe (no pythonw.exe) para que el logger escriba
REM tambien en esta consola -- asi se puede ver el progreso en vivo (y el
REM aviso de MFA si la sesion de Salesforce necesita renovarse), igual que
REM al ejecutar main.py desde VSCode.
REM
REM %~dp0 se expande a la carpeta donde vive este .bat (con barra final),
REM asi que el "cd /d" garantiza que .env, config/reports.py y
REM playwright/.auth/ se resuelvan sin importar el directorio de trabajo
REM que use la tarea programada.
cd /d "%~dp0"
python.exe main.py
