#!/bin/bash
set -e
set -o pipefail

# This script updates Vercel environment variables for services that consume a deployed service.
# It's called when a service is deployed to avoid updating all services unnecessarily.

# Arguments:
# $1: The environment variable name of the deployed service URL (e.g., SERVICO_USUARIOS_URL)
# $2: The new URL value
# $3: The Vercel organization ID
# $4: The Vercel token

CHANGED_VAR_NAME=$1
CHANGED_VAR_VALUE=$2
VERCEL_ORG_ID=$3
VERCEL_TOKEN=$4

if [ -z "$CHANGED_VAR_NAME" ] || [ -z "$CHANGED_VAR_VALUE" ] || [ -z "$VERCEL_ORG_ID" ] || [ -z "$VERCEL_TOKEN" ]; then
  echo "Error: Missing required arguments."
  echo "Usage: $0 <VAR_NAME> <VAR_VALUE> <ORG_ID> <TOKEN>"
  exit 1
fi

# Map Vercel project names to their paths in the repository
declare -A PROJECT_PATHS
PROJECT_PATHS["servico-usuarios"]="services/servico-usuarios"
PROJECT_PATHS["servico-busca"]="services/servico-busca"
PROJECT_PATHS["servico-monitoramento"]="services/servico-monitoramento"
PROJECT_PATHS["servico-agentes-ia"]="services/servico-agentes-ia"
PROJECT_PATHS["servico-lojas"]="services/servico-lojas"
PROJECT_PATHS["servico-ofertas"]="services/servico-ofertas"
PROJECT_PATHS["servico-produtos"]="services/servico-produtos"
PROJECT_PATHS["servico-healthcheck"]="services/servico-healthcheck"

# Dependency map: key is the service URL variable, value is a space-separated list of Vercel project names that consume it.
# frontend-tester is handled separately in the workflow.
declare -A DEPS
DEPS["SERVICO_USUARIOS_URL"]="servico-lojas servico-produtos servico-ofertas servico-monitoramento servico-healthcheck"
DEPS["SERVICO_LOJAS_URL"]="servico-healthcheck"
DEPS["SERVICO_PRODUTOS_URL"]="servico-agentes-ia servico-monitoramento servico-healthcheck"
DEPS["SERVICO_OFERTAS_URL"]="servico-healthcheck"
DEPS["SERVICO_BUSCA_URL"]="servico-agentes-ia servico-healthcheck"
DEPS["SERVICO_AGENTES_IA_URL"]="servico-healthcheck"
DEPS["SERVICO_MONITORAMENTO_URL"]="servico-healthcheck"
DEPS["SERVICO_HEALTHCHECK_URL"]="" # No backend services consume this

CONSUMERS=${DEPS[$CHANGED_VAR_NAME]}

if [ -z "$CONSUMERS" ]; then
  echo "No consumers to update for $CHANGED_VAR_NAME. Exiting."
  exit 0
fi

echo "--- Updating consumers for $CHANGED_VAR_NAME ---"
echo "New URL: $CHANGED_VAR_VALUE"
echo "Consumers: $CONSUMERS"

for TARGET_PROJECT in $CONSUMERS; do
  TARGET_PATH=${PROJECT_PATHS[$TARGET_PROJECT]}
  if [ -z "$TARGET_PATH" ]; then
    echo "Warning: Path for project $TARGET_PROJECT not found. Skipping."
    continue
  fi

  echo "--- Updating environment for project: $TARGET_PROJECT in path $TARGET_PATH ---"
  
  # Navigate into the service directory and link the project
  cd "$TARGET_PATH"
  vercel link --project "$TARGET_PROJECT" --scope="$VERCEL_ORG_ID" --token="$VERCEL_TOKEN" --yes
  
  echo "Setting $CHANGED_VAR_NAME for $TARGET_PROJECT"
  
  # Remove the old variable, ignoring errors if it doesn't exist.
  # The 'yes |' pipe is to automatically confirm the removal.
  yes | vercel env rm "$CHANGED_VAR_NAME" production --scope="$VERCEL_ORG_ID" --token="$VERCEL_TOKEN" 2>/dev/null || true
  
  # Add the new variable
  echo "$CHANGED_VAR_VALUE" | vercel env add "$CHANGED_VAR_NAME" production --scope="$VERCEL_ORG_ID" --token="$VERCEL_TOKEN"
  
  # Return to the root directory
  cd -
done

echo "--- Finished updating consumers for $CHANGED_VAR_NAME ---"
