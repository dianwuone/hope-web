$existing = Get-NetTCPConnection -LocalPort 4100 -State Listen -ErrorAction SilentlyContinue

if (-not $existing) {
  Write-Host "端口 4100 当前没有后台进程。" -ForegroundColor Yellow
  exit 0
}

$existing | ForEach-Object {
  Write-Host "停止进程 PID=$($_.OwningProcess)" -ForegroundColor Cyan
  Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}

Write-Host "后台已停止。" -ForegroundColor Green
