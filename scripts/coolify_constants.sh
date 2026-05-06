#!/usr/bin/env bash
# Constantes de Coolify - UUIDs y nombres del CRM que NUNCA debemos tocar.
# Source este archivo desde otros scripts: source scripts/coolify_constants.sh

CRM_PROJECT_UUID="d12s8a99e91bm5wy72plgfur"
COOLIFY_SERVER_UUID="q6zzyixsxp4hjbq6xn7arjeg"
PROTECTED_APP_NAMES=("CRM Backend API" "CRM Frontend" "CRM Worker" "sorteo-whatsapp")

# Export para subshells
export CRM_PROJECT_UUID COOLIFY_SERVER_UUID PROTECTED_APP_NAMES
