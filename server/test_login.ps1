param(
    [string]$Email = "admin@cpe.com.br",
    [string]$Password = "Cpe@7482",
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== TESTE DE LOGIN SistemaCPE ===" -ForegroundColor Cyan
Write-Host "Email: $Email"
Write-Host "URL: $BaseUrl"
Write-Host ""

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

# LOGIN
Write-Host "-> Enviando login..." -ForegroundColor Yellow

$loginBody = @{
  email = $Email
  password = $Password
} | ConvertTo-Json

try {
  $loginResponse = Invoke-WebRequest `
    -Uri "$BaseUrl/api/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $loginBody `
    -WebSession $session `
    -UseBasicParsing

  Write-Host "Login HTTP Status:" $loginResponse.StatusCode -ForegroundColor Green
} catch {
  Write-Host "ERRO NO LOGIN:" -ForegroundColor Red
  Write-Host $_.Exception.Message
  exit 1
}

# /ME
Write-Host ""
Write-Host "-> Verificando sessão (/me)..." -ForegroundColor Yellow

try {
  $me = Invoke-RestMethod `
    -Uri "$BaseUrl/api/auth/me" `
    -Method GET `
    -WebSession $session

  Write-Host ""
  Write-Host "=== USUÁRIO AUTENTICADO ===" -ForegroundColor Cyan
  Write-Host "ID:" $me.id
  Write-Host "Nome:" $me.name
  Write-Host "Email:" $me.email
  Write-Host "Role:" $me.role
  Write-Host "Setor:" $me.sector
  Write-Host "Unidade:" $me.unit

  Write-Host ""
  Write-Host "=== TESTE FINALIZADO COM SUCESSO ===" -ForegroundColor Green
} catch {
  Write-Host "ERRO AO VALIDAR /ME:" -ForegroundColor Red
  Write-Host $_.Exception.Message
  exit 1
}
