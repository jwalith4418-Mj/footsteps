#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 [SESSION_ID | --last]"
  echo "Open the Footsteps session picker, resume a specific session, or resume the latest."
}

if (( $# > 1 )); then
  usage >&2
  exit 2
fi
case ${1:-} in
  -h|--help) usage; exit 0 ;;
  --last) ;;
  -*) usage >&2; exit 2 ;;
esac

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$project_root"
exec direnv exec "$project_root" codex resume \
  --cd "$project_root" \
  --sandbox workspace-write \
  --ask-for-approval on-request \
  "$@"
