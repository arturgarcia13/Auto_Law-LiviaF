<#
.SYNOPSIS
    Inicializa o servidor Uvicorn (FastAPI) e o tunel Ngrok para integracao com Kommo CRM.
.DESCRIPTION
    Inicia a aplicacao localmente na porta 8000, cria um tunel publico seguro via Ngrok
    e exibe os endpoints exatos formatados com o token de seguranca para configuracao na Kommo.
.EXAMPLE
    .\start_tunnel.ps1
    .\start_tunnel.ps1 -Port 8000 -Domain "liviafranaadv.ngrok-free.app"
#>

[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$Domain = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Garante que a execucao ocorra no diretorio do projeto
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Auto_Law - Dra. Livia Franca | Inicializador Uvicorn e Ngrok" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Carregar variaveis do .env
$EnvFile = Join-Path $ProjectRoot ".env"
$WebhookSecret = "teste123"
$EnvDomain = ""
$EnvAuthtoken = ""

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $k = $parts[0].Trim()
            $v = $parts[1].Trim()
            if ($k -eq "KOMMO_WEBHOOK_SECRET" -and $v) {
                $WebhookSecret = $v
            }
            if ($k -eq "NGROK_DOMAIN" -and $v) {
                $EnvDomain = $v
            }
            if ($k -eq "NGROK_AUTHTOKEN" -and $v) {
                $EnvAuthtoken = $v
            }
        }
    }
}

if (-not $Domain -and $EnvDomain) {
    $Domain = $EnvDomain
}

# 2. Localizar executavel do Python / Uvicorn no .venv
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonExe = $PythonCmd.Source
    }
}

if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    Write-Host "[ERRO] Python nao encontrado no .venv ou PATH." -ForegroundColor Red
    exit 1
}

# 3. Localizar Ngrok
$NgrokCmd = (Get-Command ngrok -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $NgrokCmd) {
    Write-Host "[ERRO] Ngrok nao encontrado no PATH." -ForegroundColor Red
    Write-Host "Instale via 'winget install ngrok' ou adicione ao PATH." -ForegroundColor Gray
    exit 1
}

# Configura authtoken se fornecido no .env
if ($EnvAuthtoken) {
    if ($EnvAuthtoken -match "([a-zA-Z0-9_-]{30,})") {
        $EnvAuthtoken = $matches[1]
    }
    Write-Host "[AUTH] Atualizando/validando authtoken do Ngrok..." -ForegroundColor Cyan
    & $NgrokCmd config add-authtoken $EnvAuthtoken | Out-Null
}

# Finaliza instâncias anteriores do Ngrok para evitar conflito ERR_NGROK_334
$OldNgrok = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue
if ($OldNgrok) {
    Write-Host "[INFO] Encerrando instancias anteriores do Ngrok..." -ForegroundColor Gray
    $OldNgrok | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 600
}

# Configura saida unbuffered para transmissao imediata de logs
$env:PYTHONUNBUFFERED = "1"

