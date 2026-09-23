@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM ============================================================
REM  Atualizar-VPN-CPE.bat v1.0.0 (2026-09-23)
REM  Baixa o perfil OpenVPN da CPE do servidor CPECONTROL e
REM  aplica na pasta local de config do OpenVPN.
REM
REM  Basta rodar o arquivo. Ele pede elevacao sozinho.
REM  Deixe o arquivo em qualquer pasta com permissao de escrita
REM  (o log fica ao lado dele).
REM ============================================================

set "PKG_SLUG=vpn-openvpn"
set "SERVER_BASE=https://cpecontrol.cpetecnologia.com.br"
set "PKG_TOKEN=__PKG_TOKEN__"
set "OPENVPN_DIR=C:\Program Files\OpenVPN"

REM ---- Autoelevacao UAC ---------------------------------------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permissao de administrador...
    powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
    exit /b
)

REM ---- Setup do log ------------------------------------------
set "LOG_DIR=%~dp0"
set "TIMESTAMP=%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%-%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "LOGFILE=%LOG_DIR%Log-Atualizacao-VPN_%COMPUTERNAME%_%TIMESTAMP%.txt"
echo probe > "%LOGFILE%" 2>nul
if not exist "%LOGFILE%" (
    set "LOG_DIR=%PUBLIC%\Documents\"
    set "LOGFILE=%PUBLIC%\Documents\Log-Atualizacao-VPN_%COMPUTERNAME%_%TIMESTAMP%.txt"
)
del "%LOGFILE%" >nul 2>&1

set "ERR_COUNT=0"
set "RESULT_STATUS=SUCESSO"
set "BACKUP_DIR="
set "OPENVPN_LOG=%USERPROFILE%\OpenVPN\log\OpenVPN_CPETecnologia.log"

call :log "=========================================="
call :log " ATUALIZACAO DE VPN - CPE TECNOLOGIA"
call :log "=========================================="
call :log " Data/Hora   : %DATE% %TIME%"
call :log " Computador  : %COMPUTERNAME%"
call :log " Usuario     : %USERDOMAIN%\%USERNAME%"
for /f "delims=" %%v in ('ver') do call :log " Windows     : %%v"
call :log " Bat         : %~f0"
call :log " Log         : %LOGFILE%"
call :log ""

REM ---- 1. OpenVPN instalado? ---------------------------------
if not exist "%OPENVPN_DIR%\bin\openvpn-gui.exe" (
    call :log "[ERRO] OpenVPN nao encontrado em: %OPENVPN_DIR%"
    call :log "       Instale o OpenVPN antes de rodar este script."
    set "RESULT_STATUS=FALHA"
    goto :finalizar
)
call :log "[OK] OpenVPN instalado em: %OPENVPN_DIR%"
for /f "tokens=1-4 delims= " %%a in ('""%OPENVPN_DIR%\bin\openvpn.exe" --version" 2^>^&1 ^| findstr /I /C:"OpenVPN"') do (
    call :log "[INFO] Versao: %%a %%b %%c %%d"
    goto :continua_versao
)
:continua_versao

REM ---- 2. Baixar manifesto + arquivos temp -------------------
set "TMPBASE=%TEMP%\cpe-vpn-update-%RANDOM%"
mkdir "%TMPBASE%" 2>nul
call :log ""
call :log "[INFO] Pasta temp: %TMPBASE%"

set "MANIFEST_URL=%SERVER_BASE%/api/packages/%PKG_SLUG%/manifest"
set "MANIFEST_FILE=%TMPBASE%\manifest.json"

call :log "[INFO] Baixando manifesto: %MANIFEST_URL%"
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol='Tls12'; Invoke-WebRequest -UseBasicParsing -Uri '%MANIFEST_URL%' -Headers @{'X-Package-Token'='%PKG_TOKEN%'} -OutFile '%MANIFEST_FILE%'" 2>>"%LOGFILE%"
if %errorlevel% neq 0 (
    call :log "[ERRO] Falha ao baixar manifesto. Sem alterar nada."
    set "RESULT_STATUS=FALHA"
    goto :finalizar
)
if not exist "%MANIFEST_FILE%" (
    call :log "[ERRO] Manifesto nao chegou. Sem alterar nada."
    set "RESULT_STATUS=FALHA"
    goto :finalizar
)
call :log "[OK] Manifesto baixado."

