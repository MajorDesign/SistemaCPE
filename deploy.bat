@echo off
chcp 65001 >nul
title Deploy - SistemaCPE

echo.
echo =============================================
echo  Deploy SistemaCPE - %date% %time%
echo =============================================
echo.

:: Localiza o bash do Git for Windows
set BASH="C:\Program Files\Git\bin\bash.exe"
if not exist %BASH% set BASH="C:\Program Files (x86)\Git\bin\bash.exe"

:: Roda o script de deploy
%BASH% /e/xampp/htdocs/SistemaCPE/deploy.sh

echo.
echo =============================================
echo  Deploy concluido! Pressione qualquer tecla.
echo =============================================
pause >nul
