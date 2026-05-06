#!/usr/bin/env bash
# Verifica que un UUID no sea el del CRM. Falla con exit 1 si lo es.
# Uso: bash scripts/assert_not_crm.sh <uuid>

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "uso: $0 <uuid>" >&2
  exit 2
fi

# shellcheck source=./coolify_constants.sh
source "$(dirname "$0")/coolify_constants.sh"

if [[ "$1" == "$CRM_PROJECT_UUID" ]]; then
  echo "REFUSING: target uuid '$1' es el CRM project. Aborting." >&2
  exit 1
fi

echo "OK: uuid '$1' es seguro (no es el CRM)."
