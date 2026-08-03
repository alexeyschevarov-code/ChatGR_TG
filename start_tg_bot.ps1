# Запуск Telegram-бота из корня MyPythonProjects
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$tg = Join-Path $root "ChatGR TG"

if (-not (Test-Path $tg)) {
    Write-Host "Не найдена папка: $tg"
    exit 1
}

Set-Location $tg
$env:PYTHONPATH = $tg

$py = Join-Path $tg ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    $py = Join-Path $root "venv\Scripts\python.exe"
}
if (-not (Test-Path $py)) {
    $py = "python"
}

Write-Host "Папка: $tg"
Write-Host "Python: $py"
& $py --version
Write-Host "Запуск main.py ..."
& $py main.py
