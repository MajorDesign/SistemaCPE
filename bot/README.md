# CPE Control Bot (Discord)

Bot Discord com slash commands que consulta e (na Fase 2) abre chamados
via a CPEControlAPI.

## Comandos (Fase 1)

- `/vincular email:seu.email@cpetecnologia.com.br` — inicia o fluxo de vinculação (envia código por email)
- `/vincular-confirmar codigo:XXXXXX` — confirma o código de 6 dígitos e cria o link Discord ↔ CPE
- `/consultachamado numero:SUP-2026-00178` — mostra status + última resposta + botão pra abrir no navegador

Todas as respostas são **ephemeral** (só o usuário que executou vê).

## Setup no CPEDC22

### 1. Instalar dependências
Reusa o venv da CPEControlAPI:

```powershell
& "E:\xampp\htdocs\SistemaCPE\server\.venv\Scripts\pip.exe" install -r "E:\xampp\htdocs\SistemaCPE\bot\requirements.txt"
```

### 2. Criar `.env` do bot

```powershell
Copy-Item "E:\xampp\htdocs\SistemaCPE\bot\.env.example" "E:\xampp\htdocs\SistemaCPE\bot\.env"
```

Editar `.env` (via Notepad ou seu editor preferido):

- `DISCORD_BOT_TOKEN` — obter em https://discord.com/developers/applications → CPE Control → Bot → **Reset Token** (mostra 1 vez, copiar imediatamente)
- `DISCORD_BOT_API_KEY` — copiar o valor de `E:\xampp\htdocs\SistemaCPE\server\.discord-bot-key.txt` (arquivo criado pelo deploy do router backend). Precisa ser **idêntico** ao valor de `DISCORD_BOT_API_KEY` no `server/.env`
- Demais variáveis já vêm preenchidas no `.env.example`

Depois de copiar a `DISCORD_BOT_API_KEY` no `.env` do bot, **deletar** `.discord-bot-key.txt` (o valor real fica só nos dois `.env` que precisam dele).

### 3. Teste manual antes do serviço

```powershell
Set-Location "E:\xampp\htdocs\SistemaCPE\bot"
& "E:\xampp\htdocs\SistemaCPE\server\.venv\Scripts\python.exe" discord_bot.py
```

Deve imprimir:
```
[BOT] N slash commands sincronizados pra guild 1218275609382359050
[BOT] logado como CPE Control#XXXX (id=...)
```

Testar no Discord: digitar `/` no servidor da CPE — deve aparecer `/vincular`, `/vincular-confirmar`, `/consultachamado`.

Se estiver OK, Ctrl+C pra parar.

### 4. Criar serviço Windows via NSSM

```powershell
$py  = "E:\xampp\htdocs\SistemaCPE\server\.venv\Scripts\python.exe"
$app = "E:\xampp\htdocs\SistemaCPE\bot\discord_bot.py"
$dir = "E:\xampp\htdocs\SistemaCPE\bot"

& "C:\NSSM\nssm.exe" install CPEControlBot $py $app
& "C:\NSSM\nssm.exe" set CPEControlBot AppDirectory $dir
& "C:\NSSM\nssm.exe" set CPEControlBot AppStdout   "$dir\logs\bot-stdout.log"
& "C:\NSSM\nssm.exe" set CPEControlBot AppStderr   "$dir\logs\bot-stderr.log"
& "C:\NSSM\nssm.exe" set CPEControlBot AppRotateFiles 1
& "C:\NSSM\nssm.exe" set CPEControlBot AppRotateBytes 10485760   # rotate a cada 10MB
& "C:\NSSM\nssm.exe" set CPEControlBot AppStopMethodConsole 30000
& "C:\NSSM\nssm.exe" set CPEControlBot Description "Bot Discord do CPE Control (slash commands)"

# Auto-restart em crash — mesma politica da CPEControlAPI
& "C:\NSSM\nssm.exe" set CPEControlBot AppExit Default Restart
& "C:\NSSM\nssm.exe" set CPEControlBot AppRestartDelay 5000

# Sobe
& "C:\NSSM\nssm.exe" start CPEControlBot

# Confere status
Get-Service CPEControlBot
```

### 5. Operação

- **Ver logs**: `Get-Content "E:\xampp\htdocs\SistemaCPE\bot\logs\bot-stderr.log" -Tail 30`
- **Reiniciar**: `Restart-Service CPEControlBot`
- **Parar**: `Stop-Service CPEControlBot`
- **Deletar o serviço** (se precisar recriar): `& "C:\NSSM\nssm.exe" remove CPEControlBot confirm`

## Rotacionar token

Se o `DISCORD_BOT_TOKEN` vazar (log público, screenshot, commit acidental):

1. Developer Portal → CPE Control → Bot → **Reset Token**
2. Atualizar `E:\xampp\htdocs\SistemaCPE\bot\.env` com o token novo
3. `Restart-Service CPEControlBot`

Pra rotacionar `DISCORD_BOT_API_KEY` (chave interna, não vaza pelo Discord):

1. Gerar nova: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
2. Atualizar **os dois** `.env`: `server/.env` e `bot/.env`
3. Reiniciar ambos: `Restart-Service CPEControlAPI; Restart-Service CPEControlBot`
