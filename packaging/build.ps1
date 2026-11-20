$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "==> Testes" -ForegroundColor Cyan
python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Testes falharam. Build cancelado." }

Write-Host "==> Limpando" -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Host "==> PyInstaller" -ForegroundColor Cyan
python -m PyInstaller packaging\extrator_boletos.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou." }

Write-Host "==> Inno Setup" -ForegroundColor Cyan
$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "ISCC.exe não encontrado. Instale o Inno Setup 6." }

& $iscc packaging\setup.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falhou." }

Write-Host "==> Pronto: dist\instalador\" -ForegroundColor Green
