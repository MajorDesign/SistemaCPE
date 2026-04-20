@echo off
title Build RAPIDO - Termo Notebook CPE (onedir)
echo ============================================
echo  CPE - Build ONEDIR (abertura instantanea)
echo ============================================
echo.
echo  Gera uma PASTA em vez de arquivo unico.
echo  Abertura muito mais rapida (~1s vs ~8s).
echo  Deve ser distribuida completa (toda a pasta dist\TermoNotebookCPE\).
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Criando virtualenv...
    python -m venv .venv
)

call .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
call .venv\Scripts\pip.exe install -r requirements.txt --quiet

echo Gerando executavel (onedir)...
call .venv\Scripts\pyinstaller.exe ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name "TermoNotebookCPE" ^
    --add-data "logo.png;." ^
    --icon=logo.png ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module PIL.ImageQt ^
    --exclude-module PyQt5 ^
    --exclude-module PyQt6 ^
    --exclude-module PySide2 ^
    --exclude-module PySide6 ^
    --exclude-module scipy ^
    --exclude-module pytest ^
    --exclude-module test ^
    --exclude-module unittest ^
    termo_notebook.py

echo.
echo ============================================
echo  Concluido!
echo  Pasta gerada: dist\TermoNotebookCPE\
echo  Executavel:   dist\TermoNotebookCPE\TermoNotebookCPE.exe
echo.
echo  Distribua a PASTA INTEIRA para as maquinas clientes.
echo ============================================
pause
