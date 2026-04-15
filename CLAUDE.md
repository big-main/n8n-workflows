# n8n-workflows Repository — AI Assistant Context

> This file provides comprehensive context for AI assistants (Claude and others) working in this codebase. It describes the repository's structure, conventions, tooling, and development workflows based on the actual state of the project.

---

## Overview

This repository is a **production-grade collection of 2,061+ n8n workflow automation files** paired with a full-stack web application for browsing, searching, and downloading them. It includes:

- `workflows/` — 2,061 n8n workflow JSON files spanning 188+ integrations
- A **FastAPI backend** (`api_server.py`) with SQLite FTS5 full-text search
- A **static GitHub Pages frontend** (`docs/`) for online browsing
- **Docker / Kubernetes / Helm** infrastructure for deployment
- A **medcards-ai** sub-project (Next.js + Supabase medical education app)
- Python scripts, test suites, and CI/CD pipelines

Live interface: `zie619.github.io/n8n-workflows`

---

## Repository Structure

```
n8n-workflows/
├── workflows/                  # 2,061 n8n workflow JSON files
│   ├── Activecampaign/         # Email marketing integrations
│   ├── Airtable/               # Airtable database workflows
│   ├── Code/                   # 183 code-node-heavy workflows
│   ├── Discord/                # Discord notifications
│   ├── Gmail/                  # Gmail integrations
│   ├── Googlesheets/           # 26 Google Sheets workflows
│   ├── Http/                   # 176 HTTP Request workflows
│   ├── Manual/                 # 391 manually-triggered workflows
│   ├── Slack/                  # 18 Slack workflows
│   ├── Splitout/               # 194 data-splitting workflows
│   ├── Telegram/               # 119 Telegram bot workflows
│   ├── Wait/                   # 104 wait/delay workflows
│   └── [180+ other integration directories...]
│
├── src/                        # Backend JavaScript/Python source
│   ├── server.js               # Express server entry point
│   ├── database.js             # Database abstraction layer
│   ├── index-workflows.js      # Workflow indexing logic
│   ├── init-db.js              # Database initialization
│   ├── analytics_engine.py     # Usage analytics
│   ├── ai_assistant.py         # AI-powered search/recommendations
│   ├── community_features.py   # Community contribution features
│   ├── enhanced_api.py         # Extended API endpoints
│   ├── integration_hub.py      # Integration metadata hub
│   ├── performance_monitor.py  # Runtime performance tracking
│   └── user_management.py      # User/auth management
│
├── docs/                       # GitHub Pages static site
│   ├── api/                    # API documentation
│   ├── css/                    # Stylesheets
│   └── js/                     # Frontend JavaScript
│
├── scripts/                    # Utility and deployment scripts
│   ├── deploy.sh               # Deployment automation
│   ├── backup.sh               # Database backup
│   ├── health-check.sh         # Health monitoring
│   ├── generate_search_index.py # Search index generator
│   └── update_readme_stats.py  # Dynamic README stats updater
│
├── context/                    # Search/categorization metadata
│   ├── def_categories.json     # Category definitions
│   ├── unique_categories.json  # Deduplicated category list
│   └── search_categories.json  # Search-optimized categories
│
├── k8s/                        # Kubernetes manifests
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── configmap.yaml
│
├── helm/                       # Helm chart for k8s deployment
│   └── workflows-docs/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│
├── medcards-ai/                # Sub-project: medical education app
│   ├── src/                    # Next.js source
│   ├── supabase/               # Supabase migrations/config
│   ├── prompts/                # LLM prompt templates
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.ts
│   └── README.md
│
├── .devcontainer/              # Dev container configuration
│   ├── devcontainer.json
│   ├── Dockerfile
│   └── init-firewall.sh
│
├── .github/                    # GitHub Actions CI/CD
├── static/                     # Static web assets (CSS, JS, images)
├── templates/                  # HTML templates
│
├── api_server.py               # FastAPI application (main backend)
├── workflow_db.py              # SQLite FTS5 database manager
├── run.py                      # Server launcher
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Default production Compose
├── docker-compose.dev.yml      # Development Compose (hot reload)
├── docker-compose.prod.yml     # Full production Compose stack
├── test_workflows.py           # Workflow JSON validation tests
├── test_api.sh                 # API endpoint tests
├── test_security.sh            # Security scanning tests
├── trivy.yaml                  # Container security scanning config
├── .env.example                # Environment variable template
├── DEPLOYMENT.md               # Deployment instructions
├── SECURITY.md                 # Security policy
├── CLAUDE.md                   # This file
├── CLAUDE_ZH.md                # Chinese version of this file
└── README.md                   # Main project documentation
```

