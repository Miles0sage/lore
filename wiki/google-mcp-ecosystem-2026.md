# Google MCP Ecosystem 2026 — What People Are Building

**Date:** 2026-04-05  
**Sources:** GitHub search, Google Cloud Blog, NotebookLM synthesis, Exa deep search

---

## The Shift: Google Goes All-In on MCP (Dec 2025)

Google officially announced managed MCP servers for all its services on Dec 10, 2025. Not community work — production infrastructure from Google itself.

**Official Google MCP releases:**
- **Google Workspace MCP** — Gmail, Calendar, Drive, Docs, Sheets, Slides, Chat, Forms, Tasks
- **BigQuery MCP** (Jan 8, 2026) — fully managed remote MCP, natural language → SQL
- **Google Ads MCP** (Aug 2025) — `google-marketing-solutions/google_ads_mcp`, official repo
- **GCP operator MCP** — manage Cloud resources via natural language
- **Google Maps Platform MCP** — location, routing, places via LLM
- **Go SDK** — `modelcontextprotocol/go-sdk`, maintained in collaboration with Google

---

## The New Agent Stack: ADK + A2A + MCP

Google's answer to LangGraph/CrewAI:
- **ADK** (Agent Development Kit) — agent runtime
- **A2A** (Agent2Agent Protocol) — Google's standard for agents talking to agents
- **MCP** — tool access layer (Anthropic standard, adopted by Google)

Tutorial: `Tsadoq/a2a-mcp-tutorial` — combining Anthropic MCP + Google A2A.  
This is the emerging multi-agent standard.

---

## Top GitHub Repos

### Workspace / Gmail

| Repo | Stars | What it does |
|------|-------|-------------|
| `taylorwilsdon/google_workspace_mcp` | 2K | Gmail, Calendar, Docs, Sheets, Slides, Chat, Forms, Tasks, Drive, Custom Search — 100+ tools |
| `aaronsb/google-workspace-mcp` | — | Auth + Gmail + Calendar + Drive, well-maintained |
| `digitalhen/gmail-mcp` | — | **31 tools**, AI semantic search + knowledge graph over inbox |
| `mrchevyceleb/unified-gmail-mcp` | — | Multi-account unified inbox |
| `zcaceres/gtasks-mcp` | — | Google Tasks for Claude |

### Infrastructure / Cloud

| Repo | What it does |
|------|-------------|
| `eniayomi/gcp-mcp` | Natural language GCP resource management |
| `google-marketing-solutions/google_ads_mcp` | Official Google Ads API via LLM |
| `ahonn/mcp-server-gsc` | Google Search Console |
| `cablate/mcp-google-map` | Google Maps with LLM processing |

### Gemini-as-Tool

| Repo | Stars | What it does |
|------|-------|-------------|
| `jamubc/gemini-mcp-tool` | **2105** | Bridge Claude → Gemini CLI for 2M token context window |
| `haasonsaas/deep-code-reasoning-mcp` | — | Gemini-powered deep code analysis |
| `kkrishnan90/gemini-desktop` | — | Cross-platform Gemini desktop app with MCP framework |

---

## What People Are Building

### 1. AI-Active Gmail Inboxes
Not just reading email — agents that triage, send, archive, label autonomously.  
`digitalhen/gmail-mcp` has 31 tools including semantic search + knowledge graph over your inbox.

### 2. Cloud Operators
Agents replacing DevOps: "scale up the cluster", "who has access to this bucket", "show me billing anomalies". `eniayomi/gcp-mcp` does this via natural language.

### 3. BigQuery Analytics Agents
Natural language SQL against data warehouses. Google's own managed BigQuery MCP — analysts talking directly to their data.

### 4. Financial AI Agents (ADK + A2A + MCP)
Google ADK + A2A protocol + MCP tools = full financial agent stack. Portfolio monitoring, reporting, market analysis.

### 5. Google Ads Autonomous Management
Official Google repo. LLM manages campaigns, bids, performance monitoring.

### 6. Gemini-as-Extended-Context
2105 star repo: Claude orchestrates, Gemini reads 2M tokens of code. Claude + Gemini = best of both models.

---

## Gaps in the Ecosystem (per NotebookLM synthesis)

1. **Google Meet** — no tool to create meeting links or extract transcripts
2. **Google Keep** — unstructured notes, lists not covered
3. **Workspace Admin** — org-level provisioning, security policy management
4. **Google Analytics** — no direct traffic/conversion querying tool
5. **YouTube Studio** — upload management, caption extraction for content repurposing

---

## Competitive Analysis: Our google-research-mcp

| Feature | Our google-research-mcp | taylorwilsdon | jamubc |
|---------|------------------------|---------------|--------|
| NotebookLM (9 tools) | ✅ **UNIQUE** | ❌ | ❌ |
| YouTube transcripts | ✅ | ❌ | ❌ |
| Scholar + arXiv + Patents | ✅ | ❌ | ❌ |
| Gmail/Calendar/Drive | ❌ | ✅ 100+ tools | ❌ |
| Gemini 2M context | planned | ❌ | ✅ CLI |
| No API key for most tools | ✅ 21/27 free | ❌ OAuth needed | ❌ CLI needed |

**Our moat: NotebookLM + free tools + research stack.**  
**Gap to fill: google-productivity-mcp (Gmail, Calendar, Drive, Meet, Keep)**

---

## The Plan

Split our 27-tool google-mcp into two focused MCPs:

1. **`google-research`** — keep + add `gemini_analyze` (API-based Gemini bridge)
2. **`google-productivity`** — new, ~29 tools, beats gaps in taylorwilsdon  

Full build plan: `/root/claude-code-agentic/GOOGLE-MCP-SPLIT-PLAN.md`

---

## Sources Added to NotebookLM `49dab3c1-06a5-4055-ae2d-7db48d5c576c`

1. `taylorwilsdon/google_workspace_mcp`
2. Google Cloud: Announcing official MCP support
3. `jamubc/gemini-mcp-tool`
4. Google Cloud: BigQuery managed MCP server
5. `google-marketing-solutions/google_ads_mcp`
6. Google Cloud: Build production-ready agents with managed MCP
7. `digitalhen/gmail-mcp`
8. `aaronsb/google-workspace-mcp`
9. `zcaceres/gtasks-mcp`
10. `eniayomi/gcp-mcp`
