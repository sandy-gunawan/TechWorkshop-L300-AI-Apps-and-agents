# Tech Workshop L300 — AI Apps and Agents

This lab teaches you how to design and build AI applications and agents using **Microsoft Foundry**. You will learn how to create AI-powered applications that can interact with users, process natural language, and perform tasks based on user guidance. You will also learn how to monitor, troubleshoot, and perform red-teaming activities against agents.

## 🔗 Live Demo

A single Azure Container App hosts all three experiences at three sub-paths:

| Experience | URL |
|---|---|
| **Multi-Agent Shopping Assistant** | <https://app-4effoefsxjnb4.politefield-6c2fe495.eastus2.azurecontainerapps.io/> |
| **A2A Protocol Demo** | <https://app-4effoefsxjnb4.politefield-6c2fe495.eastus2.azurecontainerapps.io/a2a-demo/> |
| **Agent Collaboration Lab** | <https://app-4effoefsxjnb4.politefield-6c2fe495.eastus2.azurecontainerapps.io/collab-lab/> |

## Three Applications, One Container

| App | Path | Description |
|-----|------|-------------|
| **Multi-Agent Shopping Assistant** | `/` | Production-grade multi-agent system using Azure AI Foundry agents, MCP tools, and intent-based routing (the **Router** pattern) |
| **A2A Protocol Demo** | `/a2a-demo/` | Agent-to-Agent protocol demo with real-time visualization of agent delegation (the **Manager** pattern) |
| **Agent Collaboration Lab** | `/collab-lab/` | Multi-round agent-to-agent discussions with debate and consensus |

For a beginner-friendly explanation of **Router vs Manager**, see [Exercise 03 — Background](docs/03_extend_shopping_assistant_with_a2a/03_extend_shopping_assistant_with_a2a.md#background-multi-agent-router-vs-a2a-manager--whats-the-difference).

## Quick Start (Local)

```powershell
cd src

# Option A — run all three at once on http://localhost:8000
python -m uvicorn combined_app:app --port 8000

# Option B — run each individually (matches the workshop tutorials)
python -m uvicorn chat_app:app --port 8000     # Shopping Assistant
python a2a/main.py                              # A2A Demo on :8001
python a2ascenario/main.py                      # Collab Lab  on :8002
```

## Deploy to Azure

### 1. Provision infrastructure (Bicep / azd)

```powershell
azd up
# or, with the Azure CLI directly:
az deployment group create `
    --resource-group rg-aiappsagent-shopassist `
    --template-file src/infra/DeployAzureResources.bicep
```

This creates: Cosmos DB, Storage, Microsoft Foundry (account + project), Log Analytics, Application Insights, Azure Container Registry, a Container Apps Environment, and **one** Container App (placeholder image).

### 2. Build and push the combined-app image

```powershell
.\deploy-app.ps1 `
    -ResourceGroup "rg-aiappsagent-shopassist" `
    -GptEndpoint "https://your-openai.openai.azure.com/" `
    -FoundryEndpoint "https://your-foundry.services.ai.azure.com/api/projects/your-project"
```

The script discovers the ACR + Container App in the resource group, builds `src/Dockerfile.combined` in ACR, and updates the Container App with the new image and required env vars.

## Training Documentation

For trainers and newcomers — detailed guides covering architecture, patterns, and demo scripts:

| Doc | Description |
|-----|-------------|
| [01 — Solution Overview](docs/training/01-solution-overview.md) | What this is, tech stack, quick start |
| [02 — Architecture Deep Dive](docs/training/02-architecture-deep-dive.md) | Diagrams and code flows for all 3 apps |
| [03 — Agent Patterns Comparison](docs/training/03-agent-patterns-comparison.md) | When to use which pattern, decision flowchart |
| [04 — Implementation Guide](docs/training/04-implementation-guide.md) | Build each pattern step by step |
| [05 — Demo Script](docs/training/05-demo-script.md) | Presenter's guide with talking points |
| [06 — Observability & Security](docs/training/06-observability-and-security.md) | Monitoring, tracing, red teaming |
| [07 — Project Structure](docs/training/07-project-structure-reference.md) | File-by-file reference |

## Step by Step Instructions

The step by step instructions for this lab can be found in the [AI Apps and agents guide](https://microsoft.github.io/TechWorkshop-L300-AI-Apps-and-agents).

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
