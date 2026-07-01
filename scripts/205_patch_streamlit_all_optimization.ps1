$ErrorActionPreference = "Stop"

Write-Host "[INFO] Aplicando pagina Streamlit de Otimizacao Aria consolidada" -ForegroundColor Cyan

$appDir = Join-Path (Get-Location) "app"
$pagesDir = Join-Path $appDir "pages"
New-Item -ItemType Directory -Path $appDir -Force | Out-Null
New-Item -ItemType Directory -Path $pagesDir -Force | Out-Null

$module = Join-Path $appDir "rmc_optimization_all_view.py"
$page = Join-Path $pagesDir "91_Otimizacao_Aria.py"

if (-not (Test-Path $module)) { throw "Modulo ausente: $module" }
if (-not (Test-Path $page)) { throw "Pagina ausente: $page" }

Write-Host "[OK] Modulo: $module" -ForegroundColor Green
Write-Host "[OK] Pagina: $page" -ForegroundColor Green
Write-Host "[INFO] Reinicie o dashboard." -ForegroundColor Yellow
Write-Host "[INFO] Se o dashboard usa menu customizado e app/pages esta desativado, importe render_all_optimization_panel()." -ForegroundColor Yellow
