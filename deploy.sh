#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRANCH="${BRANCH:-main}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RESTART_CMD="${RESTART_CMD:-}"
BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

fail() {
  echo "❌ $1" >&2
  exit 1
}

restart_backend() {
  if [[ -n "$RESTART_CMD" ]]; then
    log "执行自定义重启命令"
    bash -lc "$RESTART_CMD"
    return
  fi

  if [[ -n "$BACKEND_SERVICE_NAME" ]]; then
    if command -v systemctl >/dev/null 2>&1; then
      log "重启 systemd 服务: $BACKEND_SERVICE_NAME"
      systemctl restart "$BACKEND_SERVICE_NAME"
      return
    fi

    if command -v supervisorctl >/dev/null 2>&1; then
      log "重启 supervisor 服务: $BACKEND_SERVICE_NAME"
      supervisorctl restart "$BACKEND_SERVICE_NAME"
      return
    fi
  fi

  log "未配置重启命令，跳过自动重启"
}

log "开始后端自动部署"

cd "$APP_DIR"

log "拉取最新代码: origin/$BRANCH"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
git clean -fd

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail "未找到 Python 命令: $PYTHON_BIN"
fi

if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  log "创建虚拟环境"
  "$PYTHON_BIN" -m venv "$APP_DIR/.venv"
fi

log "安装 Python 依赖"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

if [[ -f "$APP_DIR/admin/package.json" ]]; then
  log "构建管理前端"
  if command -v corepack >/dev/null 2>&1; then
    corepack enable
    corepack prepare pnpm@latest --activate
  fi
  if ! command -v pnpm >/dev/null 2>&1; then
    fail "未找到 pnpm，请先安装 Node.js / Corepack"
  fi
  cd "$APP_DIR/admin"
  pnpm install --frozen-lockfile
  pnpm build
  cd "$APP_DIR"
fi

restart_backend

log "后端部署完成"
