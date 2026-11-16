<#
.SYNOPSIS
    Полная сборка Windows-приложений SamboTL (сервер + клиент).

.DESCRIPTION
    1. Собирает Vue SPA (npm run build)
    2. Собирает статику Django (collectstatic)
    3. Собирает оба .exe через PyInstaller
    Результат: dist\SamboTLServer.exe, dist\SamboTLClient.exe
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "== 1/3 Frontend build (Vue SPA) =="
Push-Location frontend
npm install --no-audit --no-fund
npm run build
Pop-Location

Write-Host "== 2/3 collectstatic =="
& ".\.venv\Scripts\python.exe" manage.py collectstatic --noinput

Write-Host "== 3/3 PyInstaller =="
& ".\.venv\Scripts\python.exe" -m PyInstaller "launcher\server.spec" --noconfirm --distpath dist --workpath build
& ".\.venv\Scripts\python.exe" -m PyInstaller "launcher\client.spec" --noconfirm --distpath dist --workpath build

Write-Host "Done:"
Get-ChildItem dist -Filter "SamboTL*.exe" |
    Select-Object Name, @{N = "MB"; E = { [math]::Round($_.Length / 1MB, 1) } } |
    Format-Table -AutoSize

Write-Host "Creating desktop shortcuts..."
& "$PSScriptRoot\create_shortcuts.ps1"

Write-Host "== 4/4 Inno Setup installer (optional) =="
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if ($iscc) {
    & $iscc.Source "$PSScriptRoot\client_installer.iss"
} else {
    Write-Host "Inno Setup (iscc.exe) not found — skipping the installer."
    Write-Host "Install it from https://jrsoftware.org/isinfo.php, then re-run this script."
}
