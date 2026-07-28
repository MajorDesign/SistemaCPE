@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: ============================================================
::  CPE Control — Painel de Gerenciamento (UNICO .bat do projeto)
::
::  Substitui (deletados):
::    - Ambiente de Producao.bat
::    - deploy.bat
::    - iniciar_servidor.bat
::    - start.bat
::    - server/iniciar_staging.bat
::
::  Gerencia DOIS ambientes locais:
::    - API Dev      porta 8000  (banco cpe_plus)
::    - API Staging  porta 8001  (banco cpe_plus_staging, dados de prod)
::
::  NOTA: em PRODUCAO (CPEDC22) so existe Dev (8000). As opcoes de
::        staging vao mostrar OFFLINE e iniciar nao tera efeito util
::        sem o .env.staging configurado. Use staging apenas no local.
:: ============================================================

:: ============================================================
:: Guarda de instancia unica
:: ============================================================
set "PANEL_TITLE=CPE Control - Painel de Gerenciamento"
tasklist /V /FI "IMAGENAME eq cmd.exe" /FO CSV 2>nul | findstr /I /C:"%PANEL_TITLE%" >nul
if not errorlevel 1 (
    cls
    echo.
    echo  ==========================================================
    echo   CPE Control ja esta aberto em outra janela.
    echo  ==========================================================
    echo.
    echo   Use a janela existente. Para abrir uma nova sessao,
    echo   feche o painel atual primeiro.
    echo.
    timeout /t 5 /nobreak >nul
    exit /b 1
)
title %PANEL_TITLE%

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "SERVER=%ROOT%\server"
set "VENV_PY=%SERVER%\.venv\Scripts\python.exe"
set "BASH=C:\Program Files\Git\bin\bash.exe"
if not exist "%BASH%" set "BASH=C:\Program Files (x86)\Git\bin\bash.exe"

:: ============================================================
:: Desativa QuickEdit/InsertMode nas janelas das APIs
:: -------------------------------------------------------------
:: Sem isso, qualquer clique acidental dentro da janela
:: PAUSA o processo Python (seleciona texto) ate alguem
:: apertar uma tecla. Resultado: login trava aleatoriamente.
:: A config eh por titulo de janela e fica salva no HKCU.
:: ============================================================
reg add "HKCU\Console\CPE Control API"           /v QuickEdit  /t REG_DWORD /d 0 /f >nul 2>&1
reg add "HKCU\Console\CPE Control API"           /v InsertMode /t REG_DWORD /d 0 /f >nul 2>&1
reg add "HKCU\Console\CPE Control API - STAGING" /v QuickEdit  /t REG_DWORD /d 0 /f >nul 2>&1
reg add "HKCU\Console\CPE Control API - STAGING" /v InsertMode /t REG_DWORD /d 0 /f >nul 2>&1

:MENU
cls
echo.
echo  ==========================================================
echo   CPE Control ^| Painel de Gerenciamento
echo  ==========================================================

call :CHECK_STATUS_DEV
call :CHECK_STATUS_STAGING
call :CHECK_STATUS_CADDY
call :CHECK_STATUS_CLOUDFLARED

if "!DEV_STATUS!"=="ON" (
    echo   API Dev       [ONLINE]   porta 8000  ^(PID !DEV_PID!^)
) else (
    echo   API Dev       [OFFLINE]            porta 8000
)
if "!STAGING_STATUS!"=="ON" (
    echo   API Staging   [ONLINE]   porta 8001  ^(PID !STAGING_PID!^)
) else (
    echo   API Staging   [OFFLINE]            porta 8001
)
if "!CADDY_STATUS!"=="ON" (
    echo   Caddy         [RUNNING]            porta 443 ^(reverse proxy^)
) else if "!CADDY_STATUS!"=="MISSING" (
    echo   Caddy         [nao instalado nesta maquina]
) else (
    echo   Caddy         [STOPPED]            porta 443 ^(reverse proxy^)
)
if "!CF_STATUS!"=="ON" (
    echo   Cloudflared   [RUNNING]            tunnel publico
) else if "!CF_STATUS!"=="MISSING" (
    echo   Cloudflared   [nao instalado nesta maquina]
) else (
    echo   Cloudflared   [STOPPED]            tunnel publico
)
echo  ----------------------------------------------------------
echo.
echo   --- DEV (porta 8000) ---             --- STAGING (porta 8001) ---
echo   [1]  Iniciar API Dev                 [6]  Iniciar API Staging
echo   [2]  Parar API Dev                   [7]  Parar API Staging
echo   [3]  Reiniciar API Dev               [8]  Reiniciar API Staging
echo.
echo   [4]  Deploy Dev  ^(git pull + migrations dev^)
echo   [5]  Deploy + Reiniciar Dev          [9]   Sincronizar prod -^> staging
echo                                        [10]  Aplicar migrations no Staging
echo.
echo   --- INFRA de PRODUCAO (Caddy + Cloudflared) ---
echo   [11] Verificar/Iniciar/Reiniciar Caddy
echo   [12] Verificar/Iniciar/Reiniciar Cloudflared
echo.
echo   [0]  Sair
echo.
set /p "OPC=  Opcao: "

