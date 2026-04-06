---
backlinks: []
concepts:
- deployment
- docker
- kubernetes
- sidecar-agent
- stateless-worker
- long-running-daemon
- health-monitoring
- zero-downtime-deploy
- configuration-discipline
confidence: high
created: '2026-04-05'
domain: ai-agents
id: deployment-patterns-for-production-ai-agents
sources: []
status: published
title: Deployment Patterns for Production AI Agents
updated: '2026-04-06'
---

# Deployment Patterns for Production AI Agents

## Overview

Deploying an AI agent is not the same as deploying a web service. Agents carry ambient state, make expensive external calls, can loop indefinitely, and escalate costs silently when they fail. This article covers the three core deployment models, configuration discipline, and the operational runbook for running agents in production without surprises.

## The Three Deployment Models

### 1. Stateless Worker (recommended default)

The agent is a pure function: receive task → produce output → exit. No persistent state between invocations. All state lives in an external store (Redis, Supabase, S3).

```
 Queue / API
     │
     ▼
┌─────────────┐   spawn   ┌─────────────┐
│  Supervisor  │ ─────────▶│   Worker    │ → output → store
└─────────────┘           └─────────────┘
                           exits on completion
```

**Why this is safest:** No ambient state to corrupt. Workers can be scaled horizontally. Failures don't affect other workers. Dead workers leave no ghost state.

```dockerfile
# Dockerfile — stateless worker
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir
COPY . .
# No CMD — caller passes task as env var or stdin
ENTRYPOINT ["python", "-m", "lore.worker"]
```

```python
# worker.py — stateless pattern
import os
import sys

def main():
    task = os.environ.get("TASK_PAYLOAD") or sys.stdin.read()
    result = process(task)
    # write result to external store, not local state
    store.put(result)
    sys.exit(0)   # clean exit always
```

### 2. Sidecar Agent

The agent runs alongside the main application, sharing its network namespace but not its filesystem or credentials. Best for agents that augment an existing service.

```
┌──────────────────────────────┐
│          Pod / VM            │
│  ┌────────────┐  ┌─────────┐ │
│  │  Main App  │  │  Agent  │ │
│  │  :8080     │◀─│  :8081  │ │
│  └────────────┘  └─────────┘ │
└──────────────────────────────┘
     shared localhost network
     separate credentials
```

```yaml
# docker-compose.yml — sidecar pattern
version: "3.9"
services:
  app:
    image: myapp:latest
    ports: ["8080:8080"]
    networks: [internal]

  agent:
    image: lore-agent:latest
    environment:
      - APP_ENDPOINT=http://app:8080
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on: [app]
    networks: [internal]
    restart: unless-stopped

networks:
  internal:
```

### 3. Long-Running Daemon

The agent maintains a persistent event loop and processes tasks from a queue. Requires explicit state management, heartbeat monitoring, and graceful shutdown.

Use the [[timekeeper-scheduling-pattern]] KAIROS loop: **Check → Act → Rest**.

```python
# daemon.py — long-running pattern
import asyncio
import signal
from datetime import datetime

class AgentDaemon:
    def __init__(self, interval_s: int = 1800):
        self.interval = interval_s
        self._shutdown = False
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "_shutdown", True))
        signal.signal(signal.SIGINT, lambda *_: setattr(self, "_shutdown", True))

    async def run(self):
        print(f"Daemon started at {datetime.utcnow().isoformat()}")
        while not self._shutdown:
            cycle_start = asyncio.get_event_loop().time()
            try:
                await self.cycle()
            except Exception as exc:
                print(f"Cycle error: {exc}")  # never crash the daemon
            elapsed = asyncio.get_event_loop().time() - cycle_start
            sleep = max(0, self.interval - elapsed)
            if not self._shutdown:
                await asyncio.sleep(sleep)
        print("Daemon stopped cleanly.")

    async def cycle(self):
        raise NotImplementedError
```

## Configuration Discipline

Agents should receive configuration through a **narrow, explicit interface**.

### What goes where

| Config type | Where it lives | Why |
|---|---|---|
| API keys, tokens | Environment variables | Never baked into images |
| Operational params (intervals, limits) | Single config object at startup | Discoverable, no filesystem crawl |
| Feature flags | Separate env vars | Change behaviour without credential rotation |
| Model routing rules | `.lore/routing_rules.json` | Operator-editable, not hardcoded |

```python
# config.py — explicit config contract
from dataclasses import dataclass
import os

@dataclass
class AgentConfig:
    openai_api_key: str
    deepseek_api_key: str
    cycle_interval_s: int
    daily_budget_usd: float
    log_level: str

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            deepseek_api_key=os.environ["DEEPSEEK_API_KEY"],
            cycle_interval_s=int(os.environ.get("CYCLE_INTERVAL_S", "1800")),
            daily_budget_usd=float(os.environ.get("DAILY_BUDGET_USD", "1.0")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )
```

Call `AgentConfig.from_env()` once at startup. Pass the config object everywhere. Never call `os.environ` inside business logic.

## Health and Observability

Every production agent needs a minimal health surface:

```python
# health.py
from aiohttp import web
import time

_start_time = time.time()
_last_cycle: float | None = None
_cycle_count = 0
_total_cost_usd = 0.0

async def health_handler(request):
    now = time.time()
    return web.json_response({
        "status": "ok",
        "uptime_s": int(now - _start_time),
        "last_cycle_s_ago": int(now - _last_cycle) if _last_cycle else None,
        "cycle_count": _cycle_count,
        "total_cost_usd": round(_total_cost_usd, 4),
    })

app = web.Application()
app.router.add_get("/health", health_handler)
```