for /f "delims=" %%v in ('powershell -NoProfile -Command "(Get-Content '%MANIFEST_FILE%' -Raw ^| ConvertFrom-Json).version"') do set "PKG_VERSION=%%v"
call :log "[INFO] Versao do pacote: %PKG_VERSION%"

call :log ""
call :log "[INFO] Baixando e verificando arquivos..."
powershell -NoProfile -Command "$ErrorActionPreference='Stop';[Net.ServicePointManager]::SecurityProtocol='Tls12';$m=Get-Content '%MANIFEST_FILE%' -Raw|ConvertFrom-Json;foreach($f in $m.files){$u='%SERVER_BASE%'+$f.url;$o=Join-Path '%TMPBASE%' $f.name;Write-Host ('  ' + $f.name);Invoke-WebRequest -UseBasicParsing -Uri $u -Headers @{'X-Package-Token'='%PKG_TOKEN%'} -OutFile $o;$h=(Get-FileHash $o -Algorithm SHA256).Hash.ToLower();if($h -ne $f.sha256.ToLower()){throw 'Hash divergente em '+$f.name+'. Esperado '+$f.sha256+' recebido '+$h}}" 1>>"%LOGFILE%" 2>>"%LOGFILE%"
if %errorlevel% neq 0 (
    call :log "[ERRO] Falha no download ou na verificacao SHA256. Sem alterar nada."
    set "RESULT_STATUS=FALHA"
    goto :finalizar
)
call :log "[OK] Todos os arquivos baixados e verificados."

REM ---- 3. Fecha OpenVPN + para servicos ----------------------
call :log ""
call :log "[INFO] Fechando OpenVPN..."
taskkill /F /IM openvpn-gui.exe >nul 2>&1
taskkill /F /IM openvpn.exe >nul 2>&1
sc stop OpenVPNService >nul 2>&1
sc stop OpenVPNServiceInteractive >nul 2>&1
timeout /t 2 /nobreak >nul
call :log "[OK] Processos e servicos parados."

REM ---- 4. Backup + limpa config ------------------------------
set "BACKUP_DIR=%OPENVPN_DIR%\config-backup-%TIMESTAMP%"
call :log ""
call :log "[INFO] Backup da config atual em: %BACKUP_DIR%"
xcopy "%OPENVPN_DIR%\config" "%BACKUP_DIR%" /E /I /Y /Q >nul 2>&1
if %errorlevel% neq 0 (
    call :log "[AVISO] Backup pode ter falhado parcialmente."
)
call :log "[INFO] Conteudo ANTES:"
dir /B "%OPENVPN_DIR%\config" 2>nul >>"%LOGFILE%"

call :log "[INFO] Apagando conteudo de config..."
attrib -r -h -s "%OPENVPN_DIR%\config\*" /S /D >nul 2>&1
del /F /Q "%OPENVPN_DIR%\config\*.*" >nul 2>&1
for /d %%d in ("%OPENVPN_DIR%\config\*") do rd /S /Q "%%d" >nul 2>&1
call :log "[OK] Pasta config limpa."

REM ---- 5. Copia novos + verifica fc /b -----------------------
call :log ""
call :log "[INFO] Copiando arquivos novos..."
for %%f in ("%TMPBASE%\*") do (
    if /I not "%%~nxf"=="manifest.json" (
        copy /Y "%%f" "%OPENVPN_DIR%\config\%%~nxf" >nul 2>&1
        if !errorlevel! neq 0 (
            call :log "[ERRO] Falha ao copiar %%~nxf"
            set /a ERR_COUNT+=1
        ) else (
            fc /b "%%f" "%OPENVPN_DIR%\config\%%~nxf" >nul 2>&1
            if !errorlevel! neq 0 (
                call :log "[ERRO] fc /b divergente em %%~nxf"
                set /a ERR_COUNT+=1
            ) else (
                call :log "[OK]  %%~nxf copiado e verificado"
            )
        )
    )
)

call :log ""
call :log "[INFO] Conteudo DEPOIS:"
dir /B "%OPENVPN_DIR%\config" 2>nul >>"%LOGFILE%"

