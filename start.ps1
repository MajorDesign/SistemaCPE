Write-Host "============================================" -ForegroundColor Cyan
Write-Host " CPE Control API - Reiniciando servidor..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Parar processos Python anteriores
Write-Host "`n[1/2] Encerrando processos Python anteriores..." -ForegroundColor Yellow
taskkill /F /IM python.exe /T 2>$null
Start-Sleep -Seconds 2
Write-Host "      OK" -ForegroundColor Green

# Iniciar servidor
Write-Host "[2/2] Iniciando servidor FastAPI..." -ForegroundColor Yellow
Write-Host "`n      Acesse: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "      Para parar: Ctrl+C`n" -ForegroundColor Gray

Set-Location "$PSScriptRoot\server"
.\.venv\Scripts\python.exe app.py