---

## Workflow File Format

### File Naming Convention

```
{4-digit-ID}_{Service1}_{Service2}_{ActionType}_{TriggerType}.json
```

Examples:
- `0023_HTTP_Googlebigquery_Automation_Scheduled.json`
- `1525_Webhook_Telegram_Create_Webhook.json`
- `0737_Manual_Executecommand_Automation_Triggered.json`
- `1699_Code_Editimage_Automation_Webhook.json`

**ID range:** 0001–1962+, sequential numbering.  
**Service names:** PascalCase (`Http`, `Telegram`, `Googlesheets`).  
**Action types:** `Automation`, `Create`, `Update`, `Import`, `Send`, `Monitor`.  
**Trigger types:** `Webhook`, `Triggered`, `Scheduled`, `Manual`, `Automate`.

### Workflow JSON Structure

```json
{
  "id": "unique_workflow_id",
  "name": "Descriptive Workflow Name",
  "nodes": [
    {
      "id": "9a0c7f24-a344-4955-8bdc-b129e5d8d619",
      "name": "Node Display Name",
      "type": "n8n-nodes-base.httpRequest",
      "position": [480, 300],
      "parameters": { /* node-specific configuration */ },
      "credentials": { /* optional: credential reference only, no secrets */ },
      "typeVersion": 1,
      "notes": "Optional per-node documentation"
    }
  ],
  "connections": {
    "sourceNodeName": {
      "main": [[{ "node": "targetNodeName", "type": "main", "index": 0 }]]
    }
  },
  "settings": {
    "executionOrder": "v1",
    "saveManualExecutions": true,
    "timezone": "UTC",
    "executionTimeout": 3600,
    "maxExecutions": 1000,
    "retryOnFail": true,
    "retryCount": 3,
    "retryDelay": 1000
  },
  "meta": {
    "instanceId": "workflow-xxxxx",
    "versionId": "1.0.0",
    "createdAt": "ISO_TIMESTAMP",
    "updatedAt": "ISO_TIMESTAMP",
    "owner": "n8n-user",
    "license": "MIT",
    "category": "automation",
    "status": "active",
    "priority": "high",
    "environment": "production"
  },
  "tags": ["automation", "n8n", "production-ready"],
  "description": "What this workflow does in plain language",
  "notes": "Quality assessment, setup instructions, optimization notes"
}
```

**Key rules:**
- Node `id` values must be **UUID format** and **unique within the file**.
- `connections` keys are node **names** (not IDs).
- Credentials reference named credential configurations — no secrets in the file.
- `settings.retryOnFail`, `retryCount`, `retryDelay` are set at workflow level.

---

## Node Type Reference

### Top Node Types by Usage (across 2,061 workflows)

