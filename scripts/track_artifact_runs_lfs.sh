#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/track_artifact_runs_lfs.sh [--dry-run] RUN_DIR...
  scripts/track_artifact_runs_lfs.sh [--dry-run] --all

Track post hoc analysis run artifacts with Git LFS. RUN_DIR is usually
.artifacts/<run>/<method>. The helper excludes native backend payloads,
RGB frame directories, dense point-cloud confidence arrays, point-cloud meshes,
and Rerun viewer recordings:

  - .artifacts/**/native/*
  - .artifacts/**/rgb/*
  - .artifacts/**/frames/*
  - point_cloud_confidences.npz
  - *.ply
  - *.rrd
USAGE
}

dry_run=0
all_runs=0
run_dirs=()

while (($#)); do
  case "$1" in
    --dry-run)
      dry_run=1
      ;;
    --all)
      all_runs=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      run_dirs+=("$1")
      ;;
  esac
  shift
done

if ((all_runs)) && ((${#run_dirs[@]})); then
  echo "Use either --all or explicit RUN_DIR arguments, not both." >&2
  exit 2
fi

if ((! all_runs)) && ((${#run_dirs[@]} == 0)); then
  usage >&2
  exit 2
fi

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "Run this from inside the Git repository." >&2
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if ! command -v git-lfs >/dev/null 2>&1 && ! git lfs version >/dev/null 2>&1; then
  echo "git-lfs is required to track artifact run directories." >&2
  exit 1
fi

analysis_subdirs=(
  alignment
  benchmark
  evaluation
  input
  reference
  reconstruction
  slam
  summary
  visualization
)

if ((all_runs)); then
  while IFS= read -r -d '' run_dir; do
    run_dirs+=("$run_dir")
  done < <(
    find .artifacts -mindepth 3 -maxdepth 3 -type d \
      \( -name alignment -o -name benchmark -o -name evaluation -o -name input \
      -o -name reference -o -name reconstruction -o -name slam -o -name summary \
      -o -name visualization \) -printf '%h\0' | sort -zu
  )
fi

tmp_paths="$(mktemp)"
trap 'rm -f "$tmp_paths"' EXIT

for run_dir in "${run_dirs[@]}"; do
  if [[ ! -d "$run_dir" ]]; then
    echo "Missing run directory: $run_dir" >&2
    exit 1
  fi

  found_analysis_subdir=0
  for subdir in "${analysis_subdirs[@]}"; do
    [[ -d "$run_dir/$subdir" ]] && found_analysis_subdir=1
  done
  if ((found_analysis_subdir == 0)); then
    echo "Not a recognized artifact run directory: $run_dir" >&2
    exit 1
  fi

  find "$run_dir" -type f \
    ! -path '*/native/*' \
    ! -path '*/rgb/*' \
    ! -path '*/frames/*' \
    ! -name 'point_cloud_confidences.npz' \
    ! -name '*.ply' \
    ! -name '*.rrd' \
    -print0 >> "$tmp_paths"
done

if [[ ! -s "$tmp_paths" ]]; then
  echo "No eligible artifact files found."
  exit 0
fi

if ((dry_run)); then
  count="$(tr -cd '\0' < "$tmp_paths" | wc -c)"
  bytes="$(tr '\0' '\n' < "$tmp_paths" | xargs -r du -cb | tail -n 1 | awk '{print $1}')"
  echo "Would add $count files ($(numfmt --to=iec-i --suffix=B "$bytes")):"
  tr '\0' '\n' < "$tmp_paths"
  exit 0
fi

git lfs install --local --skip-smudge >/dev/null
git add .gitattributes .gitignore scripts/track_artifact_runs_lfs.sh
git add -f --pathspec-from-file="$tmp_paths" --pathspec-file-nul

echo "Staged Git LFS tracking metadata and eligible artifact files."
