#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}")"
APP_DIR="${APP_DIR:-/www/wwwroot/code/kuntin/backend}"
BRANCH="${BRANCH:-main}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
RESTART_CMD="${RESTART_CMD:-}"
BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-}"
BT_PROJECT_NAME="${BT_PROJECT_NAME:-}"
BT_PROJECT_SCRIPT="${BT_PROJECT_SCRIPT:-}"
BT_PROJECT_SCRIPT_DIR="${BT_PROJECT_SCRIPT_DIR:-/etc/init.d}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-4100}"
UVICORN_APP="${UVICORN_APP:-app.main:app}"
UVICORN_LOG="${UVICORN_LOG:-$APP_DIR/uvicorn.log}"
REPO_URL="${REPO_URL:-}"
SKIP_GIT_PULL="${SKIP_GIT_PULL:-0}"
FORCE_INSTALL_DEPS="${FORCE_INSTALL_DEPS:-0}"
GIT_FETCH_RETRIES="${GIT_FETCH_RETRIES:-3}"
GIT_FETCH_RETRY_DELAY="${GIT_FETCH_RETRY_DELAY:-8}"
GIT_HTTP_VERSION="${GIT_HTTP_VERSION:-HTTP/1.1}"
DEPLOY_STATE_DIR="${DEPLOY_STATE_DIR:-$APP_DIR/.deploy-state}"
DEPLOY_LOCK_DIR="${DEPLOY_LOCK_DIR:-$DEPLOY_STATE_DIR/deploy.lock}"
DEPLOY_LOCK_INFO_FILE="$DEPLOY_LOCK_DIR/lock.info"
DEPLOY_LOCK_STALE_SECONDS="${DEPLOY_LOCK_STALE_SECONDS:-1800}"
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

is_truthy() {
  [[ "$1" == "1" || "$1" == "true" || "$1" == "yes" ]]
}

write_deploy_lock_info() {
  {
    printf 'pid=%s\n' "$$"
    printf 'started_at=%s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
    printf 'started_ts=%s\n' "$(date '+%s')"
    printf 'host=%s\n' "$(hostname 2>/dev/null || printf 'unknown')"
    printf 'app_dir=%s\n' "$APP_DIR"
    printf 'script_path=%s\n' "$SCRIPT_PATH"
  } > "$DEPLOY_LOCK_INFO_FILE"
}

load_deploy_lock_info() {
  DEPLOY_LOCK_OWNER_PID=""
  DEPLOY_LOCK_OWNER_STARTED_AT=""
  DEPLOY_LOCK_OWNER_STARTED_TS=""
  DEPLOY_LOCK_OWNER_HOST=""
  DEPLOY_LOCK_OWNER_APP_DIR=""
  DEPLOY_LOCK_OWNER_SCRIPT_PATH=""

  [[ -f "$DEPLOY_LOCK_INFO_FILE" ]] || return 1

  local key value
  while IFS='=' read -r key value; do
    case "$key" in
      pid) DEPLOY_LOCK_OWNER_PID="$value" ;;
      started_at) DEPLOY_LOCK_OWNER_STARTED_AT="$value" ;;
      started_ts) DEPLOY_LOCK_OWNER_STARTED_TS="$value" ;;
      host) DEPLOY_LOCK_OWNER_HOST="$value" ;;
      app_dir) DEPLOY_LOCK_OWNER_APP_DIR="$value" ;;
      script_path) DEPLOY_LOCK_OWNER_SCRIPT_PATH="$value" ;;
    esac
  done < "$DEPLOY_LOCK_INFO_FILE"

  return 0
}