if "%OPC%"=="1"  goto START_DEV
if "%OPC%"=="2"  goto STOP_DEV
if "%OPC%"=="3"  goto RESTART_DEV
if "%OPC%"=="4"  goto DEPLOY
if "%OPC%"=="5"  goto DEPLOY_RESTART
if "%OPC%"=="6"  goto START_STAGING
if "%OPC%"=="7"  goto STOP_STAGING
if "%OPC%"=="8"  goto RESTART_STAGING
if "%OPC%"=="9"  goto SYNC_STAGING
if "%OPC%"=="10" goto MIGRATE_STAGING
if "%OPC%"=="11" goto MANAGE_CADDY
if "%OPC%"=="12" goto MANAGE_CLOUDFLARED
if "%OPC%"=="0"  goto FIM

echo   Opcao invalida.
timeout /t 2 /nobreak >nul
goto MENU

:: ============================================================
:: ============================================================
::                       DEV (porta 8000)
:: ============================================================
:: ============================================================

:START_DEV
echo.
call :CHECK_STATUS_DEV
if "!DEV_STATUS!"=="ON" (
    echo   API Dev ja esta rodando ^(PID !DEV_PID!^). Nenhuma acao necessaria.
    timeout /t 3 /nobreak >nul
    goto MENU
)
echo   [DEV] Iniciando...
start "CPE Control API" /min cmd /k "pushd "%SERVER%" && "%VENV_PY%" app.py"
echo   [DEV] Aguardando subir...
timeout /t 4 /nobreak >nul
call :CHECK_STATUS_DEV
if "!DEV_STATUS!"=="ON" (
    echo   [OK] API Dev no ar ^(PID !DEV_PID!^)
) else (
    echo   [AVISO] API Dev nao respondeu ainda. Verifique a janela minimizada.
)
pause >nul
goto MENU

:STOP_DEV
echo.
call :CHECK_STATUS_DEV
if "!DEV_STATUS!"=="OFF" (
    echo   API Dev ja esta parada.
    timeout /t 2 /nobreak >nul
    goto MENU
)
echo   [DEV] Encerrando PID !DEV_PID!...
taskkill /F /PID !DEV_PID! >nul 2>&1
timeout /t 2 /nobreak >nul
call :CHECK_STATUS_DEV
if "!DEV_STATUS!"=="OFF" (
    echo   [OK] API Dev encerrada.
) else (
    echo   [AVISO] Processo ainda presente. Tente novamente.
)
pause >nul
goto MENU

:RESTART_DEV
echo.
call :CHECK_STATUS_DEV
if "!DEV_STATUS!"=="ON" (
    echo   [DEV] Encerrando PID !DEV_PID!...
    taskkill /F /PID !DEV_PID! >nul 2>&1
    timeout /t 2 /nobreak >nul
)
echo   [DEV] Iniciando com venv...
start "CPE Control API" /min cmd /k "pushd "%SERVER%" && "%VENV_PY%" app.py"
echo   [DEV] Aguardando subir...
timeout /t 4 /nobreak >nul
call :CHECK_STATUS_DEV
if "!DEV_STATUS!"=="ON" (
    echo   [OK] API Dev reiniciada ^(PID !DEV_PID!^)
) else (
    echo   [AVISO] Verifique a janela da API minimizada na barra de tarefas.
)
pause >nul
goto MENU