| Node Type | Count | Purpose |
|-----------|-------|---------|
| `stickyNote` | 1,204 | Visual documentation/annotations |
| `noOp` | 614 | Placeholder / LLM model nodes |
| `httpRequest` | 555 | Generic HTTP/REST API calls |
| `set` | 428 | Data transformation / field mapping |
| `if` | 192 | Conditional branching (2 outputs) |
| `webhook` | 134 | HTTP webhook triggers |
| `respondToWebhook` | 131 | HTTP response to webhook caller |
| `code` | 114 | JavaScript/Python code execution |
| `stopAndError` | 113 | Error handling / early termination |
| `googleSheets` | 89 | Google Sheets read/write |
| `manualTrigger` | 86 | Manual execution trigger |
| `switch` | 65 | Multi-branch conditional routing |
| `telegram` | 65 | Telegram bot messaging |
| `merge` | 41 | Merge multiple data streams |
| `googleDrive` | 40 | Google Drive file operations |
| `cron` | 32 | Legacy time-based scheduling |
| `scheduleTrigger` | 31 | Modern time-based scheduling |
| `gmail` | 29 | Gmail email operations |
| `executeWorkflow` | 29 | Call sub-workflows |
| `notion` | 28 | Notion database operations |
| `filter` | 27 | Filter items by condition |
| `limit` | 27 | Limit number of items |
| `splitInBatches` | 24 | Batch processing |
| `aggregate` | 23 | Data aggregation |
| `airtable` | 22 | Airtable database operations |
| `redis` | 19 | Redis cache operations |

### Trigger Node Types

- `manualTrigger` — Manual single-run execution
- `scheduleTrigger` / `cron` — Time-based (use `scheduleTrigger` for new workflows)
- `webhook` — HTTP webhook (paired with `respondToWebhook` for sync responses)
- `executeWorkflowTrigger` — Triggered by another workflow
- Service-specific triggers: `telegramTrigger`, `githubTrigger`, `gmailTrigger`, `stripeTrigger`, `formTrigger`, etc.

---

## Common Workflow Patterns

### 1. Data Pipeline
```
Trigger → Fetch Data (HTTP/API/DB) → Transform (Code/Set) → Output (DB/File/Message)
```
Example: `0023_HTTP_Googlebigquery_Automation_Scheduled.json`

### 2. Integration Sync
```
Schedule Trigger → External API → Filter/Deduplicate → Update Target System
```
Example: Strava activity → Google Sheets sync

### 3. Event-Driven Automation
```
Webhook → Processing (If/Switch) → Conditional Outputs (Slack/Email/Telegram)
```
Example: `1525_Webhook_Telegram_Create_Webhook.json` (WooCommerce → Telegram)

### 4. Document Processing with AI
```
Source (Drive/File) → Conversion → AI/LLM Processing → Structured Output
```
Example: `1699_Code_Editimage_Automation_Webhook.json` (PDF → OCR → LLM)

### 5. Error-Handled Automation
```
Trigger → Try (main path) → stopAndError (catch) → Alert/Log
```
All production workflows should include `stopAndError` nodes as error catchers.

---

## Backend Application

### FastAPI Server (`api_server.py`)

The main backend is a **FastAPI application** providing REST API access to the workflow collection.

**Key features:**
- Rate limiting: 60 requests/minute per IP
- Path traversal attack prevention
- CORS restricted to specific origins
- GZip compression middleware
- JWT authentication support
- Full-text search via SQLite FTS5

**Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/search` | Full-text workflow search |
| `GET` | `/api/stats` | Repository statistics (also healthcheck) |
| `GET` | `/api/workflow/{id}` | Fetch single workflow JSON |
| `GET` | `/api/categories` | List all integration categories |
| `GET` | `/api/export` | Bulk export workflows |

### Database (`workflow_db.py`)

SQLite database manager with **FTS5 full-text search** for fast querying across all 2,061 workflows. Handles indexing, metadata storage, and categorization.

### Running Locally

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the server (default: http://localhost:8000)
python run.py
```

**Python version requirement:** 3.9+

### Key Python Dependencies

```
fastapi==0.109.0        # Web framework
uvicorn[standard]==0.27.0  # ASGI server
pydantic==2.5.3         # Data validation
PyJWT==2.8.0            # JWT auth
passlib[bcrypt]==1.7.4  # Password hashing
httpx==0.26.0           # Async HTTP client
requests==2.31.0        # Sync HTTP client
psutil==5.9.8           # System monitoring
gunicorn==21.2.0        # Production WSGI server
```

---

## Docker & Infrastructure

### Docker

The `Dockerfile` is a **multi-stage build** using `python:3.11-slim-bookworm`:
- Non-root user (`appuser`, UID 1001) for security
- Healthcheck hits `/api/stats`
- Supports `linux/amd64` and `linux/arm64`
- No cached layers for security-sensitive packages