if %ERR_COUNT% gtr 0 (
    call :log "[ERRO] %ERR_COUNT% erro(s) na copia. Backup em: %BACKUP_DIR%"
    set "RESULT_STATUS=FALHA"
    goto :finalizar
)

rd /S /Q "%TMPBASE%" >nul 2>&1

REM ---- 6. Sobe servico + abre GUI ----------------------------
call :log ""
call :log "[INFO] Iniciando OpenVPNServiceInteractive..."
sc start OpenVPNServiceInteractive >nul 2>&1
timeout /t 2 /nobreak >nul

call :log "[INFO] Abrindo OpenVPN GUI (--connect OpenVPN_CPETecnologia.ovpn)..."
start "" "%OPENVPN_DIR%\bin\openvpn-gui.exe" --connect OpenVPN_CPETecnologia.ovpn

REM ---- 7. Testa conexao (2 min timeout) ----------------------
call :log ""
call :log "[INFO] Aguardando conexao VPN (ate 2 min)..."
set "TVPN_OK=0"
set "TVPN_IP="
for /L %%i in (1,1,24) do (
    timeout /t 5 /nobreak >nul
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /R /C:"IPv4.*192\.168\.16\."') do (
        set "TVPN_IP=%%a"
        set "TVPN_IP=!TVPN_IP: =!"
        set "TVPN_OK=1"
        goto :vpn_conectada
    )
)

:vpn_conectada
if "%TVPN_OK%"=="1" (
    call :log "[OK] VPN conectada. IP recebido: !TVPN_IP!"

    for %%h in (172.16.12.1 172.16.0.10 172.16.1.10) do (
        ping -n 2 -w 1000 %%h >nul 2>&1
        if !errorlevel! equ 0 (
            call :log "[OK] Ping %%h"
        ) else (
            call :log "[AVISO] Sem resposta ping %%h (nao e erro fatal)"
        )
    )

    call :log ""
    call :log "[INFO] Rotas 172.16.x recebidas via VPN:"
    route print -4 ^| findstr "172.16" >>"%LOGFILE%" 2>&1
) else (
    call :log "[AVISO] Conexao VPN nao confirmada apos 2 min."
    call :log "        Arquivos ja foram atualizados. Tente conectar manualmente."
    set "RESULT_STATUS=ARQUIVOS ATUALIZADOS - CONEXAO NAO CONFIRMADA"
)

REM ---- 8. Envia log ao CPECONTROL (best-effort) --------------
call :log ""
call :log "[INFO] Enviando log ao servidor..."
if "%RESULT_STATUS%"=="SUCESSO" ( set "SUCC=true" ) else ( set "SUCC=false" )
powershell -NoProfile -Command "$ErrorActionPreference='SilentlyContinue';[Net.ServicePointManager]::SecurityProtocol='Tls12';$form=@{version='%PKG_VERSION%';computer='%COMPUTERNAME%';user_login='%USERDOMAIN%\%USERNAME%';success='%SUCC%';log_file=Get-Item '%LOGFILE%'};Invoke-WebRequest -UseBasicParsing -Uri '%SERVER_BASE%/api/packages/%PKG_SLUG%/log' -Method POST -Form $form -Headers @{'X-Package-Token'='%PKG_TOKEN%'} -TimeoutSec 20 | Out-Null" 2>nul
if %errorlevel% equ 0 (
    call :log "[OK] Log enviado."
) else (
    call :log "[AVISO] Envio de log falhou - sem impacto na atualizacao."
)

:finalizar
call :log ""
call :log "=========================================="
call :log " RESULTADO FINAL: %RESULT_STATUS%"
call :log "=========================================="
call :log " Erros na copia    : %ERR_COUNT%"
if defined BACKUP_DIR call :log " Backup da config  : %BACKUP_DIR%"
call :log " Log do OpenVPN    : %OPENVPN_LOG%"
call :log " Este log          : %LOGFILE%"

echo.
echo ============================================
echo  RESULTADO: %RESULT_STATUS%
echo  Log: %LOGFILE%
echo ============================================
echo.
start "" notepad "%LOGFILE%"
pause
endlocal
exit /b

:log
echo [%TIME%] %~1
echo [%TIME%] %~1 >> "%LOGFILE%"
goto :eof
