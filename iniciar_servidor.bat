@echo off
title CPE Control API - Servidor
echo ============================================
echo  CPE Control API - Iniciando servidor...
echo ============================================

:: Matar processos Python antigos
echo [1/4] Encerrando processos anteriores...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul

:: Verificar se porta 8000 ficou livre
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if %ERRORLEVEL%==0 (
    echo [AVISO] Porta 8000 ainda ocupada. Tente reiniciar o computador se continuar.
)

set "SERVER_DIR=%~dp0server"

:: Validar virtualenv (opcional — se nao existir, usa o python do PATH)
echo [2/4] Verificando virtualenv...
if exist "%SERVER_DIR%\.venv\Scripts\python.exe" (
    set "PY_EXE=%SERVER_DIR%\.venv\Scripts\python.exe"
    echo       Usando venv: %SERVER_DIR%\.venv
) else (
    set "PY_EXE=python"
    echo       venv nao encontrado, usando python do PATH
)

echo [3/4] Iniciando servidor FastAPI em nova janela...
:: Importante: usar start para desacoplar do .bat e manter a API rodando
:: mesmo depois de fechar esta janela ou desconectar o RDP. Mesma estrategia
:: usada no Ambiente de Producao.bat (opcao 2).
start "API CPE" cmd /k "cd /d "%SERVER_DIR%" && "%PY_EXE%" app.py"

echo [4/4] OK. API iniciada em janela separada.
echo.
echo  Acesse: http://127.0.0.1:8000/docs
echo  Para parar a API: feche a janela "API CPE" que abriu.
echo.

timeout /t 3 /nobreak >nul
exit /b 0