```bash
# Build
docker build -t n8n-workflows .

# Run (default)
docker-compose up

# Development (hot reload)
docker-compose -f docker-compose.dev.yml up

# Production stack
docker-compose -f docker-compose.prod.yml up
```

### Kubernetes

Manifests in `k8s/` provide a full production deployment:
- `namespace.yaml` — Isolated `n8n` namespace
- `deployment.yaml` — StatefulSet configuration
- `service.yaml` — LoadBalancer service
- `ingress.yaml` — Ingress routing
- `configmap.yaml` — Configuration management

Helm chart in `helm/workflows-docs/` provides templated k8s deployment with `Chart.yaml` and configurable `values.yaml`.

---

## Testing

### Workflow Validation (`test_workflows.py`)
Validates all workflow JSON files for:
- Valid JSON structure
- Required fields present (`id`, `name`, `nodes`, `connections`)
- Unique node IDs within each workflow
- Valid node type references
- Connection integrity

### API Tests (`test_api.sh`)
Shell script testing all API endpoints for correct responses.

### Security Tests (`test_security.sh`)
Runs Trivy container security scanning (config in `trivy.yaml`). Checks for known CVEs in dependencies and container image.

```bash
# Run workflow validation
python test_workflows.py

# Run API tests
bash test_api.sh

# Run security scan
bash test_security.sh
```

---

## Development Conventions

### For Workflow Analysis Tasks
1. Parse JSON files to understand the complete node chain
2. Identify the **business purpose**, not just the technical implementation
3. Map all external service dependencies and credentials required
4. Note trigger type (scheduled/webhook/manual) and expected frequency
5. Check for error handling completeness

### For Workflow Documentation Tasks
1. Describe **what the workflow accomplishes** (not which nodes it uses)
2. State the trigger mechanism clearly
3. List every external service/API required
4. Document any required credentials or configuration
5. Note retry logic and error handling present

### For Workflow Modification Tasks
1. Preserve required JSON fields (`id`, `name`, `nodes`, `connections`, `settings`)
2. Keep node IDs as UUIDs — generate new ones for new nodes
3. Update `connections` when adding/removing/renaming nodes
4. Connection keys use node **names**, not IDs
5. Validate JSON structure after modifications

### For Adding New Workflows
1. Follow naming convention: `{ID}_{Service1}_{Service2}_{Action}_{Trigger}.json`
2. Use next available sequential ID number
3. Place in the appropriate integration subdirectory under `workflows/`
4. Include `description` and `meta` fields
5. Add `stickyNote` nodes for setup instructions on complex workflows
6. Include `stopAndError` nodes for error handling on critical paths

---

## Security Considerations

- **No secrets in workflow files** — credentials reference named configurations stored in n8n, not the JSON files themselves
- **Webhook URLs** may appear in trigger node configurations — treat as sensitive
- **Hardcoded values** (API keys, tokens, URLs) in `parameters` should be flagged and replaced with n8n credential references or environment variables
- The API server uses **parameterized queries** (SQLite) to prevent SQL injection — maintain this when extending database queries
- The `api_server.py` enforces **path traversal prevention** — do not weaken this when modifying file-serving logic
- `trivy.yaml` and `test_security.sh` should be run before any Docker image changes

---

## AI & Agent Platform Integrations

### OpenClaw (v2026.4.14 — April 14, 2026)

