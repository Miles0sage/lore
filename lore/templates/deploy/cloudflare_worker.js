// LORE DEPLOY: cloudflare_worker
// Stateful AI agent on Cloudflare edge using Durable Objects

// --- wrangler.toml (place alongside this file) ---
// name = "agent-worker"
// main = "src/index.js"
// compatibility_date = "2024-01-01"
//
// [durable_objects]
// bindings = [{ name = "AGENT_SESSION", class_name = "AgentSession" }]
//
// [[migrations]]
// tag = "v1"
// new_classes = ["AgentSession"]
//
// [vars]
// ENVIRONMENT = "production"
//
// [[kv_namespaces]]
// binding = "SHARED_STATE"
// id = "your-kv-namespace-id"

export class AgentSession {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.history = [];
  }

  async fetch(request) {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return new Response(JSON.stringify({ status: "ok" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    if (request.method === "POST" && url.pathname === "/message") {
      const { message } = await request.json();

      // Load persisted state
      const stored = await this.state.storage.get("history");
      if (stored) {
        this.history = stored;
      }

      // Process message (replace with your agent logic)
      const response = {
        role: "assistant",
        content: `Processed: ${message}`,
        timestamp: Date.now(),
      };

      // Persist state
      this.history.push({ role: "user", content: message });
      this.history.push(response);
      await this.state.storage.put("history", this.history);

      return new Response(JSON.stringify(response), {
        headers: { "Content-Type": "application/json" },
      });
    }

    if (request.method === "GET" && url.pathname === "/history") {
      const stored = await this.state.storage.get("history");
      return new Response(JSON.stringify(stored || []), {
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response("Not Found", { status: 404 });
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Health check at worker level
    if (url.pathname === "/health") {
      return new Response(JSON.stringify({ status: "ok", worker: true }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // Route to session Durable Object
    const sessionId = url.searchParams.get("session") || "default";
    const id = env.AGENT_SESSION.idFromName(sessionId);
    const session = env.AGENT_SESSION.get(id);

    // Read from KV for shared state
    if (url.pathname === "/shared") {
      const value = await env.SHARED_STATE.get("config");
      return new Response(value || "{}", {
        headers: { "Content-Type": "application/json" },
      });
    }

    return session.fetch(request);
  },
};
