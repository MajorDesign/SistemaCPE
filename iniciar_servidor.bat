@echo off
title CPE Control API - Servidor
echo ============================================
echo  CPE Control API - Iniciando servidor...
echo ============================================

:: Matar processos Python antigos
echo [1/3] Encerrando processos anteriores...
taskkill /F /IM python.exe /T 2>nul
timeout /t 2 /nobreak >nul

:: Verificar se porta 8000 ficou livre
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul
if %ERRORLEVEL%==0 (
    echo [AVISO] Porta 8000 ainda ocupada. Tente reiniciar o computador se continuar.
)

:: Ativar virtualenv e iniciar servidor
echo [2/3] Ativando ambiente virtual...
cd /d "%~dp0server"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERRO] Virtualenv nao encontrado em server\.venv\
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo [3/3] Iniciando servidor FastAPI...
echo.
echo  Acesse: http://127.0.0.1:8000/docs
echo  Para parar: feche esta janela ou pressione Ctrl+C
echo.

python app.py

pause
