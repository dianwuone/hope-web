$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
  Write-Error "未找到虚拟环境 Python：$python"
}

$existing = Get-NetTCPConnection -LocalPort 4100 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
  Write-Host "端口 4100 已被占用，正在停止旧进程..." -ForegroundColor Yellow
  $existing | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
  }
  Start-Sleep -Seconds 1
}

Write-Host "正在启动 Quentin Window Backend..." -ForegroundColor Cyan
Write-Host "地址: http://127.0.0.1:4100/admin" -ForegroundColor Green
Write-Host "文档: http://127.0.0.1:4100/docs" -ForegroundColor Green

& $python -m uvicorn app.main:app --host 127.0.0.1 --port 4100 --app-dir $root
