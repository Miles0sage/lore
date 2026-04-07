# Lore Hardening Plan — Circuit Breaker, DLQ, Observability, Memory 2026-04-06

## Four-Module Hardening Plan (Opus Architecture)

### Reusable Assets Identified

- `ai-factory/circuit_breaker.py` — async CB with CLOSED/OPEN/HALF_OPEN, fully tested → direct extract
- `ai-factory/health_monitor.py` — ErrorClassifier + StuckDetector → extract for DLQ classification
- `openclaw/agent_sessions.py` — three-layer memory (WorkingMemory, EpisodicMemory, ProceduralMemory) → direct copy
- `openclaw/semantic_memory.py` — Gemini embeddings + TF-IDF fallback, no external vector DB → extract
- `openclaw/error_recovery.py` — JSON-persisted circuit state → persistence pattern
- `mantis/trace_store.py` — structured tracing (model, provider, job_id, stats) → adapt for observability

### Module 1: lore/circuit_breaker.py (~350 lines)

Replaces inline circuit breaker in dispatch.py:48-74

Key classes:
- `CircuitState` enum: CLOSED, OPEN, HALF_OPEN
- `CircuitConfig` (frozen dataclass): per-tool failure_threshold, recovery_wait_seconds, half_open_max_probes
- `CircuitSnapshot` (frozen): immutable point-in-time state
- `CircuitMetric` (frozen): emitted on every transition (breaker_opened/closed/probe_sent)
- `CachedFallback`: cached response returned when breaker OPEN
- `SqliteCircuitStore`: SQLite-backed (default, zero-dep)
- `InMemoryCircuitStore`: for tests
- `RedisCircuitStore`: optional multi-worker
- `CircuitBreakerEngine`: manages all breakers, emits metrics, handles HALF_OPEN probing

Integration: dispatch.py removes 5 inline functions, adds lazy import, delegates to engine.

### Module 2: lore/dlq.py (~380 lines)

New module — dead letter queue.

Key classes:
- `FailureClass` enum: TRANSIENT (network/timeout/429), PERMANENT (schema/auth), AMBIGUOUS (LLM hallucination/unknown)
- `DLQEntry` (frozen): entry_id, task_type, prompt_hash, failure_class, error_message, attempt_count, expires_at, status, original_payload
- `DLQStats`: total, pending, by_failure_class, by_task_type, alert (True when pending > 50)
- `DLQStore`: SQLite-backed with per-task-type queues, TTL 7-30 days, depth alerting
- `DLQConsumer`: out-of-band replay with liveness monitoring

SQLite schema: dlq_entries table with indexes on status, task_type, prompt_hash.

Integration: dispatch.py exception handler enqueues failures after circuit breaker records them.

### Module 3: lore/observability.py (~370 lines)

Key classes:
- `ErrorEnvelope` (frozen): task_id, error_type, stack_trace, timestamp, worker_id, attempt_count, model, latency_s, context_tokens_used
- `ToolCallVerifier`: validates HTTP status, non-empty response, schema compliance
- `TokenBudget`: tracks per-step usage, warns at 80% (15-20% remaining)
- `ObservabilityHub`: central coordinator — emit_error(), emit_metric(), verify_and_log(), record_tokens(), optional OTel export

Telemetry: observability.jsonl + circuit_metrics.jsonl

Integration: dispatch.py success path calls record_tokens() + verify_and_log(); exception path calls emit_error().

### Module 4: lore/memory.py (~390 lines)

Three-layer stack:
- `WorkingMemory`: in-process buffer, max 50 entries, compact at 40 (evicts to episodic)
- `EpisodicMemory`: SQLite-backed, searchable by session/pattern/date
- `ProceduralMemory`: SOUL.md file, key-value rules (## key\nvalue format)
- `MemoryRouter`: auto-routes writes (short → working, rule keywords → procedural, else → episodic); merges reads across all layers; checkpoint/restore at context boundaries

SOUL.md format: human-readable, git-friendly, editable.

### Modified Files

- `dispatch.py`: remove 5 inline CB functions, add lazy imports for dlq/observability, wire hooks
- `config.py`: add 6 path helpers (get_dlq_db_path, get_circuit_db_path, get_memory_db_path, get_soul_path, get_observability_log_path, get_circuit_metrics_log_path)
- `server.py`: add 10 new MCP tools (lore_dlq_status, lore_dlq_list, lore_dlq_replay, lore_dlq_resolve, lore_observability, lore_token_budget, lore_memory_write, lore_memory_read, lore_memory_status, lore_memory_checkpoint)

### Implementation Order

1. circuit_breaker.py + tests (foundation)
2. config.py path helpers (needed by all)
3. Wire circuit_breaker into dispatch.py (backward compat test)
4. dlq.py + tests, then wire into dispatch.py
5. observability.py + tests, then wire into dispatch.py
6. memory.py + tests (most independent)
7. server.py new tools (final integration)

### Key Decisions

- SQLite default (zero-dep, fits dependencies = [])
- Separate DBs per module (independence, no cross-contamination)
- Redis optional (RedisCircuitStore lazy import)
- No required vector DB (TF-IDF fallback from openclaw pattern)
- SOUL.md for procedural memory (human-readable, git-friendly)