:: ============================================================
:: ============================================================
::                          DEPLOY
:: ============================================================
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
echo   [2/2] Reiniciando API Dev...
call :CHECK_STATUS_DEV
if "!DEV_STATUS!"=="ON" (
    taskkill /F /PID !DEV_PID! >nul 2>&1
    timeout /t 2 /nobreak >nul
)
start "CPE Control API" /min cmd /k "pushd "%SERVER%" && "%VENV_PY%" app.py"
timeout /t 4 /nobreak >nul
call :CHECK_STATUS_DEV
if "!DEV_STATUS!"=="ON" (
    echo   [OK] Atualizacao completa — API Dev no ar ^(PID !DEV_PID!^)
) else (
    echo   [AVISO] Verifique a janela da API minimizada.
)
pause >nul
goto MENU

:: ============================================================
:: ============================================================
::                     STAGING (porta 8001)
:: ============================================================
:: ============================================================

:START_STAGING
echo.
if not exist "%SERVER%\.env.staging" (
    echo   [ERRO] %SERVER%\.env.staging nao encontrado.
    echo          Staging nao esta configurado nesta maquina.
    pause >nul
    goto MENU
)
call :CHECK_STATUS_STAGING
if "!STAGING_STATUS!"=="ON" (
    echo   API Staging ja esta rodando ^(PID !STAGING_PID!^). Nenhuma acao necessaria.
    timeout /t 3 /nobreak >nul
    goto MENU
)
echo   [STAGING] Iniciando uvicorn na porta 8001 com .env.staging...
start "CPE Control API - STAGING" /min cmd /k "pushd "%SERVER%" && "%VENV_PY%" -m uvicorn app:app --host 0.0.0.0 --port 8001 --env-file .env.staging"
echo   [STAGING] Aguardando subir...
timeout /t 5 /nobreak >nul
call :CHECK_STATUS_STAGING
if "!STAGING_STATUS!"=="ON" (
    echo   [OK] API Staging no ar ^(PID !STAGING_PID!^)
) else (
    echo   [AVISO] API Staging nao respondeu ainda. Verifique a janela minimizada.
)
pause >nul
goto MENU

:STOP_STAGING
echo.
call :CHECK_STATUS_STAGING
if "!STAGING_STATUS!"=="OFF" (
    echo   API Staging ja esta parada.
    timeout /t 2 /nobreak >nul
    goto MENU
)
echo   [STAGING] Encerrando PID !STAGING_PID!...
taskkill /F /PID !STAGING_PID! >nul 2>&1
timeout /t 2 /nobreak >nul
call :CHECK_STATUS_STAGING
if "!STAGING_STATUS!"=="OFF" (
    echo   [OK] API Staging encerrada.
) else (
    echo   [AVISO] Processo ainda presente. Tente novamente.
)
pause >nul
goto MENU

:RESTART_STAGING
echo.
if not exist "%SERVER%\.env.staging" (
    echo   [ERRO] %SERVER%\.env.staging nao encontrado.
    pause >nul
    goto MENU
)
call :CHECK_STATUS_STAGING
if "!STAGING_STATUS!"=="ON" (
    echo   [STAGING] Encerrando PID !STAGING_PID!...
    taskkill /F /PID !STAGING_PID! >nul 2>&1
    timeout /t 2 /nobreak >nul
)
echo   [STAGING] Iniciando uvicorn na porta 8001...
start "CPE Control API - STAGING" /min cmd /k "pushd "%SERVER%" && "%VENV_PY%" -m uvicorn app:app --host 0.0.0.0 --port 8001 --env-file .env.staging"
echo   [STAGING] Aguardando subir...
timeout /t 5 /nobreak >nul
call :CHECK_STATUS_STAGING
if "!STAGING_STATUS!"=="ON" (
    echo   [OK] API Staging reiniciada ^(PID !STAGING_PID!^)
) else (
    echo   [AVISO] Verifique a janela da API minimizada.
)
pause >nul
goto MENU

