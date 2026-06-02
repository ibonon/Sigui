param(
    [switch]$NoUi
)

$ErrorActionPreference = "Stop"

Write-Host "Starting Sigui backend..." -ForegroundColor Cyan
Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..'; .\venv\Scripts\python -m uvicorn main:app --reload --port 8000"

if (-not $NoUi) {
    Write-Host "Starting premium demo UI..." -ForegroundColor Cyan
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\demo-ui'; npm run dev"
}

Write-Host ""
Write-Host "Sigui startup commands launched." -ForegroundColor Green
Write-Host "API:  http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "Docs: http://127.0.0.1:8000/docs" -ForegroundColor Yellow
if (-not $NoUi) {
    Write-Host "UI:   http://localhost:3001" -ForegroundColor Yellow
}

