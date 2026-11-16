#!/usr/bin/env bash
# Linux/macOS: bash run.sh [https://hub.docker.com/r/USER/exercise10-transactions]
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
mkdir -p results
if [[ -n "${EX10_IMAGE:-}" ]]; then
    docker pull "$EX10_IMAGE"
else
    docker compose build python
fi
docker compose up -d ex10-mongo1 ex10-mongo2 ex10-mongo3
docker compose run --rm -T python init
if [[ -f results/lab_10_1_bank.json ]]; then
    lab_backup="results/archive-$(date +%Y%m%d-%H%M%S)-$$"
    mkdir -p "$lab_backup"
    find results -maxdepth 1 -type f -exec cp {} "$lab_backup/" \;
fi
docker compose run --rm -T python bank
docker compose run --rm -T python inventory
docker compose run --rm -T python durability-prepare
trap 'docker compose up -d ex10-mongo1 ex10-mongo2 ex10-mongo3' EXIT
docker compose kill -s SIGKILL ex10-mongo1 ex10-mongo2 ex10-mongo3
docker compose up -d ex10-mongo1 ex10-mongo2 ex10-mongo3
trap - EXIT
docker compose run --rm -T python durability-verify
lab_report_args=(report)
if [[ -n "${1:-}" ]]; then lab_report_args+=(--hub-url "$1"); fi
docker compose run --rm -T python "${lab_report_args[@]}"
