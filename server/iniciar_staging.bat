@echo off
title CPE Control API — STAGING (porta 8001)
cd /d %~dp0

echo.
echo ============================================================
echo   CPE Control API — Ambiente STAGING
echo   Banco   : cpe_plus_staging (dados de producao copiados)
echo   Porta   : 8001
echo   Dev API : http://127.0.0.1:8001
echo ============================================================
echo.
echo   Para sincronizar dados de producao antes de iniciar:
echo     server/.venv/Scripts/python.exe tools/sync_staging.py
echo.

set MYSQL_DB=cpe_plus_staging
set DATABASE_URL=mysql+pymysql://root:Cpe%%407482@127.0.0.1:3306/cpe_plus_staging?charset=utf8mb4
set CORS_ORIGINS=http://localhost,http://127.0.0.1,http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8001,http://127.0.0.1:8001

.venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8001 --app-dir . --env-file .env.staging

pause