:SYNC_STAGING
echo.
if not exist "%ROOT%\tools\sync_staging.py" (
    echo   [ERRO] %ROOT%\tools\sync_staging.py nao encontrado.
    pause >nul
    goto MENU
)
echo   [SYNC] Copiando dados de PRODUCAO ^(CPEDC22^) para cpe_plus_staging local...
echo.
echo   ATENCAO: isso apaga e reimporta o banco cpe_plus_staging local.
set /p "CONFIRMA=  Confirma? (s/n): "
if /i not "%CONFIRMA%"=="s" (
    echo   Cancelado.
    timeout /t 2 /nobreak >nul
    goto MENU
)
echo.
"%VENV_PY%" "%ROOT%\tools\sync_staging.py"
echo.
echo   Sync finalizado. Reinicie a API Staging para usar os dados novos.
pause >nul
goto MENU

:MIGRATE_STAGING
echo.
if not exist "%SERVER%\.env.staging" (
    echo   [ERRO] %SERVER%\.env.staging nao encontrado.
    echo          Staging nao esta configurado nesta maquina.
    pause >nul
    goto MENU
)
if not exist "%BASH%" (
    echo   [ERRO] Git Bash nao encontrado. Instale o Git for Windows.
    pause >nul
    goto MENU
)
echo   [MIGRATE STAGING] Aplicando migrations pendentes em cpe_plus_staging...
echo.
"%BASH%" "%ROOT%/apply_migrations.sh" server/.env.staging
echo.
echo   Para a API Staging usar o novo schema, reinicie pela opcao [8].
pause >nul
goto MENU

:: ============================================================
:: ============================================================
::            INFRA DE PRODUCAO (Caddy + Cloudflared)
:: ============================================================
:: ============================================================
::
:: Estes 2 servicos so existem no servidor CPEDC22. No PC de dev
:: os checks vao retornar MISSING e as opcoes vao avisar.
:: net start/stop requer Administrador — o codigo checa e avisa.

:MANAGE_CADDY
echo.
call :CHECK_STATUS_CADDY
if "!CADDY_STATUS!"=="MISSING" (
    echo   Servico "Caddy" nao existe nesta maquina.
    echo   Esta acao so vale no servidor de producao CPEDC22.
    pause >nul
    goto MENU
)
if "!CADDY_STATUS!"=="ON" (
    echo   Caddy [RUNNING] — testando resposta local em https://127.0.0.1/ ...
    set "CADDY_HTTP=err"
    for /f "delims=" %%H in ('curl.exe -k -sS -o NUL -w "%%{http_code}" --max-time 5 https://127.0.0.1/ 2^>nul') do set "CADDY_HTTP=%%H"
    if "!CADDY_HTTP!"=="err" (
        echo   [ALERTA] Caddy respondeu com FALHA de conexao — provavelmente TRAVADO.
        echo            ^(bug conhecido: porta escuta mas nao responde^)
    ) else (
        echo   [OK] Caddy respondeu HTTP !CADDY_HTTP! em 127.0.0.1
    )
    echo.
    set "OPC="
    set /p "OPC=  [R] Reiniciar Caddy  ^| [Enter] voltar: "
    if /i "!OPC!"=="R" (
        call :REQUIRE_ADMIN || goto MENU
        echo   Parando Caddy...
        net stop Caddy
        timeout /t 2 /nobreak >nul
        echo   Iniciando Caddy...
        net start Caddy
        timeout /t 3 /nobreak >nul
        call :CHECK_STATUS_CADDY
        echo   Status pos-restart: !CADDY_STATUS!
    )
) else (
    echo   Caddy [STOPPED]
    echo.
    set "OPC="
    set /p "OPC=  [S] Iniciar Caddy    ^| [Enter] voltar: "
    if /i "!OPC!"=="S" (
        call :REQUIRE_ADMIN || goto MENU
        echo   Iniciando Caddy...
        net start Caddy
        timeout /t 3 /nobreak >nul
        call :CHECK_STATUS_CADDY
        echo   Status pos-start: !CADDY_STATUS!
    )
)
pause >nul
goto MENU

