# Запуск TG-бота из папки "ChatGR TG"
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH = $PSScriptRoot

$py = $null
if (Test-Path "..\venv\Scripts\python.exe") {
    $py = "..\venv\Scripts\python.exe"
} else {
    $py = "python"
}

Write-Host "PYTHONPATH=$env:PYTHONPATH"
Write-Host "Starting ChatGR TG..."
& $py main.py
