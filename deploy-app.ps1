<#
.SYNOPSIS
    Build the combined-app Docker image, push it to ACR, and update the Container App.

.DESCRIPTION
    The combined-app mounts all 3 workshop experiences on a single FastAPI instance:
      /              -> Multi-Agent Shopping Assistant
      /a2a-demo/     -> A2A Protocol Demo
      /collab-lab/   -> Agent Collaboration Lab

    This script:
      1. Discovers the ACR + Container App in the resource group
      2. Builds and pushes src/Dockerfile.combined to ACR (cloud build)
      3. Updates the Container App image and required env vars
      4. Prints the public URL

.PARAMETER ResourceGroup
    Azure resource group that contains the resources from DeployAzureResources.bicep.

.PARAMETER GptEndpoint
    Azure OpenAI / Foundry endpoint for the gpt deployment (e.g. https://aif-xxx.openai.azure.com/).

.PARAMETER FoundryEndpoint
    Optional. Microsoft Foundry endpoint (e.g. https://aif-xxx.services.ai.azure.com/api/projects/proj-xxx).

.PARAMETER EmbeddingEndpoint
    Optional. Embedding model endpoint.

.PARAMETER Phi4Endpoint
    Optional. Phi-4 model endpoint.

.EXAMPLE
    .\deploy-app.ps1 -ResourceGroup "rg-aiappsagent-shopassist" `
                     -GptEndpoint "https://aif-xxx.openai.azure.com/" `
                     -FoundryEndpoint "https://aif-xxx.services.ai.azure.com/api/projects/proj-xxx"
#>

param(
    [Parameter(Mandatory = $true)]  [string]$ResourceGroup,
    [Parameter(Mandatory = $true)]  [string]$GptEndpoint,
    [string]$FoundryEndpoint,
    [string]$EmbeddingEndpoint,
    [string]$Phi4Endpoint
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Discovering Azure resources in $ResourceGroup ===" -ForegroundColor Cyan
$acrName = az acr list --resource-group $ResourceGroup --query "[0].name" -o tsv
$appName = az containerapp list --resource-group $ResourceGroup --query "[0].name" -o tsv

if (-not $acrName) { Write-Error "No Azure Container Registry found in $ResourceGroup"; exit 1 }
if (-not $appName) { Write-Error "No Azure Container App found in $ResourceGroup"; exit 1 }

$acrLoginServer = az acr show --name $acrName --query "loginServer" -o tsv
$tag = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "  ACR:           $acrName"
Write-Host "  Container App: $appName"
Write-Host "  Image tag:     $tag"

Write-Host "`n=== Building combined-app image (src/Dockerfile.combined) ===" -ForegroundColor Cyan
az acr build `
    --registry $acrName `
    --image "combined-app:$tag" `
    --file src/Dockerfile.combined `
    src/

Write-Host "`n=== Configuring ACR pull access ===" -ForegroundColor Cyan
az containerapp registry set `
    --name $appName `
    --resource-group $ResourceGroup `
    --server $acrLoginServer `
    --identity system | Out-Null

Write-Host "`n=== Updating Container App image + env vars ===" -ForegroundColor Cyan
$envVars = @("gpt_endpoint=$GptEndpoint")
if ($FoundryEndpoint)   { $envVars += "FOUNDRY_ENDPOINT=$FoundryEndpoint" }
if ($EmbeddingEndpoint) { $envVars += "embedding_endpoint=$EmbeddingEndpoint" }
if ($Phi4Endpoint)      { $envVars += "phi_4_endpoint=$Phi4Endpoint" }

az containerapp update `
    --name $appName `
    --resource-group $ResourceGroup `
    --image "$acrLoginServer/combined-app:$tag" `
    --set-env-vars @envVars | Out-Null

$fqdn = az containerapp show --name $appName --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" -o tsv

Write-Host "`n=== Deployment Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "  Shopping Assistant:      https://$fqdn/"            -ForegroundColor Yellow
Write-Host "  A2A Protocol Demo:       https://$fqdn/a2a-demo/"   -ForegroundColor Yellow
Write-Host "  Agent Collaboration Lab: https://$fqdn/collab-lab/" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Image: $acrLoginServer/combined-app:$tag" -ForegroundColor DarkGray
