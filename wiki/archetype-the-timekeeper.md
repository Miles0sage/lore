# The Timekeeper

**"The one who decides when — so agents don't have to."**

---

## The Identity

**Archetype:** The Timekeeper  
**Domain:** Scheduled Agents, Temporal Triggers, Polling Loops, Cron Patterns  
**Formal Pattern:** Temporal Orchestration  
**Allied Archetypes:** The Council (Supervisor-Worker), The Breaker (Circuit Breaker), The Sentinel (Observability), The Warden (Safety)

---

## The Lore

Most agents wait to be asked. They sit idle until a human types a message, clicks a button, sends a webhook. They are reactive — powerful but passive.

The Timekeeper breaks this. It is the architect of autonomous initiative. While the rest of the system sleeps, The Timekeeper watches the clock, watches the state of the world, and at the precise moment — fires.

Morning briefings at 7am. Inbox triage every 5 minutes. Nightly research summaries. The Timekeeper doesn't need a human to say "go." It already knows when.

Without The Timekeeper, agents are tools. With it, agents become autonomous systems.

---

## The Pattern

**Formal Name:** Temporal Orchestration  
**Core Philosophy:** Agents should not wait for human prompts to perform routine tasks. Time-based and state-based triggers make agents proactive. The Timekeeper defines the *when* of autonomous action — separating task scheduling from task execution so both can be optimized independently.

---

## The Mechanism

Three trigger types govern when agents fire:

### 1. Cron Triggers — Clock-Based

The simplest form. Fire at a fixed schedule, regardless of system state.

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio

scheduler = AsyncIOScheduler()

# Morning briefing — 7am daily
@scheduler.scheduled_job('cron', hour=7, minute=0)
async def morning_briefing():
    result = await segundo.run("Generate today's briefing: news, calendar, tasks")
    await telegram.send(result)

# Inbox triage — every 5 minutes
@scheduler.scheduled_job('interval', minutes=5)
async def inbox_triage():
    emails = await gmail.fetch_new()
    for email in emails:
        await triage_agent.classify_and_route(email)

# Nightly research digest — 10pm
@scheduler.scheduled_job('cron', hour=22, minute=0)
async def nightly_digest():
    digest = await research_agent.compile_daily_learnings()
    await telegram.send(digest)

scheduler.start()
asyncio.get_event_loop().run_forever()
```

**Cloudflare Workers Cron Triggers:**
```toml
# wrangler.toml
[triggers]
crons = ["0 7 * * *", "*/5 * * * *", "0 22 * * *"]
```

```typescript
export default {
  async scheduled(event: ScheduledEvent, env: Env): Promise<void> {
    switch (event.cron) {
      case "0 7 * * *":
        await morningBriefing(env);
        break;
      case "*/5 * * * *":
        await inboxTriage(env);
        break;
      case "0 22 * * *":
        await nightlyDigest(env);
        break;
    }
  }
}
```

### 2. Polling Loops — State-Based

The agent polls a data source continuously, triggering when new state is detected. Slower than webhooks but works with any data source.

```python
# VIGIL-style polling loop — the canonical pattern
import asyncio
import time

POLL_INTERVAL = 10  # seconds

async def poll_task_queue():
    """Core VIGIL pattern: poll Supabase for new tasks"""
    while True:
        try:
            # Check for pending tasks
            tasks = await supabase.get("tasks", {"status": "eq.pending"})
            for task in tasks:
                # Claim the task (prevent double-execution)
                claimed = await supabase.patch(
                    f"tasks?id=eq.{task['id']}",
                    {"status": "in_progress", "claimed_at": time.time()}
                )
                if claimed:
                    asyncio.create_task(execute_task(task))
            
            # Check for triggers
            triggers = await supabase.get("vigil_triggers", {"status": "eq.pending"})
            for trigger in triggers:
                task = trigger_to_task(trigger)
                await supabase.post("tasks", task)
                await supabase.patch(
                    f"vigil_triggers?id=eq.{trigger['id']}",
                    {"status": "done"}
                )
                
        except Exception as e:
            log.error(f"Poll loop error: {e}")
            # Don't die — keep polling
        
        await asyncio.sleep(POLL_INTERVAL)

async def execute_task(task):
    """Execute a claimed task with circuit breaker protection"""
    try:
        result = await agent.run(task['prompt'])
        await supabase.patch(
            f"tasks?id=eq.{task['id']}",
            {"status": "done", "result": result, "completed_at": time.time()}
        )
        # Notify if result needs human review
        if task.get('notify_on_complete'):
            await telegram.send(f"Task complete: {task['title']}\n{result[:500]}")
    except Exception as e:
        await supabase.patch(
            f"tasks?id=eq.{task['id']}",
            {"status": "failed", "error": str(e)}
        )