deploy_lock_pid_running() {
  local lock_pid="${1:-}"
  [[ "$lock_pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$lock_pid" 2>/dev/null
}

find_other_deploy_process() {
  command -v pgrep >/dev/null 2>&1 || return 1

  local pid
  while IFS= read -r pid; do
    if [[ -n "$pid" && "$pid" != "$$" ]]; then
      printf '%s\n' "$pid"
      return 0
    fi
  done < <(pgrep -f "$SCRIPT_PATH" || true)

  return 1
}

deploy_lock_age_seconds() {
  local lock_mtime now_ts
  lock_mtime="$(stat -c '%Y' "$DEPLOY_LOCK_DIR" 2>/dev/null || true)"
  [[ "$lock_mtime" =~ ^[0-9]+$ ]] || return 1

  now_ts="$(date '+%s')"
  printf '%s\n' "$((now_ts - lock_mtime))"
}

clear_deploy_lock_dir() {
  case "$DEPLOY_LOCK_DIR" in
    "$DEPLOY_STATE_DIR"/*) ;;
    *)
      fail "部署锁目录不在状态目录内，拒绝清理: $DEPLOY_LOCK_DIR"
      ;;
  esac

  rm -rf "$DEPLOY_LOCK_DIR"
}

release_deploy_lock() {
  if [[ -n "${DEPLOY_LOCK_HELD:-}" ]]; then
    rm -f "$DEPLOY_LOCK_INFO_FILE" 2>/dev/null || true
    rmdir "$DEPLOY_LOCK_DIR" 2>/dev/null || true
    unset DEPLOY_LOCK_HELD
  fi
}

acquire_deploy_lock() {
  if ! [[ "$DEPLOY_LOCK_STALE_SECONDS" =~ ^[0-9]+$ ]]; then
    fail "DEPLOY_LOCK_STALE_SECONDS 必须是非负整数"
  fi

  mkdir -p "$DEPLOY_STATE_DIR"

  if mkdir "$DEPLOY_LOCK_DIR" 2>/dev/null; then
    DEPLOY_LOCK_HELD=1
    write_deploy_lock_info
    trap release_deploy_lock EXIT
    trap 'release_deploy_lock; exit 130' INT
    trap 'release_deploy_lock; exit 143' TERM
    log "已获取部署锁: $DEPLOY_LOCK_DIR"
    return
  fi

  if load_deploy_lock_info; then
    if deploy_lock_pid_running "$DEPLOY_LOCK_OWNER_PID"; then
      log "已有部署任务正在执行，PID: ${DEPLOY_LOCK_OWNER_PID:-unknown}，开始时间: ${DEPLOY_LOCK_OWNER_STARTED_AT:-unknown}，主机: ${DEPLOY_LOCK_OWNER_HOST:-unknown}，部署目录: ${DEPLOY_LOCK_OWNER_APP_DIR:-unknown}"
      exit 0
    fi

    log "检测到陈旧部署锁，持有进程已不存在，准备清理: pid=${DEPLOY_LOCK_OWNER_PID:-unknown} started_at=${DEPLOY_LOCK_OWNER_STARTED_AT:-unknown}"
  else
    local other_deploy_pid=""
    other_deploy_pid="$(find_other_deploy_process || true)"
    if [[ -n "$other_deploy_pid" ]]; then
      log "检测到另一个部署脚本进程仍在运行，PID: $other_deploy_pid，继续保留现有锁: $DEPLOY_LOCK_DIR"
      exit 0
    fi

    local lock_age=""
    lock_age="$(deploy_lock_age_seconds || true)"
    if [[ "$lock_age" =~ ^[0-9]+$ ]] && (( lock_age < DEPLOY_LOCK_STALE_SECONDS )); then
      log "检测到近期创建但缺少元数据的部署锁（${lock_age}s < ${DEPLOY_LOCK_STALE_SECONDS}s），为避免并发部署，本次退出: $DEPLOY_LOCK_DIR"
      exit 0
    fi

    if [[ "$lock_age" =~ ^[0-9]+$ ]]; then
      log "检测到无元数据的陈旧部署锁（已存在 ${lock_age}s），准备清理: $DEPLOY_LOCK_DIR"
    else
      log "检测到无法识别的部署锁，准备按陈旧锁处理: $DEPLOY_LOCK_DIR"
    fi
  fi

  clear_deploy_lock_dir

  if mkdir "$DEPLOY_LOCK_DIR" 2>/dev/null; then
    DEPLOY_LOCK_HELD=1
    write_deploy_lock_info
    trap release_deploy_lock EXIT
    trap 'release_deploy_lock; exit 130' INT
    trap 'release_deploy_lock; exit 143' TERM
    log "已清理陈旧部署锁并重新获取: $DEPLOY_LOCK_DIR"
    return
  fi

  if load_deploy_lock_info && deploy_lock_pid_running "$DEPLOY_LOCK_OWNER_PID"; then
    log "部署锁已被新的部署任务接管，PID: ${DEPLOY_LOCK_OWNER_PID:-unknown}，退出本次任务"
    exit 0
  fi

  fail "部署锁清理后仍无法重新获取: $DEPLOY_LOCK_DIR"
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
  local safe_dir
  safe_dir="$(git -C "$APP_DIR" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$APP_DIR")"

  if ! git config --global --get-all safe.directory | grep -Fxq "$safe_dir"; then
    log "登记 Git 安全目录: $safe_dir"
    git config --global --add safe.directory "$safe_dir"
  fi

  if [[ "$safe_dir" != "$APP_DIR" ]] && ! git config --global --get-all safe.directory | grep -Fxq "$APP_DIR"; then
    log "登记 Git 安全目录: $APP_DIR"
    git config --global --add safe.directory "$APP_DIR"
  fi
}

is_git_work_tree() {
  git -C "$APP_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1
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

update_code_from_git() {
  if is_truthy "$SKIP_GIT_PULL"; then
    log "已设置 SKIP_GIT_PULL，跳过 Git 拉取"
    return
  fi

  if ! is_git_work_tree; then
    log "部署目录不是 Git 仓库，跳过 Git 拉取"
    return
  fi

  log "拉取最新代码: origin/$BRANCH"
  local attempt
  for attempt in $(seq 1 "$GIT_FETCH_RETRIES"); do
    if git -C "$APP_DIR" -c http.version="$GIT_HTTP_VERSION" fetch origin "$BRANCH"; then
      git -C "$APP_DIR" reset --hard "origin/$BRANCH"
      git -C "$APP_DIR" clean -fd
      return
    fi

    if [[ "$attempt" -lt "$GIT_FETCH_RETRIES" ]]; then
      log "Git 拉取失败，${GIT_FETCH_RETRY_DELAY}s 后重试 ($attempt/$GIT_FETCH_RETRIES)"
      sleep "$GIT_FETCH_RETRY_DELAY"
    fi
  done

  fail "Git 拉取失败。若 $APP_DIR 已由中转目录同步到最新代码，可设置 SKIP_GIT_PULL=1 后重试。"
}

restart_backend() {
  if [[ -n "$RESTART_CMD" ]]; then
    log "执行自定义重启命令"
    bash -lc "$RESTART_CMD"
    return
  fi

  if restart_bt_project; then
    return
  fi

  if [[ -n "$BACKEND_SERVICE_NAME" ]]; then
    if command -v supervisorctl >/dev/null 2>&1; then
      if supervisorctl status "$BACKEND_SERVICE_NAME" >/dev/null 2>&1; then
        log "重启 supervisor 服务: $BACKEND_SERVICE_NAME"
        supervisorctl restart "$BACKEND_SERVICE_NAME"
        return
      fi

      if supervisorctl status 2>/dev/null | awk '{print $1}' | grep -Eq "^${BACKEND_SERVICE_NAME}(:|$)"; then
        log "重启 supervisor 服务组: $BACKEND_SERVICE_NAME"
        supervisorctl restart "$BACKEND_SERVICE_NAME:*"
        return
      fi
    fi

    if command -v systemctl >/dev/null 2>&1; then
      if systemctl list-unit-files "${BACKEND_SERVICE_NAME}.service" --no-legend 2>/dev/null | grep -q . ||
        systemctl list-units --all "${BACKEND_SERVICE_NAME}.service" --no-legend 2>/dev/null | grep -q .; then
        log "重启 systemd 服务: $BACKEND_SERVICE_NAME"
        systemctl restart "$BACKEND_SERVICE_NAME"
        return
      fi
    fi

    log "未找到可重启的服务: $BACKEND_SERVICE_NAME，改用 uvicorn 命令重启"
  else
    log "未配置服务名，改用 uvicorn 命令重启"
  fi

  restart_uvicorn_backend
}

resolve_bt_project_script() {
  if [[ -n "$BT_PROJECT_SCRIPT" ]]; then
    [[ -f "$BT_PROJECT_SCRIPT" ]] || return 1
    printf '%s\n' "$BT_PROJECT_SCRIPT"
    return 0
  fi

  [[ -n "$BT_PROJECT_NAME" ]] || return 1

  local candidate="$BT_PROJECT_SCRIPT_DIR/${BT_PROJECT_NAME}_pymanager"
  [[ -f "$candidate" ]] || return 1
  printf '%s\n' "$candidate"
}

backend_process_pattern() {
  printf 'uvicorn %s.*--port %s' "$UVICORN_APP" "$BACKEND_PORT"
}

stop_uvicorn_backend() {
  local pattern
  pattern="$(backend_process_pattern)"
  local pids=()
  local pid

  if command -v pgrep >/dev/null 2>&1; then
    mapfile -t pids < <(pgrep -f "$pattern" || true)
    for pid in "${pids[@]}"; do
      if [[ -n "$pid" && "$pid" != "$$" ]]; then
        log "停止旧 uvicorn 进程: $pid"
        kill "$pid" 2>/dev/null || true
      fi
    done

    sleep 1

    mapfile -t pids < <(pgrep -f "$pattern" || true)
    for pid in "${pids[@]}"; do
      if [[ -n "$pid" && "$pid" != "$$" ]]; then
        log "强制停止旧 uvicorn 进程: $pid"
        kill -9 "$pid" 2>/dev/null || true
      fi
    done
    return
  fi

  pkill -f "$pattern" 2>/dev/null || true
  sleep 1
}

wait_backend_started() {
  local pattern
  pattern="$(backend_process_pattern)"
  local started_pid=""

  sleep 2

  if command -v pgrep >/dev/null 2>&1; then
    started_pid="$(pgrep -f "$pattern" | head -n 1 || true)"
  fi

  if [[ -n "$started_pid" ]]; then
    log "uvicorn 已启动，PID: $started_pid，日志: $UVICORN_LOG"
    return
  fi

  if command -v ss >/dev/null 2>&1 && ss -ltn "( sport = :$BACKEND_PORT )" 2>/dev/null | grep -q LISTEN; then
    log "后端端口已监听: $BACKEND_HOST:$BACKEND_PORT，日志: $UVICORN_LOG"
    return
  fi

  fail "uvicorn 启动失败，请查看日志: $UVICORN_LOG"
}

restart_bt_project() {
  local project_script project_service
  project_script="$(resolve_bt_project_script)" || return 1
  project_service="$(basename "$project_script")"

  log "使用宝塔 Python 项目重启: ${BT_PROJECT_NAME:-$project_service}"

  if command -v service >/dev/null 2>&1; then
    if service "$project_service" restart >/dev/null 2>&1; then
      wait_backend_started
      return 0
    fi
  fi

  stop_uvicorn_backend
  bash "$project_script"
  wait_backend_started
  return 0
}

start_uvicorn_backend() {
  local started_pid

  mkdir -p "$(dirname "$UVICORN_LOG")"
  log "启动 uvicorn: $PYTHON_BIN -m uvicorn $UVICORN_APP --host $BACKEND_HOST --port $BACKEND_PORT --app-dir $APP_DIR"
  nohup "$PYTHON_BIN" -m uvicorn "$UVICORN_APP" \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" \
    --app-dir "$APP_DIR" \
    >> "$UVICORN_LOG" 2>&1 &
  started_pid=$!

  sleep 2
  if ! kill -0 "$started_pid" 2>/dev/null; then
    fail "uvicorn 启动失败，请查看日志: $UVICORN_LOG"
  fi

  log "uvicorn 已启动，PID: $started_pid，日志: $UVICORN_LOG"
}

restart_uvicorn_backend() {
  stop_uvicorn_backend
  start_uvicorn_backend
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

python_requirements_ready() {
  local python_to_check="${1:-$APP_DIR/.venv/bin/python}"
  [[ -x "$python_to_check" || "$(command -v "$python_to_check" 2>/dev/null)" ]] || return 1

  if ! "$python_to_check" -m pip --version >/dev/null 2>&1; then
    return 1
  fi

  if [[ -f "$APP_DIR/requirements.txt" ]]; then
    local requirement package_name
    while IFS= read -r requirement || [[ -n "$requirement" ]]; do
      requirement="$(printf '%s\n' "$requirement" | sed -E 's/#.*$//; s/^[[:space:]]+//; s/[[:space:]]+$//')"
      [[ -z "$requirement" || "$requirement" == -* ]] && continue

      package_name="$(printf '%s\n' "$requirement" | sed -E 's/[[:space:];].*$//; s/\[.*$//; s/[<>=!~].*$//')"
      [[ -z "$package_name" ]] && continue

      if ! "$python_to_check" -m pip show "$package_name" >/dev/null 2>&1; then
        log "Python 依赖缺失: $package_name"
        return 1
      fi
    done < "$APP_DIR/requirements.txt"
  fi

  "$python_to_check" -m pip check >/dev/null 2>&1
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

admin_node_modules_ready() {
  [[ -d "$APP_DIR/admin/node_modules" ]] || return 1

  if ! command -v node >/dev/null 2>&1; then
    log "未找到 node，无法检查管理前端依赖"
    return 1
  fi

  node - "$APP_DIR/admin" <<'NODE'
const fs = require("fs");
const path = require("path");

const root = process.argv[2];
const pkg = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
const deps = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
const missing = [];

for (const name of Object.keys(deps)) {
  if (!fs.existsSync(path.join(root, "node_modules", name, "package.json"))) {
    missing.push(name);
  }
}

if (!fs.existsSync(path.join(root, "node_modules", ".bin", "vite"))) {
  missing.push(".bin/vite");
}

if (missing.length > 0) {
  console.error(`管理前端依赖缺失: ${missing.join(", ")}`);
  process.exit(1);
}
NODE
}

ensure_python_deps() {
  local current_python_dep_hash cached_python_dep_hash
  current_python_dep_hash="$(calc_python_dep_hash)"
  cached_python_dep_hash=""
  if [[ -f "$PYTHON_DEP_HASH_FILE" ]]; then
    cached_python_dep_hash="$(tr -d '\r\n' < "$PYTHON_DEP_HASH_FILE")"
  fi

  if ! is_truthy "$FORCE_INSTALL_DEPS" && [[ "$current_python_dep_hash" == "$cached_python_dep_hash" ]] && python_requirements_ready "$APP_DIR/.venv/bin/python"; then
    log "后端依赖未变化，跳过 pip install"
    DEPLOY_PYTHON="$APP_DIR/.venv/bin/python"
    return
  fi

  if is_truthy "$FORCE_INSTALL_DEPS"; then
    log "已设置 FORCE_INSTALL_DEPS，强制检查并安装后端依赖"
  elif [[ "$current_python_dep_hash" == "$cached_python_dep_hash" ]]; then
    log "后端依赖缓存命中，但环境不完整，重新安装"
  fi

  resolve_python_runtime
  ensure_pip_available

  log "安装 Python 依赖"
  "$DEPLOY_PYTHON" -m pip install --upgrade pip
  "$DEPLOY_PYTHON" -m pip install -r "$APP_DIR/requirements.txt"
  python_requirements_ready "$DEPLOY_PYTHON" || fail "后端依赖安装后仍不完整，请检查 pip 输出"

  if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
    printf '%s\n' "$current_python_dep_hash" > "$PYTHON_DEP_HASH_FILE"
  fi
}

log "开始后端自动部署"
log "脚本目录: $SCRIPT_DIR"
log "部署目录: $APP_DIR"
prepare_deploy_environment
acquire_deploy_lock

if ! is_git_work_tree; then
  if [[ -z "$REPO_URL" ]]; then
    if is_truthy "$SKIP_GIT_PULL"; then
      log "部署目录不是 Git 仓库，但已设置 SKIP_GIT_PULL，继续使用现有文件"
    else
      fail "未找到 Git 仓库目录: $APP_DIR，请先执行 git init 并设置远程仓库，或设置 SKIP_GIT_PULL=1"
    fi
  else
    log "初始化部署仓库: $APP_DIR"
    mkdir -p "$APP_DIR"
    git -C "$APP_DIR" init
  fi
fi

if is_git_work_tree; then
  ensure_git_safe_directory
  ensure_git_remote
fi

cd "$APP_DIR"
update_code_from_git

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

  should_install_admin_deps=0
  if is_truthy "$FORCE_INSTALL_DEPS"; then
    log "已设置 FORCE_INSTALL_DEPS，强制安装管理前端依赖"
    should_install_admin_deps=1
  elif [[ ! -d "$APP_DIR/admin/node_modules" ]]; then
    log "管理前端 node_modules 不存在，需要安装依赖"
    should_install_admin_deps=1
  elif [[ "$current_admin_dep_hash" != "$cached_admin_dep_hash" ]]; then
    log "管理前端依赖清单有变化，需要安装依赖"
    should_install_admin_deps=1
  elif ! admin_node_modules_ready; then
    log "管理前端依赖缓存命中，但 node_modules 不完整，重新安装"
    should_install_admin_deps=1
  fi

  if [[ "$should_install_admin_deps" == "1" ]]; then
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
    admin_node_modules_ready || fail "管理前端依赖安装后仍不完整，请检查 pnpm 输出"
    printf '%s\n' "$current_admin_dep_hash" > "$ADMIN_DEP_HASH_FILE"
  else
    log "管理前端依赖未变化，跳过 pnpm install"
  fi

  HUSKY=0 CI=true VITE_DEPLOY_MODE=server VITE_CDN=false $PNPM_RUNNER build
  cd "$APP_DIR"
fi

restart_backend

log "后端部署完成"
