@echo off
title Build - Termo Notebook CPE
echo ============================================
echo  CPE - Build Termo Notebook
echo ============================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Criando virtualenv local...
    python -m venv .venv
    if errorlevel 1 (
        echo ERRO: Python nao encontrado. Instale Python 3.11+
        pause
        exit /b 1
    )
) else (
    echo [1/3] Virtualenv ja existe.
)

echo [2/3] Instalando dependencias...
call .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
call .venv\Scripts\pip.exe install -r requirements.txt --quiet

echo [3/3] Gerando executavel (onefile, otimizado)...
call .venv\Scripts\pyinstaller.exe ^
    --noconfirm ^
    --onefile ^
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
echo  EXE onefile gerado:  dist\TermoNotebookCPE.exe
echo ============================================
echo.
pause
