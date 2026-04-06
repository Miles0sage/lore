---
backlinks: []
concepts:
- tail sampling
- grafana lgtm stack
- otlp protocol
- opentelemetry
- auto-instrumentation
- otel collector
- semantic conventions
- manual instrumentation
- observability
confidence: medium
created: '2026-04-05'
domain: ai-agents
id: opentelemetry-in-production-end-to-end-observability-for-microservices-in-2026
sources:
- raw/2026-04-05-opentelemetry-web.md
status: published
title: 'OpenTelemetry in Production: End-to-End Observability for Microservices in
  2026'
updated: '2026-04-05'
---

# OpenTelemetry in Production: End-to-End Observability for Microservices in 2026

OpenTelemetry (OTel) is the universal standard for production observability in 2026. It provides a vendor-neutral, runtime-agnostic framework that is stable across traces, metrics, and logs. This implementation utilizes Grafana's LGTM stack (Loki, Grafana, Tempo, Mimir) for backend storage and visualization.

## The Three Pillars of Observability
* **Traces**: Maps request flow through distributed systems. Pipeline: OTLP traces → Tempo.
* **Metrics**: Tracks aggregated system health over time. Pipeline: OTLP metrics → Mimir/Prometheus.
* **Logs**: Records timestamped event data. Pipeline: OTLP logs → Loki.

The core OTel principle is to instrument once and export to any compatible backend.

## Architecture Overview
```
Your Services (Node/Python/Java/Go)
    ↓ OTLP (gRPC/HTTP)
OTel Collector (sidecar or daemonset)
    ↓ ↓ ↓
  Tempo  Mimir  Loki
    ↓ ↓ ↓
    Grafana (unified UI)
```
The OTel Collector acts as the central routing and transformation layer, receiving telemetry from instrumented services and forwarding it to designated storage backends.

## Collector Configuration

### docker-compose.yml
Deploys the collector alongside the LGTM stack and Grafana (v11.4.0).
```yaml
version: "3.9"
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.115.0
    command: ["--config=/etc/otelcol-contrib/config.yaml"]
    volumes:
      - ./otel-config.yaml:/etc/otelcol-contrib/config.yaml
    ports:
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
      - "8888:8888"    # Collector metrics
      - "8889:8889"    # Prometheus scrape endpoint
    depends_on:
      - tempo
      - loki
      - mimir

  tempo:
    image: grafana/tempo:2.6.0
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo-config.yaml:/etc/tempo.yaml
      - tempo-data:/var/tempo
    ports:
      - "3200:3200"

  loki:
    image: grafana/loki:3.3.0
    command: ["-config.file=/etc/loki/local-config.yaml"]
    volumes:
      - loki-data:/loki
    ports:
      - "3100:3100"

  mimir:
    image: grafana/mimir:2.14.0
    command: ["--config.file=/etc/mimir/mimir.yaml"]
    volumes:
      - ./mimir-config.yaml:/etc/mimir/mimir.yaml
      - mimir-data:/data
    ports:
      - "9009:9009"

  grafana:
    image: grafana/grafana:11.4.0
    environment:
      - GF_FEATURE_TOGGLES_ENABLE=traceqlEditor metricsSummary
    volumes:
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"

volumes:
  tempo-data:
  loki-data:
  mimir-data:
  grafana-data:
```

### otel-config.yaml
Configures receivers, processors (batching, resource enrichment, memory limiting, tail sampling), and exporters.
```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

  # Add resource attributes to all signals
  resource:
    attributes:
      - key: deployment.environment
        value: production
        action: upsert

  # Memory limiter prevents OOM
  memory_limiter:
    check_interval: 1s
    limit_mib: 400
    spike_limit_mib: 100

  # Tail sampling: keep 100% of errors, 10% of success
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors-policy
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow-traces-policy
        type: latency
        latency: { threshold_ms: 1000 }
      - name: sampling-policy
        type: probabilistic
        probabilistic: { sampling_percentage: 10 }

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true

  loki:
    endpoint: http://loki:3100/loki/api/v1/push
    default_labels_enabled:
      exporter: false
      job: true

  prometheusremotewrite:
    endpoint: http://mimir:9009/api/v1/push

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch, tail_sampling]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [prometheusremotewrite]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [loki]
```