# Finaliza qualquer processo anterior escutando na porta $Port para evitar conflito WinError 10048
Write-Host "[PORT] Verificando conexoes ativas na porta $Port..." -ForegroundColor Gray
try {
    $PortConnections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($PortConnections) {
        $PortPids = $PortConnections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pidToKill in $PortPids) {
            if ($pidToKill -and $pidToKill -ne $PID) {
                Write-Host "[INFO] Encerrando processo na porta $Port (PID $pidToKill)..." -ForegroundColor Yellow
                Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Milliseconds 600
    }
} catch {
    # Ignora caso comando falhe
}

# Finaliza processos Python zumbis órfãos associados ao Uvicorn deste projeto
try {
    $OrphanPythons = Get-CimInstance Win32_Process -Filter "Name LIKE '%python%'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*uvicorn*" -and $_.CommandLine -like "*app.main:app*" -and $_.ProcessId -ne $PID }
    if ($OrphanPythons) {
        foreach ($proc in $OrphanPythons) {
            Write-Host "[INFO] Encerrando processo zumbi do Uvicorn (PID $($proc.ProcessId))..." -ForegroundColor Yellow
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 500
    }
} catch {
    # Ignora caso CIM não esteja disponível
}

Write-Host ""
Write-Host "[1/3] Iniciando servidor FastAPI (Uvicorn) na porta $Port..." -ForegroundColor Yellow
$UvicornArgs = @(
    "-m", "uvicorn", "app.main:app",
    "--host", "0.0.0.0",
    "--port", "$Port",
    "--reload",
    "--reload-dir", "app",
    "--reload-dir", "agent",
    "--reload-dir", "integrations",
    "--reload-dir", "scheduler"
)
$UvicornProcess = Start-Process -FilePath $PythonExe `
    -ArgumentList $UvicornArgs `
    -PassThru -NoNewWindow

Start-Sleep -Seconds 2

# 4. Iniciar Ngrok Tunnel
Write-Host "[2/3] Estabelecendo tunel Ngrok..." -ForegroundColor Yellow
$NgrokOut = Join-Path $ProjectRoot ".ngrok_out.log"
$NgrokErr = Join-Path $ProjectRoot ".ngrok_err.log"
Remove-Item $NgrokOut, $NgrokErr -Force -ErrorAction SilentlyContinue

$NgrokArgs = @("http", "$Port")
if ($Domain) {
    Write-Host "      Tentando conectar com dominio: $Domain" -ForegroundColor Cyan
    $NgrokArgs += @("--url", "$Domain")
}

$NgrokProcess = Start-Process -FilePath $NgrokCmd `
    -ArgumentList $NgrokArgs `
    -PassThru `
    -RedirectStandardOutput $NgrokOut `
    -RedirectStandardError $NgrokErr

Start-Sleep -Milliseconds 1500

# Se o Ngrok falhar ao tentar subdominio pago/invalido (ERR_NGROK_313), faz fallback automatico para dev domain gratuito
if ($NgrokProcess.HasExited) {
    $errContent = ""
    if (Test-Path $NgrokErr) {
        $errContent += Get-Content $NgrokErr -Raw -ErrorAction SilentlyContinue
    }
    if (Test-Path $NgrokOut) {
        $errContent += Get-Content $NgrokOut -Raw -ErrorAction SilentlyContinue
    }

    if ($errContent -match "ERR_NGROK_313" -or $errContent -match "custom subdomains") {
        Write-Host "      [AVISO] O dominio customizado '$Domain' requer plano pago (ERR_NGROK_313)." -ForegroundColor DarkYellow
        Write-Host "      [INFO] Conectando com o dominio estatico permanente gratuito atribuido a sua conta..." -ForegroundColor Cyan
        
        $NgrokOutFallback = Join-Path $ProjectRoot ".ngrok_fallback_out.log"
        $NgrokErrFallback = Join-Path $ProjectRoot ".ngrok_fallback_err.log"
        $NgrokArgsFallback = @("http", "$Port")
        $NgrokProcess = Start-Process -FilePath $NgrokCmd `
            -ArgumentList $NgrokArgsFallback `
            -PassThru `
            -RedirectStandardOutput $NgrokOutFallback `
            -RedirectStandardError $NgrokErrFallback
    } else {
        Write-Host "[ERRO] Ngrok falhou ao iniciar:" -ForegroundColor Red
        if ($errContent) {
            Write-Host $errContent -ForegroundColor Yellow
        }
    }
}

# 5. Capturar a URL publica do tunel consultando a API local do Ngrok (http://127.0.0.1:4040/api/tunnels)
$TunnelUrl = $null
$TimeoutSeconds = 20
$Elapsed = 0

while (-not $TunnelUrl -and $Elapsed -lt $TimeoutSeconds) {
    Start-Sleep -Milliseconds 800
    $Elapsed += 1
    try {
        $apiResp = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($apiResp -and $apiResp.tunnels) {
            $httpsTunnel = $apiResp.tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1
            if ($httpsTunnel -and $httpsTunnel.public_url) {
                $TunnelUrl = $httpsTunnel.public_url.TrimEnd("/")
            } elseif ($apiResp.tunnels[0].public_url) {
                $TunnelUrl = $apiResp.tunnels[0].public_url.TrimEnd("/")
            }
        }
    } catch {
        # Aguarda API local inicializar
    }
}

if (-not $TunnelUrl) {
    Write-Host "[AVISO] Nao foi possivel detectar a URL do Ngrok automaticamente." -ForegroundColor Red
    Write-Host "Verifique a interface do Ngrok em http://127.0.0.1:4040 ou os logs .ngrok_err.log" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "[3/3] Tunel Ngrok ativo com sucesso!" -ForegroundColor Green
    Write-Host "----------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "URL Base do Tunel: $TunnelUrl" -ForegroundColor Cyan
    Write-Host "Token de Webhook:  $WebhookSecret" -ForegroundColor Cyan
    Write-Host "----------------------------------------------------------------------" -ForegroundColor DarkGray

    Write-Host ""
    Write-Host "COPIE E COLE NA KOMMO (Configuracoes de Webhook / Integracoes):" -ForegroundColor Green
    Write-Host "-> URL do Webhook da Kommo (Principal):" -ForegroundColor Yellow
    Write-Host "   $TunnelUrl/kommo/webhook?token=$WebhookSecret" -ForegroundColor White

    Write-Host ""
    Write-Host "-> URL do Webhook da Kommo (Alias alternativo):" -ForegroundColor Yellow
    Write-Host "   $TunnelUrl/webhook/kommo?token=$WebhookSecret" -ForegroundColor White

    Write-Host ""
    Write-Host "-> URL para o Salesbot da Kommo (se configurado):" -ForegroundColor Yellow
    Write-Host "   $TunnelUrl/webhook/salesbot?token=$WebhookSecret" -ForegroundColor White

    Write-Host ""
    Write-Host "-> URL para Teste de Status no Navegador:" -ForegroundColor Yellow
    Write-Host "   $TunnelUrl/" -ForegroundColor White
    Write-Host "   $TunnelUrl/health" -ForegroundColor White

    Write-Host ""
    Write-Host "-> Endpoint para Disparos Manuais ou Templates (/send):" -ForegroundColor Yellow
    Write-Host "   $TunnelUrl/send?token=$WebhookSecret" -ForegroundColor White
    Write-Host "----------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "Painel Web de Inspecao do Ngrok: http://127.0.0.1:4040" -ForegroundColor Cyan
    Write-Host "Pressione [Ctrl + C] para encerrar o Uvicorn e o Ngrok." -ForegroundColor Magenta
}

# 6. Manter em execucao e gerenciar encerramento limpo
try {
    while (-not $UvicornProcess.HasExited -and -not $NgrokProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "Encerrando Uvicorn e Ngrok..." -ForegroundColor Yellow
    if ($UvicornProcess -and -not $UvicornProcess.HasExited) {
        Stop-Process -Id $UvicornProcess.Id -Force -ErrorAction SilentlyContinue
    }
    if ($NgrokProcess -and -not $NgrokProcess.HasExited) {
        Stop-Process -Id $NgrokProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $NgrokOut, $NgrokErr, (Join-Path $ProjectRoot ".ngrok_fallback*.log") -Force -ErrorAction SilentlyContinue
    Write-Host "Servicos finalizados com sucesso!" -ForegroundColor Green
}