:MANAGE_CLOUDFLARED
echo.
call :CHECK_STATUS_CLOUDFLARED
if "!CF_STATUS!"=="MISSING" (
    echo   Servico "Cloudflared" nao existe nesta maquina.
    echo   Esta acao so vale no servidor de producao CPEDC22.
    pause >nul
    goto MENU
)
if "!CF_STATUS!"=="ON" (
    echo   Cloudflared [RUNNING] — testando dominio publico ...
    set "CF_HTTP=err"
    for /f "delims=" %%H in ('curl.exe -sS -o NUL -w "%%{http_code}" --max-time 10 https://cpecontrol.cpetecnologia.com.br/ 2^>nul') do set "CF_HTTP=%%H"
    if "!CF_HTTP!"=="err" (
        echo   [ALERTA] dominio publico nao respondeu ^(pode ser Caddy tambem^).
    ) else if "!CF_HTTP!"=="530" (
        echo   [ALERTA] Cloudflare retornou 530 — tunnel morto ou origin caido.
    ) else (
        echo   [OK] cpecontrol.cpetecnologia.com.br respondeu HTTP !CF_HTTP!
    )
    echo.
    set "OPC="
    set /p "OPC=  [R] Reiniciar Cloudflared  ^| [Enter] voltar: "
    if /i "!OPC!"=="R" (
        call :REQUIRE_ADMIN || goto MENU
        echo   Parando Cloudflared...
        net stop Cloudflared
        timeout /t 2 /nobreak >nul
        echo   Iniciando Cloudflared...
        net start Cloudflared
        echo   Aguardando tunnel reconectar ^(15s^)...
        timeout /t 15 /nobreak >nul
        call :CHECK_STATUS_CLOUDFLARED
        echo   Status pos-restart: !CF_STATUS!
    )
) else (
    echo   Cloudflared [STOPPED]
    echo   ^(sistema fica INACESSIVEL externamente ate iniciar^)
    echo.
    set "OPC="
    set /p "OPC=  [S] Iniciar Cloudflared    ^| [Enter] voltar: "
    if /i "!OPC!"=="S" (
        call :REQUIRE_ADMIN || goto MENU
        echo   Iniciando Cloudflared...
        net start Cloudflared
        echo   Aguardando tunnel reconectar ^(15s^)...
        timeout /t 15 /nobreak >nul
        call :CHECK_STATUS_CLOUDFLARED
        echo   Status pos-start: !CF_STATUS!
    )
)
pause >nul
goto MENU

:: ============================================================
:FIM
endlocal
exit /b 0

:: ============================================================
:: Subrotinas de status (define VAR_STATUS=ON/OFF e VAR_PID)
:: ============================================================

:CHECK_STATUS_DEV
set "DEV_STATUS=OFF"
set "DEV_PID="
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    set "DEV_PID=%%P"
    set "DEV_STATUS=ON"
)
exit /b 0

:CHECK_STATUS_STAGING
set "STAGING_STATUS=OFF"
set "STAGING_PID="
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":8001 " ^| findstr "LISTENING"') do (
    set "STAGING_PID=%%P"
    set "STAGING_STATUS=ON"
)
exit /b 0

:: Servico Caddy: retorna CADDY_STATUS = ON | OFF | MISSING
:: sc query SEMPRE retorna errorlevel=0 (mesmo se servico nao existe),
:: entao a deteccao e via output — procura RUNNING primeiro, senao
:: STOPPED (ou START_PENDING). Se nenhum bate, o servico nao existe.
:CHECK_STATUS_CADDY
set "CADDY_STATUS=MISSING"
sc query Caddy 2>&1 | findstr /C:"RUNNING" >nul && set "CADDY_STATUS=ON"
if "!CADDY_STATUS!"=="MISSING" sc query Caddy 2>&1 | findstr /R /C:"STOPPED" /C:"START_PENDING" /C:"PAUSED" >nul && set "CADDY_STATUS=OFF"
exit /b 0

:: Servico Cloudflared: retorna CF_STATUS = ON | OFF | MISSING
:CHECK_STATUS_CLOUDFLARED
set "CF_STATUS=MISSING"
sc query Cloudflared 2>&1 | findstr /C:"RUNNING" >nul && set "CF_STATUS=ON"
if "!CF_STATUS!"=="MISSING" sc query Cloudflared 2>&1 | findstr /R /C:"STOPPED" /C:"START_PENDING" /C:"PAUSED" >nul && set "CF_STATUS=OFF"
exit /b 0

:: Verifica se o bat esta rodando com privilegio de Administrador.
:: Retorna 0 se ADMIN, 1 se nao (com mensagem). Chamador usa || pra abortar.
:REQUIRE_ADMIN
net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERRO] Esta acao precisa de privilegios de Administrador.
    echo          Feche este painel e reabra com "Executar como administrador".
    echo.
    exit /b 1
)
exit /b 0
