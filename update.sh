#!/usr/bin/env bash
# Safely fast-forward a production checkout and run the transactional installer.
set -euo pipefail

CHECK=0
ALLOW_DIRTY=0
USE_CURRENT=0
usage() { echo "Usage: sudo ./update.sh [--check] [--allow-dirty] [--current]"; }
while (($#)); do
  case "$1" in
    --check|--dry-run) CHECK=1 ;;
    --allow-dirty) ALLOW_DIRTY=1 ;;
    --current) USE_CURRENT=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
  shift
done

[[ -f install.sh && -d .git ]] || { echo "Run this from a vast-revenue-monitor Git checkout." >&2; exit 1; }
command -v flock >/dev/null || { echo "flock is required." >&2; exit 1; }
exec 9>"${TMPDIR:-/tmp}/vast-revenue-monitor-update.lock"
flock -n 9 || { echo "Another updater is already running." >&2; exit 1; }

GIT=(git)
if [[ ${EUID} -eq 0 && -n ${SUDO_USER:-} && ${SUDO_USER} != root ]]; then
  GIT=(sudo -u "$SUDO_USER" git)
fi
branch=$("${GIT[@]}" symbolic-ref --quiet --short HEAD) || { echo "Detached HEAD is not updateable." >&2; exit 1; }
upstream=$("${GIT[@]}" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)
echo "Checked-out branch: $branch (upstream: ${upstream:-none})"
if ((USE_CURRENT)); then
  [[ -n $upstream ]] || { echo "Current branch has no upstream." >&2; exit 1; }
  target=$upstream
else
  [[ $branch == main ]] || { echo "Production updates default to main; check out main or pass --current." >&2; exit 1; }
  target=origin/main
fi
if ((ALLOW_DIRTY == 0)) && [[ -n $("${GIT[@]}" status --porcelain --untracked-files=no) ]]; then
  echo "Refusing uncommitted tracked changes (use --allow-dirty only after reviewing them)." >&2
  exit 1
fi

old=$("${GIT[@]}" rev-parse HEAD)
echo "Fetching remotes (git fetch --prune)..."
"${GIT[@]}" fetch --prune
new=$("${GIT[@]}" rev-parse "$target")
echo "Old commit: $old"
echo "New commit: $new"
"${GIT[@]}" merge-base --is-ancestor "$old" "$new" || { echo "Update is not fast-forward; refusing." >&2; exit 1; }
if ((CHECK)); then
  [[ $old == "$new" ]] && echo "Already current; no action would be taken." || echo "Would fast-forward to $new and run sudo bash install.sh."
  exit 0
fi
if [[ $old != "$new" ]]; then
  "${GIT[@]}" merge --ff-only "$target"
else
  echo "Already current. Re-running installer to verify the installed application."
fi
if ! sudo bash install.sh; then
  echo "Source checkout is at $new; installation failed and install.sh performed its transactional rollback." >&2
  exit 1
fi
echo "Update and installation completed successfully."
