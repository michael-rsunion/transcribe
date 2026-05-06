#!/usr/bin/env bash
# Pre-commit guard: falla si el UUID del CRM aparece en archivos de deploy/scripts.
# Solo se permite el UUID en docs/ (donde se documenta como blocklist).

set -euo pipefail

# shellcheck source=./coolify_constants.sh
source "$(dirname "$0")/coolify_constants.sh"

# Buscamos en archivos de deploy/scripts/build, NO en docs ni en sí mismo.
LEAKED=$(grep -RIln "$CRM_PROJECT_UUID" \
  --include="Makefile" \
  --include="Dockerfile" \
  --include="*.yml" \
  --include="*.yaml" \
  --include="*.sh" \
  --include="*.py" \
  app/ scripts/ .github/ Dockerfile Makefile 2>/dev/null \
  | grep -v "scripts/coolify_constants.sh" \
  || true)

if [[ -n "$LEAKED" ]]; then
  echo "REFUSING: CRM project uuid leaked in:" >&2
  echo "$LEAKED" >&2
  exit 1
fi

echo "OK: no leak del CRM uuid."
