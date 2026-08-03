# Запуск TG-бота из папки "ChatGR TG"
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH = $PSScriptRoot

# Свой venv на Python 3.12 (aiogram). НЕ используй корневой venv на 3.15.
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Нет .venv. Создай:"
    Write-Host '  py -3.12 -m venv .venv'
    Write-Host '  .\.venv\Scripts\pip install -r requirements.txt'
    exit 1
}

Write-Host "Python: $(& $py --version)"
Write-Host "Starting ChatGR TG..."
& $py main.py