**Minimum alert signals:**
- No heartbeat for >2× expected interval → page
- DLQ depth >10 → investigate
- Cost counter >daily budget → hard stop
- Worker exit code ≠ 0 → retry, then alert

## Docker Compose (Full Stack)

```yaml
# docker-compose.yml — full LORE deployment
version: "3.9"

services:
  lore-mcp:
    build: .
    image: lore-agents:latest
    ports: ["8080:8080"]
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - LORE_MODE=public
    volumes:
      - lore-wiki:/app/wiki:ro
      - lore-state:/app/.lore
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  lore-daemon:
    image: lore-agents:latest
    command: python3 scripts/lore_research_daemon.py
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - CYCLE_INTERVAL_S=1800
      - DAILY_BUDGET_USD=0.50
    volumes:
      - lore-wiki:/app/wiki
      - lore-state:/app/.lore
    restart: unless-stopped
    depends_on:
      lore-mcp:
        condition: service_healthy

volumes:
  lore-wiki:
  lore-state:
```

## Kubernetes (Production Scale)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lore-mcp
spec:
  replicas: 2
  selector:
    matchLabels: {app: lore-mcp}
  template:
    metadata:
      labels: {app: lore-mcp}
    spec:
      containers:
        - name: lore-mcp
          image: lore-agents:1.0.0
          ports: [{containerPort: 8080}]
          env:
            - name: OPENAI_API_KEY
              valueFrom:
                secretKeyRef:
                  name: lore-secrets
                  key: openai-api-key
            - name: DEEPSEEK_API_KEY
              valueFrom:
                secretKeyRef:
                  name: lore-secrets
                  key: deepseek-api-key
          livenessProbe:
            httpGet: {path: /health, port: 8080}
            initialDelaySeconds: 10
            periodSeconds: 30
          resources:
            requests: {memory: "256Mi", cpu: "100m"}
            limits: {memory: "512Mi", cpu: "500m"}
---
# k8s/secrets.yaml (populate with kubectl create secret)
apiVersion: v1
kind: Secret
metadata:
  name: lore-secrets
type: Opaque
# kubectl create secret generic lore-secrets \
#   --from-literal=openai-api-key=sk-... \
#   --from-literal=deepseek-api-key=sk-...
```

## Zero-Downtime Deployment

```bash
# Rolling update (Kubernetes)
kubectl set image deployment/lore-mcp lore-mcp=lore-agents:1.0.1
kubectl rollout status deployment/lore-mcp

# Rollback if health checks fail
kubectl rollout undo deployment/lore-mcp
```

For daemons: drain the queue before upgrading.

```python
# graceful drain before restart
async def drain(timeout_s: int = 60):
    deadline = time.monotonic() + timeout_s
    while queue.depth() > 0 and time.monotonic() < deadline:
        await asyncio.sleep(5)
    if queue.depth() > 0:
        print(f"Warning: {queue.depth()} tasks still in queue at shutdown")
```

## Deployment Anti-Patterns

| Anti-pattern | What breaks | Fix |
|---|---|---|
| **Fat credential bundle** | Agent has all keys "just in case" | Least-privilege: one key per integration |
| **Shared mutable filesystem** | Two agents corrupt the same file | Use external store + advisory locks |
| **Unbounded retry loop** | No circuit breaker, burns budget | [[circuit-breaker-pattern-for-ai-agents]] |
| **Silent cost escalation** | Failures auto-upgrade to expensive models | Cost ceiling + alert, not auto-escalation |
| **Secrets baked into image** | Keys leak in Docker Hub history | Always environment variables |
| **No health endpoint** | Orchestrator can't detect dead workers | Every long-running process needs `/health` |
| **Restart=always without backoff** | Crash loop burns API quota | Use `restart: on-failure` with delay |

## Deployment Runbook

```
New deploy:
  1. Build image with pinned dependencies
  2. Run tests in CI (not just unit — integration too)
  3. Push to registry with version tag (never :latest in prod)
  4. Deploy to staging, verify /health returns ok
  5. Run smoke test: one full cycle, check cost counter
  6. Rolling deploy to prod
  7. Monitor DLQ depth for 2× cycle interval

Rollback:
  1. kubectl rollout undo OR docker-compose pull <previous-tag>
  2. Verify /health on previous version
  3. Check for state corruption (queue, wiki, .lore/)
  4. File postmortem within 24h

Scaling:
  - MCP server: horizontal scale freely (stateless)
  - Research daemon: single instance only (uses global state)
  - Workers: scale on queue depth (target <10 pending)
```

## Related Patterns

- [[circuit-breaker-pattern-for-ai-agents]] — prevent runaway API calls
- [[dead-letter-queue-pattern-for-ai-agents]] — capture failed tasks
- [[timekeeper-scheduling-pattern]] — KAIROS loop, scheduled jobs
- [[archetype-the-warden]] — credential and permission management
- [[sentinel-observability-pattern]] — structured logging and metrics

## Key Concepts

[[deployment]]
[[docker]]
[[kubernetes]]
[[stateless-worker]]
[[long-running-daemon]]
[[health-monitoring]]
[[configuration-discipline]]
[[zero-downtime-deploy]]
