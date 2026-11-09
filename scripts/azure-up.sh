#!/usr/bin/env bash
# Create (or update) the Azure resources the app needs and print the endpoint setting for .env.
#   scripts/azure-up.sh [resource-group] [location]
# Needs: az login, and rights to create a resource group and a role assignment in the current subscription.
set -euo pipefail
cd "$(dirname "$0")/.."

rg="${1:-rg-geert-content-understanding}"
location="${2:-swedencentral}"

az group create --name "$rg" --location "$location" --tags owner=Geert purpose=content-understanding-explorer -o none
user=$(az ad signed-in-user show --query id -o tsv)
endpoint=$(az deployment group create --resource-group "$rg" --name main --template-file infra/main.bicep \
  --parameters userObjectId="$user" --query properties.outputs.endpoint.value -o tsv)

echo "Deployed to $rg. Put this line in .env:"
echo "CONTENT_UNDERSTANDING_ENDPOINT=$endpoint"
echo "Remove everything again with: az group delete --name $rg"
