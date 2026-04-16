@echo off
echo Iniciando CPE Sistema...
echo.

cd /d "%~dp0server"
.venv\Scripts\python.exe app.py
