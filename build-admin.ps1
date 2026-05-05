$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$admin = Join-Path $root "admin"

if (-not (Test-Path $admin)) {
  Write-Error "未找到后台前端目录：$admin"
}

Set-Location $admin
Write-Host "正在构建 pure-admin 后台前端..." -ForegroundColor Cyan
corepack pnpm build