## Node.js Instrumentation

### Auto-Instrumentation
Requires zero code changes to business logic. Import the SDK before application startup to automatically trace Express, HTTP, PostgreSQL, Redis, and gRPC.
```typescript
// tracing.ts — import BEFORE anything else
import { NodeSDK } from "@opentelemetry/sdk-node";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-grpc";
import { OTLPMetricExporter } from "@opentelemetry/exporter-metrics-otlp-grpc";
import { OTLPLogExporter } from "@opentelemetry/exporter-logs-otlp-grpc";
import { PeriodicExportingMetricReader } from "@opentelemetry/sdk-metrics";
import { BatchLogRecordProcessor } from "@opentelemetry/sdk-logs";
import { getNodeAutoInstrumentations } from "@opentelemetry/auto-instrumentations-node";
import { Resource } from "@opentelemetry/resources";
import { ATTR_SERVICE_NAME, ATTR_SERVICE_VERSION } from "@opentelemetry/semantic-conventions";

const sdk = new NodeSDK({
  resource: new Resource({
    [ATTR_SERVICE_NAME]: "order-service",
    [ATTR_SERVICE_VERSION]: "2.1.0",
    "deployment.environment": process.env.NODE_ENV ?? "development",
  }),

  traceExporter: new OTLPTraceExporter({
    url: "http://otel-collector:4317",
  }),

  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({
      url: "http://otel-collector:4317",
    }),
    exportIntervalMillis: 10_000,
  }),

  logRecordProcessor: new BatchLogRecordProcessor(
    new OTLPLogExporter({ url: "http://otel-collector:4317" })
  ),

  // Auto-instruments: express, http, pg, redis, grpc, and 40+ more
  instrumentations: [
    getNodeAutoInstrumentations({
      "@opentelemetry/instrumentation-http": {
        ignoreIncomingRequestHook: (req) => req.url === "/health",
      },
      "@opentelemetry/instrumentation-pg": {
        enhancedDatabaseReporting: true, // Include SQL queries in spans
      },
    }),
  ],
});

sdk.start();
process.on("SIGTERM", () => sdk.shutdown());
```
Execution command: `node -r ./tracing.js dist/server.js`

### Manual Instrumentation for Business Logic
Used to capture custom metrics, spans, and events for domain-specific operations.
```typescript
import { trace, metrics, context, propagation } from "@opentelemetry/api";

const tracer = trace.getTracer("order-service");
const meter = metrics.getMeter("order-service");

// Custom metrics
const orderCounter = meter.createCounter("orders.created", {
  description: "Number of orders created",
  unit: "{order}",
});

const processingTime = meter.createHistogram("order.processing.duration", {
  description: "Time to process an order",
  unit: "ms",
});

export async function processOrder(orderId: string, items: OrderItem[]) {
  // Create a custom span
  return tracer.startActiveSpan("processOrder", async (span) => {
    try {
      // Add semantic attributes
      span.setAttribute("order.id", orderId);
      span.setAttribute("order.item_count", items.length);
      span.setAttribute("order.total_value", calculateTotal(items));

      const start = performance.now();

      // Validate inventory
      span.addEvent("inventory_check_started");
      await checkInventory(items);
      span.addEvent("inventory_check_completed");

      // Create order in DB
      const order = await db.orders.create({ orderId, items });

      // Record metrics
      // [... truncated 6301 chars ...]
```

## Key Concepts
[[OpenTelemetry]]
[[Observability]]
[[OTLP Protocol]]
[[Grafana LGTM Stack]]
[[OTel Collector]]
[[Tail Sampling]]
[[Auto-Instrumentation]]
[[Manual Instrumentation]]
[[Semantic Conventions]]

## Sources
* `2026-04-05-opentelemetry-web.md`
