---
backlinks: []
concepts:
- api observability
- node.js microservices
- bulkhead pattern
- retry with exponential backoff
- opossum
- circuit breaker pattern
- idempotent operations
- cascading failure prevention
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: resilient-api-patterns-in-nodejs-circuit-breaker-bulkhead-retry
sources:
- raw/2026-04-05-circuit-breaker-pattern-web.md
status: published
title: Resilient API Patterns in Node.js (Circuit Breaker, Bulkhead, Retry)
updated: '2026-04-05'
---

# Resilient API Patterns in Node.js (Circuit Breaker, Bulkhead, Retry)

## Overview
Modern distributed systems require resilience patterns to prevent cascading failures caused by network glitches, slow databases, or third-party API latency. In 2026, production Node.js architectures frequently depend on external AI APIs (OpenAI, Anthropic, Gemini), payment gateways (99.9% SLA, equating to ~8.7 hours downtime/year), internal microservices, and databases. Without fault tolerance, a single slow dependency can exhaust thread, queue, or connection pools, causing full service outages.

## Circuit Breaker Pattern
Popularized by Michael Nygard's *Release It!*, the circuit breaker stops requests to failing services once a failure threshold is exceeded, returning an immediate fallback instead of waiting for timeouts.

### State Transitions
- **CLOSED**: Normal operation. Requests flow through; failures are counted.
- **OPEN**: Circuit tripped. All requests immediately return a fallback; no traffic reaches the failing service.
- **HALF-OPEN**: After a reset timeout, a single probe request is allowed. Success closes the circuit; failure reopens it.

Transition flow: `CLOSED → (failures > threshold) → OPEN → (reset timeout) → HALF-OPEN → (success) → CLOSED` or `↘ (failure) → OPEN`

### Opossum 9.x Implementation
Opossum 9.0.0 (released June 2025) requires Node.js ≥ 20 and aligns with the WHATWG Fetch API.

Installation:
```bash
npm install opossum@9
npm install -D @types/opossum
```

Core wrapper configuration:
```javascript
// lib/circuit-breaker.js
import CircuitBreaker from 'opossum';
/**
 * Wraps an async function with a circuit breaker.
 * @param {Function} fn - The async function to protect
 * @param {Object} options - Opossum options
 */
export function createBreaker(fn, options = {}) {
  const defaults = {
    timeout: 5000,                  // Fail if takes > 5s
    errorThresholdPercentage: 50,   // Trip at 50% failure rate
    resetTimeout: 30000,            // Try again after 30s
    volumeThreshold: 5,             // Min 5 requests before tripping
    rollingCountTimeout: 10000,     // Measure over a 10s window
  };

const breaker = new CircuitBreaker(fn, { ...defaults, ...options });

// Observability hooks
  breaker.on('open',     () => console.warn([CircuitBreaker] OPEN — ${fn.name}));
  breaker.on('halfOpen', () => console.info([CircuitBreaker] HALF-OPEN — ${fn.name}));
  breaker.on('close',    () => console.info([CircuitBreaker] CLOSED — ${fn.name}));
  breaker.on('fallback', (result) => console.warn([CircuitBreaker] FALLBACK — ${fn.name}:, result));

return breaker;
}
```

Service integration with fallback:
```javascript
// services/payment.service.js
import { createBreaker } from '../lib/circuit-breaker.js';
async function chargeCard(payload) {
  const response = await fetch('https://api.payment-provider.com/v1/charge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(4500), // Hard abort at 4.5s
  });

if (!response.ok) {
    throw new Error(Payment API error: ${response.status});
  }

return response.json();
}

// Fallback: queue for async retry
function paymentFallback(payload) {
  console.warn('Payment service unavailable — queuing for retry:', payload.orderId);
  return { queued: true, orderId: payload.orderId, retryAt: Date.now() + 60_000 };
}

const paymentBreaker = createBreaker(chargeCard, {
  timeout: 4000,
  errorThresholdPercentage: 30, // Payment APIs: trip faster
  resetTimeout: 60000,           // Try again after 60s
});

paymentBreaker.fallback(paymentFallback);

export { paymentBreaker };
```

Route handler usage:
```javascript
// routes/orders.js
import { paymentBreaker } from '../services/payment.service.js';
app.post('/orders', async (req, res) => {
  try {
    const result = await paymentBreaker.fire({
      orderId: req.body.orderId,
      amount: req.body.amount,
      currency: req.body.currency,
    });

if (result.queued) {
      return res.status(202).json({
        message: 'Order accepted, payment will process shortly',
        orderId: result.orderId,
      });
    }

res.json({ success: true, transactionId: result.transactionId });
  } catch (err) {
    // Only reaches here if no fallback is set
    res.status(503).json({ error: 'Service temporarily unavailable' });
  }
});
```

## Retry with Exponential Backoff
The retry pattern automatically re-attempts failed requests. Exponential backoff spaces retries with increasing delays to prevent thundering herds.

### Implementation Rules
- Only retry idempotent operations (GET, PUT, DELETE are safe; POST requires caution).
- Add jitter to randomize backoff and prevent synchronized retry storms.
- Set a maximum retry count.
- Respect `Retry-After` headers from external APIs.

### Manual Implementation
```javascript
// lib/retry.js
/**
 * Retry an async function with exponential backoff + jitter
 * @param {Function} fn - Async function to retry
 * @param {Object} opts - Retry configuration
 */
export async function withRetry(fn, opts = {}) {
  const {
    maxAttempts = 3,
    baseDelayMs = 200,
    maxDelayMs = 10_000,
    jitter = true,
    shouldRetry = (err) => true, // Custom predicate
  } = opts;

let lastError;

for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;

// Don't retry on the last attempt
```

## Observability & Health Checks
Circuit breaker state and metrics can be exposed via health endpoints for monitoring pipelines (Prometheus, OpenTelemetry).

```javascript
// GET /health/circuit-breakers
app.get('/health/circuit-breakers', (req, res) => {
  res.json({
    payment: {
      state: paymentBreaker.opened ? 'OPEN' : paymentBreaker.halfOpen ? 'HALF_OPEN' : 'CLOSED',
      stats: paymentBreaker.stats,
    },
  });
});
```
The `stats` object tracks `fires`, `successes`, `failures`, `rejects`, `timeouts`, `fallbacks`, and latency `percentiles`.

## Key Concepts
[[Circuit Breaker Pattern]]
[[Bulkhead Pattern]]
[[Retry with Exponential Backoff]]
[[Opossum]]
[[Cascading Failure Prevention]]
[[Idempotent Operations]]
[[API Observability]]
[[Node.js Microservices]]

## Sources
- [How to Build Resilient APIs with Circuit Breaker, Bulkhead & Retry Patterns in Node.js (2026 Guide)](https://1xapi.com/blog) (Mar 17, 2026)
- [Opossum 9.x Package](https://www.npmjs.com/package/opossum)
