#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="${APP_DIR:-/www/wwwroot/kuntin}"
BRANCH="${BRANCH:-main}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RESTART_CMD="${RESTART_CMD:-}"
BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-}"
REPO_URL="${REPO_URL:-}"
DEPLOY_STATE_DIR="${DEPLOY_STATE_DIR:-$APP_DIR/.deploy-state}"
DEPLOY_PYTHON=""
PNPM_RUNNER="pnpm"
PYTHON_DEP_HASH_FILE="$DEPLOY_STATE_DIR/requirements.sha256"
ADMIN_DEP_HASH_FILE="$DEPLOY_STATE_DIR/admin-deps.sha256"
PNPM_FETCH_TIMEOUT="${PNPM_FETCH_TIMEOUT:-600000}"
PNPM_FETCH_RETRIES="${PNPM_FETCH_RETRIES:-10}"
PNPM_NETWORK_CONCURRENCY="${PNPM_NETWORK_CONCURRENCY:-1}"
PNPM_REGISTRY="${PNPM_REGISTRY:-https://registry.npmmirror.com}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

fail() {
  echo "❌ $1" >&2
  exit 1
}

prepare_deploy_environment() {
  mkdir -p "$DEPLOY_STATE_DIR"

  if [[ -z "${HOME:-}" ]]; then
    export HOME="$DEPLOY_STATE_DIR/home"
    mkdir -p "$HOME"
    log "当前环境未设置 HOME，临时使用: $HOME"
  fi

  if [[ ! -f "$PYTHON_DEP_HASH_FILE" && -f "$APP_DIR/.venv/.deploy-requirements.sha256" ]]; then
    cp "$APP_DIR/.venv/.deploy-requirements.sha256" "$PYTHON_DEP_HASH_FILE"
  fi

  if [[ ! -f "$ADMIN_DEP_HASH_FILE" && -f "$APP_DIR/admin/.deploy-deps.sha256" ]]; then
    cp "$APP_DIR/admin/.deploy-deps.sha256" "$ADMIN_DEP_HASH_FILE"
  fi
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

calc_python_dep_hash() {
  if [[ -f "$APP_DIR/requirements.txt" ]]; then
    sha256sum "$APP_DIR/requirements.txt" | awk '{print $1}'
    return
  fi
  echo ""
}

calc_admin_dep_hash() {
  if [[ -f "$APP_DIR/admin/package.json" && -f "$APP_DIR/admin/pnpm-lock.yaml" ]]; then
    sha256sum "$APP_DIR/admin/package.json" "$APP_DIR/admin/pnpm-lock.yaml" | sha256sum | awk '{print $1}'
    return
  fi
  echo ""
}

ensure_python_deps() {
  local current_python_dep_hash cached_python_dep_hash
  current_python_dep_hash="$(calc_python_dep_hash)"
  cached_python_dep_hash=""
  if [[ -f "$PYTHON_DEP_HASH_FILE" ]]; then
    cached_python_dep_hash="$(tr -d '\r\n' < "$PYTHON_DEP_HASH_FILE")"
  fi

  if [[ -x "$APP_DIR/.venv/bin/python" && "$current_python_dep_hash" == "$cached_python_dep_hash" ]]; then
    log "后端依赖未变化，跳过 pip install"
    DEPLOY_PYTHON="$APP_DIR/.venv/bin/python"
    return
  fi

  resolve_python_runtime
  ensure_pip_available

  log "安装 Python 依赖"
  "$DEPLOY_PYTHON" -m pip install --upgrade pip
  "$DEPLOY_PYTHON" -m pip install -r "$APP_DIR/requirements.txt"

  if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
    printf '%s\n' "$current_python_dep_hash" > "$PYTHON_DEP_HASH_FILE"
  fi
}

log "开始后端自动部署"
prepare_deploy_environment

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

ensure_python_deps

if [[ -f "$APP_DIR/admin/package.json" ]]; then
  log "构建管理前端"
  resolve_pnpm_runner
  cd "$APP_DIR/admin"
  current_admin_dep_hash="$(calc_admin_dep_hash)"
  cached_admin_dep_hash=""
  if [[ -f "$ADMIN_DEP_HASH_FILE" ]]; then
    cached_admin_dep_hash="$(tr -d '\r\n' < "$ADMIN_DEP_HASH_FILE")"
  fi

  if [[ ! -d "$APP_DIR/admin/node_modules" || "$current_admin_dep_hash" != "$cached_admin_dep_hash" ]]; then
    log "安装管理前端依赖"
    HUSKY=0 CI=true $PNPM_RUNNER install \
      --frozen-lockfile \
      --config.confirmModulesPurge=false \
      --config.enable-pre-post-scripts=false \
      --config.strict-dep-builds=false \
      --fetch-timeout "$PNPM_FETCH_TIMEOUT" \
      --fetch-retries "$PNPM_FETCH_RETRIES" \
      --network-concurrency "$PNPM_NETWORK_CONCURRENCY" \
      --registry "$PNPM_REGISTRY"
    printf '%s\n' "$current_admin_dep_hash" > "$ADMIN_DEP_HASH_FILE"
  else
    log "管理前端依赖未变化，跳过 pnpm install"
  fi

  HUSKY=0 CI=true VITE_DEPLOY_MODE=server VITE_CDN=false $PNPM_RUNNER build
  cd "$APP_DIR"
fi

restart_backend

log "后端部署完成"
