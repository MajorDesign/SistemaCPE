@echo off
title Build - Termo Notebook CPE
echo ============================================
echo  CPE - Build Termo Notebook
echo ============================================

REM Sobe de scripts\ para tools\termo_notebook\
cd /d "%~dp0.."

REM Versao ANTIGA (apenas para log)
set "VER_OLD="
for /f "usebackq delims=" %%v in ("VERSION") do if not defined VER_OLD set "VER_OLD=%%v"
if "%VER_OLD%"=="" set "VER_OLD=0.0.0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/5] Criando virtualenv local...
    python -m venv .venv
    if errorlevel 1 (
        echo ERRO: Python nao encontrado. Instale Python 3.11+
        pause
        exit /b 1
    )
) else (
    echo [1/5] Virtualenv ja existe.
)

echo [2/5] Instalando dependencias...
call .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
call .venv\Scripts\pip.exe install -r requirements.txt --quiet

REM Bump automatico: cada build gera uma versao nova
echo [3/5] Incrementando versao (patch +1)...
set "VER="
for /f "usebackq delims=" %%v in (`call .venv\Scripts\python.exe scripts\bump_version.py`) do set "VER=%%v"
if "%VER%"=="" (
    echo ERRO ao incrementar versao.
    pause
    exit /b 1
)
echo    v%VER_OLD%  -->  v%VER%
echo.

echo [4/5] Gerando executavel (onefile)...
call .venv\Scripts\pyinstaller.exe ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "TermoNotebookCPE" ^
    --add-data "logo.png;." ^
    --add-data "VERSION;." ^
    --add-data "config.ini;." ^
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
if errorlevel 1 ( echo ERRO no PyInstaller & pause & exit /b 1 )

echo [5/5] Publicando em release\ (versao no nome)...
if not exist "release" mkdir "release"
REM Apaga versao anterior para release ficar sempre com 1 unico arquivo
del /q "release\TermoNotebookCPE_v*.exe" 2>nul
copy /y "dist\TermoNotebookCPE.exe" "release\TermoNotebookCPE_v%VER%.exe" >nul

echo.
echo ============================================
echo  OK! Nova release publicada automaticamente:
echo   release\TermoNotebookCPE_v%VER%.exe
echo.
echo  A pagina /web/pages/download-agents.html ja
echo  mostra a versao nova — basta dar Ctrl+F5.
echo ============================================
pause
