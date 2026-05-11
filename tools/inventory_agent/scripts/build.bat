@echo off
title Build - CPE Agente de Inventario T.I.
chcp 65001 >nul
echo ============================================
echo  CPE - Build Agente de Inventario T.I.
echo ============================================

REM Sobe de scripts\ para tools\inventory_agent\
cd /d "%~dp0.."

REM Le VERSAO do CPEAgente.py (linha: VERSAO = "x.y.z")
set "VER="
for /f "usebackq tokens=2 delims==" %%v in (`findstr /R "^VERSAO" CPEAgente.py`) do (
    if not defined VER (
        set "RAW=%%v"
        setlocal enabledelayedexpansion
        set "RAW=!RAW: =!"
        set "RAW=!RAW:"=!"
        endlocal & set "VER=%%v"
    )
)
REM Limpeza simples (remove aspas e espacos)
set "VER=%VER:"=%"
set "VER=%VER: =%"

if "%VER%"=="" (
    echo ERRO: nao consegui ler VERSAO de CPEAgente.py
    pause & exit /b 1
)
echo Versao detectada: v%VER%
echo.

REM venv local
if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Criando virtualenv local...
    python -m venv .venv
    if errorlevel 1 (
        echo ERRO: Python 3.11+ nao encontrado no PATH.
        pause & exit /b 1
    )
) else (
    echo [1/4] Virtualenv ja existe.
)

echo [2/4] Instalando dependencias + PyInstaller...
call .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
call .venv\Scripts\pip.exe install --quiet ^
    psutil requests pystray Pillow pyinstaller

echo [3/4] Gerando executavel (onefile, sem console)...
call .venv\Scripts\pyinstaller.exe ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "CPEAgente" ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module PyQt5 ^
    --exclude-module PyQt6 ^
    --exclude-module PySide2 ^
    --exclude-module PySide6 ^
    --exclude-module scipy ^
    --exclude-module pytest ^
    --exclude-module test ^
    --exclude-module unittest ^
    CPEAgente.py
if errorlevel 1 ( echo ERRO no PyInstaller & pause & exit /b 1 )

echo [4/4] Publicando em release\ com versao no nome...
if not exist "release" mkdir "release"
REM Mantem apenas a release atual
del /q "release\CPEAgente_v*.exe" 2>nul
copy /y "dist\CPEAgente.exe" "release\CPEAgente_v%VER%.exe" >nul

echo.
echo ============================================
echo  OK! Nova release publicada:
echo   release\CPEAgente_v%VER%.exe
echo.
echo  Backend /api/inventario/agent/version ja vai
echo  responder com a versao nova. As maquinas
echo  instaladas se auto-atualizam no proximo
echo  heartbeat (ate 5 min).
echo ============================================
pause
