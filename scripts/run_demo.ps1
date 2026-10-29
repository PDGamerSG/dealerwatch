<#
.SYNOPSIS
  Start the DealerWatch investigator UI on synthetic data.
.DESCRIPTION
  Generates data/generated (seed 7) if missing, optionally renders call audio with Windows SAPI,
  starts the FastAPI app (the server runs the pipeline on startup when the case store is empty)
  and opens the browser. Ctrl+C stops the server.
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts/run_demo.ps1 -Regenerate -Audio
#>
param(
    [int]$Port = 8077,
    [switch]$Regenerate,   # regenerate data/generated even if it exists
    [switch]$Audio,        # render calls/*.json to audio/*.wav via scripts/make_audio.ps1
    [switch]$Fresh,        # delete runtime/ so cases and the ledger are rebuilt from scratch
    [switch]$NoBrowser
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root ".venv/Scripts/python.exe"
if (-not (Test-Path $py)) { throw "Python venv not found at $py" }
if (-not $env:DW_LLM) { $env:DW_LLM = "mock" }
if (-not $env:DW_DEMO) { $env:DW_DEMO = "1" }

if ($Regenerate -or -not (Test-Path "data/generated/orders.json")) {
    Write-Host "Generating synthetic universe (seed 7) ..."
    & $py -m dealerwatch.data.synth --seed 7 --out data/generated
    if ($LASTEXITCODE -ne 0) { throw "data generation failed" }
    $Fresh = $true
}
if ($Audio) {
    if (Test-Path "scripts/make_audio.ps1") {
        & powershell -NoProfile -ExecutionPolicy Bypass -File scripts/make_audio.ps1
    } else {
        Write-Warning "scripts/make_audio.ps1 not found; continuing without audio"
    }
}
if ($Fresh -and (Test-Path "runtime")) { Remove-Item -Recurse -Force "runtime" }

$url = "http://127.0.0.1:$Port"
Write-Host "Starting DealerWatch at $url (LLM=$($env:DW_LLM)) ..."
$server = Start-Process -FilePath $py -NoNewWindow -PassThru `
    -ArgumentList "-m", "uvicorn", "dealerwatch.api:app", "--host", "127.0.0.1", "--port", "$Port"
try {
    $ready = $false
    for ($i = 0; $i -lt 120 -and -not $server.HasExited; $i++) {
        try { Invoke-RestMethod "$url/api/health" -TimeoutSec 2 | Out-Null; $ready = $true; break }
        catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw "server did not become ready" }
    $health = Invoke-RestMethod "$url/api/health"
    Write-Host "Ready: $($health.cases) cases, LLM $($health.llm), ASR $($health.asr). Ctrl+C to stop."
    if (-not $NoBrowser) { Start-Process $url }
    Wait-Process -Id $server.Id
}
finally {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force }
}