```

### 3. Event / Webhook Triggers — Reactive Temporal

External events fire the agent immediately. The Timekeeper registers for these events and dispatches execution.

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Telegram sends messages here — Segundo's entry point"""
    body = await request.json()
    message = body.get("message", {})
    text = message.get("text", "")
    chat_id = message["chat"]["id"]
    
    # Dispatch to agent asynchronously
    asyncio.create_task(segundo.handle_message(text, chat_id))
    return {"ok": True}

@app.post("/webhook/github")
async def github_webhook(request: Request):
    """Fire code review agent on PR open"""
    body = await request.json()
    if body.get("action") == "opened":
        pr = body["pull_request"]
        asyncio.create_task(review_agent.review_pr(pr["url"]))
    return {"ok": True}
```

---

## The Temporal Orchestration Stack

Full production stack for a proactive agent system:

```
TIMEKEEPER LAYER
├── Cron (wrangler.toml / APScheduler / GitHub Actions cron)
│     └── Fires: morning briefing, nightly digest, weekly reports
├── Polling Loop (VIGIL pattern — 10s interval)
│     └── Fires: new tasks in queue, trigger events, state changes
└── Webhooks (Telegram, GitHub, Stripe, etc.)
      └── Fires: immediately on external event

EXECUTION LAYER (The Council dispatches)
├── Quick tasks → inline execution in worker
├── Long tasks → enqueue in task queue → VIGIL worker picks up
└── Failed tasks → Dead Letter Queue → The Breaker protects

NOTIFICATION LAYER
└── Results → Telegram message → human informed, not interrupted
```

---

## Critical Use Cases — When to Summon The Timekeeper

1. **Personal AI assistants (Segundo pattern)** — Morning briefings, evening summaries, reminder nudges, inbox triage. The assistant becomes proactive without the human asking.

2. **VIGIL autonomous worker loops** — Long-running tasks (research, builds, code review) dispatched by humans, executed autonomously by VIGIL polling the task queue.

3. **Market/data monitoring** — Check Polymarket odds every hour. Alert when a position moves more than 5%. The Timekeeper fires, the scout fetches, the human decides.

4. **Health checks and keepalives** — Cookie sessions die. Services go down. Cron pings keepalives every 30 minutes before session expiry.

5. **Automated reporting** — Weekly expense summaries, GitHub activity digests, research roundups. The Timekeeper fires at the end of each period, agents compile, human receives.

---

## Failure Modes — What Happens Without The Timekeeper

- **Missed opportunities** — Market moved while the human was sleeping. The agent would have caught it if it was watching.
- **Stale sessions** — Twitter cookies expired at 3am. No keepalive cron. The morning briefing fails silently.
- **Task queue deadlock** — Tasks pile up in the queue with no polling loop to claim them. Work sits undone.
- **Human bottleneck** — Every agent action requires a human prompt. The agent is powerful but passive — a tool, not a system.

---

## The Alliance

**The Council (Supervisor-Worker):**  
The Timekeeper fires the supervisor. The supervisor dispatches workers. Temporal orchestration is the trigger layer sitting above the entire Supervisor-Worker stack.

**The Breaker (Circuit Breaker):**  
Polling loops can hammer failing services. The Breaker wraps every outbound call inside The Timekeeper's loops. If Supabase is down, the polling loop keeps running but the Breaker stops hammering.

**The Sentinel (Observability):**  
The Sentinel monitors cron job execution: did the 7am briefing fire? Did it succeed? Missed cron detection is a key alert class. LangSmith, Langfuse, and custom dashboards track Timekeeper execution.

**The Warden (Safety):**  
Autonomous agents firing on cron need guardrails. The Warden ensures scheduled agents don't take irreversible actions (send emails, make trades, delete data) without confirmation thresholds.

---

## Grimoire — Framework Implementations

**APScheduler (Python):**  
`AsyncIOScheduler` for async agents. `cron`, `interval`, and `date` job types. Persistent job store (SQLAlchemy) survives restarts. The standard for VPS-deployed Python agents.

**Cloudflare Workers Cron:**  
Native cron triggers in `wrangler.toml`. Zero infrastructure — Workers handles the scheduling. Ideal for Segundo-style CF Workers agents. Fires the `scheduled()` handler.

**GitHub Actions:**  
```yaml
on:
  schedule:
    - cron: '0 7 * * *'  # 7am UTC daily
```
Free for public repos. Good for research and reporting agents tied to code repos.

**Celery Beat:**  
Celery's scheduler. Combines with Celery workers for distributed task execution. Overkill for single-server setups; right tool for multi-worker systems.

**NSSM + Windows Task Scheduler:**  
For Windows bastion deployments (VIGIL Windows). NSSM wraps Python scripts as Windows services. Task Scheduler fires time-based triggers. The Timekeeper runs on Windows.

---

## Key Concepts

[[supervisor-worker-pattern]] [[circuit-breaker-pattern-for-ai-agents]] [[dead-letter-queue-pattern-for-ai-agents]] [[agent-observability]] [[agentic-coding]]

---

## Related Archetypes

- **The Council** — The Timekeeper triggers The Council to start orchestrating
- **The Breaker** — Protects The Timekeeper's polling loops from hammering failing services
- **The Sentinel** — Monitors whether The Timekeeper's scheduled jobs are actually firing
- **The Warden** — Ensures autonomous scheduled actions don't cause irreversible harm
