@echo off
setlocal EnableExtensions
REM ============================================================
REM  Atualizar-VPN-CPE.bat v1.0.0 (2026-09-23)
REM  Baixa os arquivos OpenVPN da CPE e coloca em C:\Program Files\OpenVPN\config
REM  Backup automatico da pasta config atual.
REM ============================================================

set "SRC_BASE=https://cpecontrol.cpetecnologia.com.br/SistemaCPE/web/uploads/vpn"
set "OPENVPN_DIR=C:\Program Files\OpenVPN"
set "OPENVPN_CFG=%OPENVPN_DIR%\config"

REM ---- Autoelevacao UAC ---------------------------------------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permissao de administrador...
    powershell -NoProfile -Command "Start-Process -Verb RunAs -FilePath '%~f0'"
    exit /b
)

echo.
echo ============================================================
echo   ATUALIZACAO DE VPN - CPE TECNOLOGIA
echo ============================================================
echo.

REM ---- OpenVPN instalado? ------------------------------------
if not exist "%OPENVPN_DIR%\bin\openvpn-gui.exe" (
    echo [ERRO] OpenVPN nao encontrado em: %OPENVPN_DIR%
    echo        Instale o OpenVPN antes de rodar este script.
    echo.
    pause
    exit /b 1
)

REM ---- Baixar arquivos pra pasta temp -------------------------
set "TMP_DIR=%TEMP%\cpe-vpn-%RANDOM%"
mkdir "%TMP_DIR%" 2>nul

echo Baixando arquivos do CPECONTROL...
echo.
for %%f in ("OpenVPN_CPETecnologia.ovpn" "CA-CPE-NEW.crt" "openvpn-users-cpe-new.crt" "openvpn-users-cpe-new.key") do (
    echo   %%~f
    powershell -NoProfile -Command "$ErrorActionPreference='Stop';[Net.ServicePointManager]::SecurityProtocol='Tls12';Invoke-WebRequest -UseBasicParsing -Uri '%SRC_BASE%/%%~f' -OutFile '%TMP_DIR%\%%~f'" 2>nul
    if not exist "%TMP_DIR%\%%~f" (
        echo.
        echo [ERRO] Falha ao baixar %%~f
        echo        Verifique sua conexao com a internet e tente novamente.
        echo.
        rd /S /Q "%TMP_DIR%" >nul 2>&1
        pause
        exit /b 1
    )
)
echo.
echo [OK] Arquivos baixados.
echo.

REM ---- Fecha OpenVPN se estiver aberto ------------------------
echo Fechando OpenVPN se estiver aberto...
taskkill /F /IM openvpn-gui.exe >nul 2>&1
taskkill /F /IM openvpn.exe >nul 2>&1
sc stop OpenVPNServiceInteractive >nul 2>&1
timeout /t 2 /nobreak >nul

REM ---- Backup da config atual ---------------------------------
set "TS=%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%-%TIME:~0,2%%TIME:~3,2%"
set "TS=%TS: =0%"
set "BACKUP_DIR=%OPENVPN_DIR%\config-backup-%TS%"

if exist "%OPENVPN_CFG%" (
    echo Backup em: %BACKUP_DIR%
    xcopy "%OPENVPN_CFG%" "%BACKUP_DIR%" /E /I /Y /Q >nul 2>&1
) else (
    mkdir "%OPENVPN_CFG%" 2>nul
)

REM ---- Limpa config antiga ------------------------------------
attrib -r -h -s "%OPENVPN_CFG%\*" /S /D >nul 2>&1
del /F /Q "%OPENVPN_CFG%\*.*" >nul 2>&1
for /d %%d in ("%OPENVPN_CFG%\*") do rd /S /Q "%%d" >nul 2>&1

REM ---- Copia arquivos novos -----------------------------------
copy /Y "%TMP_DIR%\*" "%OPENVPN_CFG%\" >nul
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao copiar os arquivos para %OPENVPN_CFG%
    echo        Backup: %BACKUP_DIR%
    echo.
    rd /S /Q "%TMP_DIR%" >nul 2>&1
    pause
    exit /b 1
)

rd /S /Q "%TMP_DIR%" >nul 2>&1

echo.
echo ============================================================
echo   PRONTO! Arquivos atualizados.
echo ============================================================
echo.
echo   Backup da config anterior:
echo   %BACKUP_DIR%
echo.
echo   Agora abra o OpenVPN (icone na bandeja do Windows,
echo   ao lado do relogio) e conecte manualmente.
echo.
echo ============================================================
echo.
pause
endlocal
exit /b 0
