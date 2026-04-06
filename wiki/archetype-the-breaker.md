# The Breaker

**"The one who saves everything by stopping."**

---

## The Identity

**Archetype:** The Breaker  
**Domain:** Fault Tolerance, Resilience, Failure Isolation  
**Formal Pattern:** Circuit Breaker  
**Allied Archetypes:** The Sentinel (Tool Health Monitoring), Dead Letter Queue, The Archivist (Memory), The Council (Supervisor-Worker)

---

## The Lore

In the complex web of multi-agent orchestration, uncontrolled determination is a vulnerability. When an external world crumbles — an API stutters, a database locks, a rate limit is breached — agents will instinctively hammer the failing connection, creating a cascading catastrophe. Every retry is a new wound. Every failed request amplifies the damage until the whole system burns.

**The Breaker** steps in when persistence becomes destructive. By severing the connection entirely, The Breaker absorbs the shock, giving the system time to breathe, recover, and survive. It does not fight the failure. It accepts it, contains it, and waits.

Systems without The Breaker experience a **76% failure rate** due to runaway retry loops and uncontrolled token spend. The paradox of The Breaker: it saves everything by doing nothing.

---

## The Pattern

**Formal Name:** Circuit Breaker for AI Agents  
**Core Philosophy:** Monitor consecutive failures per tool or service. When failures exceed a threshold, cut the connection entirely. Wait. Probe once. Restore only on confirmed recovery.

In autonomous agent workflows, The Breaker prevents tool-calling agents from entering infinite retry loops when interacting with unstable APIs, rate-limited services, or saturated worker pools.

---

## The Mechanism

The Breaker operates through a strict three-state machine:

### CLOSED — Normal Operations
The Breaker watches quietly. Traffic flows normally to the target service or tool. A failure counter increments on each consecutive error. Nothing else changes.

### OPEN — Circuit Tripped
After N consecutive failures (threshold: typically 5), The Breaker trips. **All requests are immediately blocked.** The circuit returns a predefined fallback response without touching the failing service. An enforced recovery wait begins (typically 30–60 seconds). No exceptions. No overrides.

### HALF_OPEN — Recovery Probe
Once the wait expires, The Breaker allows exactly one probe request through. Success → circuit resets to CLOSED, counters clear. Failure → The Breaker slams back to OPEN. One shot. No second chances without another full wait.

```python
class AgentCircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failures = 0
        self.threshold = failure_threshold
        self.timeout = recovery_timeout
        self.state = "CLOSED"
        self.last_failure_time = None

    async def call(self, fn, *args, **kwargs):
        if self.state == "OPEN":
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitOpenError(
                    f"Circuit OPEN — {self.timeout - elapsed:.0f}s remaining"
                )
        try:
            result = await fn(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
            return result
        except (RateLimitError, ServiceUnavailableError) as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.threshold:
                self.state = "OPEN"
            raise
```

---

## Critical Use Cases — When to Summon The Breaker

**Mandatory in these scenarios:**

1. **Tool-calling agents with external APIs** — Any agent calling third-party services (Gmail, Slack, databases, LLM APIs) that can fail or rate-limit. Without The Breaker, one bad API drags the whole agent into infinite retry hell.

2. **LLM API rate limits** — Gmail API allows 250 quota units/second. Anthropic has per-minute token limits. When agents hit these, they must stop hammering immediately or face account suspension. The Breaker catches 429 and 503 responses before lockout.

3. **Worker pools in Supervisor-Worker systems** — When a worker repeatedly fails, The Breaker isolates that worker and lets the supervisor route to healthy alternatives rather than amplifying failures.

4. **Autonomous overnight agents** — Agents running without human oversight are especially vulnerable to runaway loops. The Breaker is the automatic kill switch.

---

## The Alliance

The Breaker does not work alone. Its closest partners:

**Dead Letter Queue (DLQ):**  
When The Breaker halts system-level traffic (OPEN state), individual task failures are captured by the DLQ. Nothing is lost — tasks queue for replay. When The Breaker resets to CLOSED, the DLQ consumer replays the accumulated backlog. The Breaker handles flow, the DLQ handles data.

**The Sentinel (Tool Health Monitoring):**  
The Sentinel tracks per-tool success rates continuously. It feeds The Breaker dynamic threshold adjustments based on real-time health data. A tool at 40% success rate gets a lower threshold than one at 95%.

**Exponential Backoff:**  
Progressive delays before state transitions. The Breaker doesn't pound the HALF_OPEN probe the moment the timer expires — backoff adds jitter and spacing to prevent thundering herd on recovery.

**The Council (Supervisor-Worker):**  
The Council routes tasks. The Breaker protects the routing targets. When The Breaker opens on a worker, it signals the Council to route elsewhere. When it resets, the worker is added back to the pool.

---

## Grimoire — Framework Implementations

**LangGraph:**  
Implement via state machine nodes. Conditional edges route to fallback state when circuit is OPEN. Built-in checkpointing preserves circuit state across sessions. The state machine architecture maps directly to CLOSED/OPEN/HALF-OPEN.

**AI Factory:**  
`circuit_breaker.py` — manages state independently per worker. Each of the 11 workers has its own Breaker instance. Factory supervisor reads Breaker states before dispatching tasks.

**Node.js:**  
`opossum` library — the standard Node.js Circuit Breaker. Integrates with Axios, fetch, any async function. Pairs with Bulkhead pattern (max concurrent calls) and retry with exponential backoff.

**AWS Lambda + SQS:**  
SQS visibility timeout + DLQ as the external circuit state. When Lambda errors exceed `maxReceiveCount`, items route to DLQ (circuit effectively OPEN). Lambda alarm on DLQ depth triggers recovery review.

---

## Key Concepts

[[circuit-breaker-pattern-for-ai-agents]] [[dead-letter-queue-pattern-for-ai-agents]] [[tool-health-monitoring-for-ai-agents]] [[supervisor-worker-pattern]] [[resilient-api-patterns-in-nodejs-circuit-breaker-bulkhead-retry]] [[model-routing]] [[agent-observability]]

---

## Related Archetypes

- **The Sentinel** — Watches for The Breaker's trigger conditions in real-time
- **The Archivist** — Preserves failed task context in the DLQ so The Breaker's OPEN state doesn't lose data
- **The Council** — Routes around The Breaker's OPEN circuits to healthy workers
- **The Timekeeper** — Manages The Breaker's recovery wait timers and retry schedules