[OpenClaw](https://github.com/openclaw/openclaw) is an open-source AI agent orchestration platform relevant to workflows in this collection that route through LLM-powered agents. Key capabilities as of v2026.4.14:

**Model support**
- Forward-compatible with `gpt-5.4-pro` (Codex pricing tier) — relevant when building workflows that call OpenClaw as an HTTP endpoint or sub-agent
- Use `httpRequest` nodes to invoke OpenClaw's API; credential references should store API keys, not inline values

**Telegram integration improvements**
- Human-readable forum topic names now surface in agent context, prompt metadata, and plugin hook metadata via Telegram service messages
- Affects workflows in `workflows/Telegram/` that route messages through an OpenClaw agent — topic context is now available as a named field rather than a raw ID

**Security changes to be aware of (v2026.4.14)**
- **Slack `allowFrom`** — global channel allowlist is now enforced on all channel interactions; workflows that post to Slack via OpenClaw must ensure the n8n instance hostname is in the allowlist
- **Media attachment path resolution** — canonical path failures now fail closed; workflows handling file attachments through OpenClaw should not rely on path fallbacks
- **Markdown ReDoS** — maliciously crafted markdown can no longer freeze the OpenClaw Control UI; no workflow changes needed, but relevant for any workflow that forwards user-supplied text to the OpenClaw UI
- **Browser SSRF** — hostname navigation restored under default policy; strict mode remains available and should be used in production deployments

**Common n8n → OpenClaw workflow pattern**
```
Trigger → Prepare Payload (Set) → HTTP Request (OpenClaw API) → Parse Response (Code/Set) → Output
```
- Authenticate via `Authorization: Bearer` header stored as an n8n credential
- Use `respondToWebhook` if OpenClaw is calling n8n back as a plugin hook
- Telegram forum topic name is now available at `$json.topic_name` in OpenClaw webhook payloads

---

## medcards-ai Sub-project

The `medcards-ai/` directory contains an independent **Next.js application** for medical education (flashcard-style learning powered by AI). It uses:
- **Next.js** (TypeScript) frontend
- **Supabase** for database and authentication
- **LLM prompts** in `prompts/` for AI-generated content
- Independent `package.json` and `tsconfig.json`

To work on this sub-project, `cd medcards-ai/` and run `npm install` first. It has its own README, EXECUTIVE_SUMMARY.md, SCALABILITY_ARCHITECTURE.md, and PRODUCT_STRATEGY.md.

---

## Workflow Statistics (Current State)

| Metric | Value |
|--------|-------|
| Total workflow files | 2,061 |
| Integration categories | 188 |
| Unique node types | 300+ |
| Total nodes across all workflows | 29,445+ |
| Largest category | Manual (391 workflows) |
| Most-used node | stickyNote (1,204 instances) |
| Most-used integration node | httpRequest (555 instances) |

---

## Helpful Context for AI Assistants

### Workflow Analysis
- Focus on **business purpose** by examining the full node chain, not individual nodes in isolation
- `stickyNote` nodes contain human-written setup instructions — read them for context
- `noOp` nodes are often placeholder nodes for LLM model integrations
- The `connections` object uses node **names** as keys — cross-reference with `nodes[].name`

### Common Pitfalls
- Incorrect node **connections** (using IDs instead of names, or wrong output index)
- Missing **error handling** — production workflows need `stopAndError` nodes
- Inefficient **loops** — prefer `splitInBatches` over unbounded iteration
- **Hardcoded values** that should be credentials or parameters

### Optimization Opportunities
- Replace `cron` trigger with `scheduleTrigger` (newer API)
- Use `filter` node instead of `if` + `noOp` for simple filtering
- Use `splitInBatches` for large dataset processing
- Extract repeated sub-flows into separate workflows called via `executeWorkflow`

### Code Generation for Workflow Tooling
- Handle multiple n8n format versions (older files may lack `meta`, `settings`)
- Connection keys are node names — account for name collisions
- Parse n8n expressions (`={{ $json.field }}`) carefully — they are JavaScript-like
- Node execution order follows connections; nodes without inputs run first
- `typeVersion` matters — same node type may behave differently across versions

---

## Version & Compatibility

- **n8n compatibility:** Workflows support n8n v0.x through v1.x formats
- **Python:** 3.9+ required for backend
- **Node.js:** Required for `src/*.js` scripts and `medcards-ai/`
- **Last major update:** November 2025 (security audit, Docker multi-platform, GitHub Pages)
- **OpenClaw:** v2026.4.14 (April 2026) — `gpt-5.4-pro` support, Telegram forum topic names in agent context, Slack `allowFrom` enforcement, media path fail-closed, ReDoS fix

---

[中文版本](./CLAUDE_ZH.md)
