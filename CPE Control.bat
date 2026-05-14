@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================================
::  CPE Control — Painel de Gerenciamento
::  Substitui: Ambiente de Producao.bat, deploy.bat, iniciar_servidor.bat
:: ============================================================

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "SERVER=%ROOT%\server"
set "VENV_PY=%SERVER%\.venv\Scripts\python.exe"
set "BASH=C:\Program Files\Git\bin\bash.exe"
if not exist "%BASH%" set "BASH=C:\Program Files (x86)\Git\bin\bash.exe"

:MENU
cls
echo.
echo  ==========================================================
echo   CPE Control ^| Painel de Gerenciamento
echo  ==========================================================

:: --- Status da API ---
call :CHECK_STATUS
if "!API_STATUS!"=="ON" (
    echo   API  [ONLINE]  porta 8000  ^(PID !API_PID!^)
) else (
    echo   API  [OFFLINE]
)
echo  ----------------------------------------------------------
echo.
echo   [1]  Iniciar API
echo   [2]  Parar API
echo   [3]  Reiniciar API
echo   [4]  Deploy  ^(git pull + migrations^)
echo   [5]  Deploy + Reiniciar  ^(atualizacao completa^)
echo   [0]  Sair
echo.
set /p "OPC=  Opcao: "

if "%OPC%"=="1" goto START_API
if "%OPC%"=="2" goto STOP_API
if "%OPC%"=="3" goto RESTART_API
if "%OPC%"=="4" goto DEPLOY
if "%OPC%"=="5" goto DEPLOY_RESTART
if "%OPC%"=="0" goto FIM

echo   Opcao invalida.
timeout /t 2 /nobreak >nul
goto MENU

:: ============================================================
:START_API
echo.
call :CHECK_STATUS
if "!API_STATUS!"=="ON" (
    echo   API ja esta rodando ^(PID !API_PID!^). Nenhuma acao necessaria.
    timeout /t 3 /nobreak >nul
    goto MENU
)
echo   [API] Iniciando...
start "CPE Control API" /min cmd /k "cd /d "%SERVER%" && "%VENV_PY%" app.py"
echo   [API] Aguardando subir...
timeout /t 4 /nobreak >nul
call :CHECK_STATUS
if "!API_STATUS!"=="ON" (
    echo   [OK] API no ar ^(PID !API_PID!^)
) else (
    echo   [AVISO] API nao respondeu ainda. Verifique a janela minimizada.
)
pause >nul
goto MENU

:: ============================================================
:STOP_API
echo.
call :CHECK_STATUS
if "!API_STATUS!"=="OFF" (
    echo   API ja esta parada.
    timeout /t 2 /nobreak >nul
    goto MENU
)
echo   [API] Encerrando PID !API_PID!...
taskkill /F /PID !API_PID! >nul 2>&1
timeout /t 2 /nobreak >nul
call :CHECK_STATUS
if "!API_STATUS!"=="OFF" (
    echo   [OK] API encerrada.
) else (
    echo   [AVISO] Processo ainda presente. Tente novamente.
)
pause >nul
goto MENU

:: ============================================================
:RESTART_API
echo.
call :CHECK_STATUS
if "!API_STATUS!"=="ON" (
    echo   [API] Encerrando PID !API_PID!...
    taskkill /F /PID !API_PID! >nul 2>&1
    timeout /t 2 /nobreak >nul
)
echo   [API] Iniciando com venv...
start "CPE Control API" /min cmd /k "cd /d "%SERVER%" && "%VENV_PY%" app.py"
echo   [API] Aguardando subir...
timeout /t 4 /nobreak >nul
call :CHECK_STATUS
if "!API_STATUS!"=="ON" (
    echo   [OK] API reiniciada ^(PID !API_PID!^)
) else (
    echo   [AVISO] Verifique a janela da API minimizada na barra de tarefas.
)
pause >nul
goto MENU

:: ============================================================
:DEPLOY
echo.
echo   [DEPLOY] Rodando git pull + migrations...
echo.
if not exist "%BASH%" (
    echo   [ERRO] Git Bash nao encontrado. Instale o Git for Windows.
    pause >nul
    goto MENU
)
"%BASH%" "%ROOT%/deploy.sh"
echo.
echo   Deploy concluido. A API ainda esta rodando com o codigo anterior.
echo   Use a opcao [3] Reiniciar para aplicar as mudancas.
pause >nul
goto MENU

:: ============================================================
:DEPLOY_RESTART
echo.
echo   [1/2] Rodando deploy...
if not exist "%BASH%" (
    echo   [ERRO] Git Bash nao encontrado.
    pause >nul
    goto MENU
)
"%BASH%" "%ROOT%/deploy.sh"
echo.
echo   [2/2] Reiniciando API...
call :CHECK_STATUS
if "!API_STATUS!"=="ON" (
    taskkill /F /PID !API_PID! >nul 2>&1
    timeout /t 2 /nobreak >nul
)
start "CPE Control API" /min cmd /k "cd /d "%SERVER%" && "%VENV_PY%" app.py"
timeout /t 4 /nobreak >nul
call :CHECK_STATUS
if "!API_STATUS!"=="ON" (
    echo   [OK] Atualizacao completa — API no ar ^(PID !API_PID!^)
) else (
    echo   [AVISO] Verifique a janela da API minimizada.
)
pause >nul
goto MENU

:: ============================================================
:FIM
endlocal
exit /b 0

:: ============================================================
:: Subrotina: detecta se a API esta rodando na porta 8000
:: Define API_STATUS (ON/OFF) e API_PID
:CHECK_STATUS
set "API_STATUS=OFF"
set "API_PID="
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    set "API_PID=%%P"
    set "API_STATUS=ON"
)
exit /b 0
