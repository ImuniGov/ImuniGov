$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.env')) {
    $randomBytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($randomBytes)
    $databasePassword = [Convert]::ToHexString($randomBytes).ToLowerInvariant()
    "POSTGRES_PASSWORD=$databasePassword`nPUBLIC_ORIGIN=http://localhost:4173`nCOOKIE_SECURE=false" | Set-Content -LiteralPath '.env' -Encoding utf8
    Write-Host 'Configuração local criada com senha aleatória do banco.'
}
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível iniciar o aplicativo. Consulte docker compose logs.' }
Write-Host 'ImuniGuia: http://localhost:4173'
