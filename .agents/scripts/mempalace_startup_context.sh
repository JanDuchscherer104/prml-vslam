#!/usr/bin/env bash
set -u

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root" || exit 0

helper=".agents/skills/mempalace-repo/scripts/mempalace_repo.py"
log_dir=".artifacts/mempalace/logs"
lock_dir=".artifacts/mempalace/startup-refresh.lock"
log_file="$log_dir/startup-refresh.log"
pid_file="$lock_dir/pid"

echo "PRML VSLAM MemPalace startup context"

if [ ! -f "$helper" ]; then
  echo "- MemPalace helper missing at \`$helper\`; skipping startup refresh."
  exit 0
fi

mkdir -p "$log_dir"

start_refresh() {
  refresh_script='
    repo_root="$1"
    helper="$2"
    log_file="$3"
    lock_dir="$4"
    pid_file="$5"
    cd "$repo_root" || exit 0
    trap '\''rm -f "$pid_file"; rmdir "$lock_dir" 2>/dev/null || true'\'' EXIT
    printf "%s\n" "$$" >"$pid_file"
    {
      printf "\n[%s] startup refresh begin\n" "$(date -Is)"
      python3 "$helper" refresh
      printf "[%s] startup refresh end\n" "$(date -Is)"
    } >>"$log_file" 2>&1
  '
  if command -v setsid >/dev/null 2>&1; then
    setsid bash -c "$refresh_script" _ "$repo_root" "$helper" "$log_file" "$lock_dir" "$pid_file" >/dev/null 2>&1 &
  else
    nohup bash -c "$refresh_script" _ "$repo_root" "$helper" "$log_file" "$lock_dir" "$pid_file" >/dev/null 2>&1 &
  fi
}

if [ "${MEMPALACE_SKIP_STARTUP_REFRESH:-}" = "1" ]; then
  echo "- Startup refresh skipped by MEMPALACE_SKIP_STARTUP_REFRESH=1."
elif [ -d "$lock_dir" ]; then
  refresh_pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [ -n "$refresh_pid" ] && kill -0 "$refresh_pid" 2>/dev/null; then
    echo "- A MemPalace startup refresh is already running."
  else
    rm -rf "$lock_dir"
    if mkdir "$lock_dir" 2>/dev/null; then
      start_refresh
      echo "- Removed a stale MemPalace startup lock and restarted refresh."
    else
      echo "- A MemPalace startup refresh is already running."
    fi
  fi
elif mkdir "$lock_dir" 2>/dev/null; then
  start_refresh
  echo "- Refreshing docs and Codex chat histories in the background."
else
  echo "- A MemPalace startup refresh is already running."
fi

echo "- Refresh log: \`$log_file\`"
echo "- Search command: \`python3 $helper search \"query\"\`"
echo "- Use MemPalace before answering questions about prior Codex sessions, user preferences, previous attempts, or durable project decisions."
echo

python3 "$helper" wake-up 2>/dev/null || {
  echo "Wake-up context is unavailable. Check \`$log_file\` and run \`python3 $helper status\`."
}
