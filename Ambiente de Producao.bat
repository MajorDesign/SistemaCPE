@echo off
chcp 65001 >nul
title Ambiente de Producao - SistemaCPE

echo.
echo =============================================
echo  AMBIENTE DE PRODUCAO - SistemaCPE
echo =============================================
echo.
echo  Escolha uma opcao:
echo.
echo  [1] Deploy completo (git pull + migrations)
echo  [2] Reiniciar API
echo  [3] Deploy + Reiniciar API
echo  [4] Ver logs da API
echo  [5] Sair
echo.
set /p opcao="  Opcao: "

if "%opcao%"=="1" goto deploy
if "%opcao%"=="2" goto reiniciar
if "%opcao%"=="3" goto tudo
if "%opcao%"=="4" goto logs
if "%opcao%"=="5" goto fim

echo Opcao invalida.
pause >nul
goto fim

:: --------------------------------------------------
:deploy
echo.
echo [DEPLOY] Atualizando codigo e migrations...
echo.
set BASH="C:\Program Files\Git\bin\bash.exe"
if not exist %BASH% set BASH="C:\Program Files (x86)\Git\bin\bash.exe"
%BASH% /e/xampp/htdocs/SistemaCPE/deploy.sh
echo.
echo Deploy concluido!
pause >nul
goto fim

:: --------------------------------------------------
:reiniciar
echo.
echo [API] Encerrando processo Python...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul
echo [API] Iniciando API em nova janela...
start "API CPE - Producao" cmd /k "cd /d E:\xampp\htdocs\SistemaCPE\server && python app.py"
echo.
echo API reiniciada! Aguarde alguns segundos para ela subir.
pause >nul
goto fim

:: --------------------------------------------------
:tudo
echo.
echo [1/2] Rodando deploy...
set BASH="C:\Program Files\Git\bin\bash.exe"
if not exist %BASH% set BASH="C:\Program Files (x86)\Git\bin\bash.exe"
%BASH% /e/xampp/htdocs/SistemaCPE/deploy.sh
echo.
echo [2/2] Reiniciando API...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul
start "API CPE - Producao" cmd /k "cd /d E:\xampp\htdocs\SistemaCPE\server && python app.py"
echo.
echo Tudo pronto! API subindo em nova janela.
pause >nul
goto fim

:: --------------------------------------------------
:logs
echo.
echo [LOGS] Exibindo ultimas 50 linhas do log...
echo (Ctrl+C para sair)
echo.
set BASH="C:\Program Files\Git\bin\bash.exe"
if not exist %BASH% set BASH="C:\Program Files (x86)\Git\bin\bash.exe"
%BASH% -c "tail -f /e/xampp/htdocs/SistemaCPE/server/logs/api.log 2>/dev/null || echo 'Arquivo de log nao encontrado.'"
pause >nul
goto fim

:: --------------------------------------------------
:fim
exit
