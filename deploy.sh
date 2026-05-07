#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-/www/wwwroot/kuntin}"
BRANCH="${BRANCH:-main}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RESTART_CMD="${RESTART_CMD:-}"
BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-}"
REPO_URL="${REPO_URL:-}"
DEPLOY_PYTHON=""
PNPM_RUNNER="pnpm"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

fail() {
  echo "❌ $1" >&2
  exit 1
}

ensure_git_safe_directory() {
  if ! git config --global --get-all safe.directory | grep -Fxq "$APP_DIR"; then
    log "登记 Git 安全目录: $APP_DIR"
    git config --global --add safe.directory "$APP_DIR"
  fi
}

ensure_git_remote() {
  if git -C "$APP_DIR" remote get-url origin >/dev/null 2>&1; then
    if [[ -n "$REPO_URL" ]]; then
      current_url="$(git -C "$APP_DIR" remote get-url origin)"
      if [[ "$current_url" != "$REPO_URL" ]]; then
        log "更新 origin 地址: $current_url -> $REPO_URL"
        git -C "$APP_DIR" remote set-url origin "$REPO_URL"
      fi
    fi
  else
    if [[ -z "$REPO_URL" ]]; then
      fail "未配置 origin 远程地址，请设置 REPO_URL"
    fi
    log "添加 origin 远程: $REPO_URL"
    git -C "$APP_DIR" remote add origin "$REPO_URL"
  fi
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

resolve_python_runtime() {
  if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
    DEPLOY_PYTHON="$APP_DIR/.venv/bin/python"
    return
  fi

  log "创建虚拟环境"
  if "$PYTHON_BIN" -m venv "$APP_DIR/.venv"; then
    if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
      DEPLOY_PYTHON="$APP_DIR/.venv/bin/python"
      return
    fi
  fi

  log "虚拟环境创建失败，改用系统 Python"
  DEPLOY_PYTHON="$PYTHON_BIN"
}

resolve_pnpm_runner() {
  if command -v pnpm >/dev/null 2>&1; then
    PNPM_RUNNER="pnpm"
    return
  fi

  if command -v corepack >/dev/null 2>&1; then
    log "启用 Corepack pnpm"
    corepack enable >/dev/null 2>&1 || true
    PNPM_RUNNER="corepack pnpm"
    return
  fi

  fail "未找到 pnpm 或 corepack，请先安装 pnpm"
}

ensure_pip_available() {
  if "$DEPLOY_PYTHON" -m pip --version >/dev/null 2>&1; then
    return
  fi

  log "当前 Python 环境没有 pip，尝试通过 ensurepip 修复"
  if "$DEPLOY_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1; then
    if "$DEPLOY_PYTHON" -m pip --version >/dev/null 2>&1; then
      return
    fi
  fi

  fail "当前 Python 环境没有 pip，请安装 python3-pip，或删除 .venv 后重新执行"
}

log "开始后端自动部署"

if [[ ! -d "$APP_DIR/.git" ]]; then
  if [[ -z "$REPO_URL" ]]; then
    fail "未找到 Git 仓库目录: $APP_DIR，请先执行 git init 并设置远程仓库"
  fi
  log "初始化部署仓库: $APP_DIR"
  mkdir -p "$APP_DIR"
  git -C "$APP_DIR" init
fi

ensure_git_safe_directory
ensure_git_remote

cd "$APP_DIR"

log "拉取最新代码: origin/$BRANCH"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
git clean -fd

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail "未找到 Python 命令: $PYTHON_BIN"
fi

resolve_python_runtime

ensure_pip_available

log "安装 Python 依赖"
"$DEPLOY_PYTHON" -m pip install --upgrade pip
"$DEPLOY_PYTHON" -m pip install -r "$APP_DIR/requirements.txt"

if [[ -f "$APP_DIR/admin/package.json" ]]; then
  log "构建管理前端"
  resolve_pnpm_runner
  cd "$APP_DIR/admin"
  CI=true $PNPM_RUNNER install --frozen-lockfile --config.confirmModulesPurge=false
  CI=true $PNPM_RUNNER build
  cd "$APP_DIR"
fi

restart_backend

log "后端部署完成"
