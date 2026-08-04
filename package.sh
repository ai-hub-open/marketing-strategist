#!/usr/bin/env bash
# Сборка трёх пакетов набора в dist/ (запуск: ./package.sh)
# Файлы из dist/ прикладываются к релизу как есть, без переименования.

set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/package_skill.py "$@"
