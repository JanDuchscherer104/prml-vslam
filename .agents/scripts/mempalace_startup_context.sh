#!/usr/bin/env bash
set -u

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root" || exit 0

helper=".agents/skills/mempalace-repo/scripts/mempalace_repo.py"
log_dir=".artifacts/mempalace/logs"
lock_dir=".artifacts/mempalace/startup-refresh.lock"
log_file="$log_dir/startup-refresh.log"

echo "PRML VSLAM MemPalace startup context"

if [ ! -f "$helper" ]; then
  echo "- MemPalace helper missing at \`$helper\`; skipping startup refresh."
  exit 0
fi

mkdir -p "$log_dir"

if [ "${MEMPALACE_SKIP_STARTUP_REFRESH:-}" = "1" ]; then
  echo "- Startup refresh skipped by MEMPALACE_SKIP_STARTUP_REFRESH=1."
elif mkdir "$lock_dir" 2>/dev/null; then
  (
    trap 'rmdir "$lock_dir" 2>/dev/null || true' EXIT
    {
      printf '\n[%s] startup refresh begin\n' "$(date -Is)"
      python3 "$helper" refresh
      printf '[%s] startup refresh end\n' "$(date -Is)"
    } >>"$log_file" 2>&1
  ) &
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
