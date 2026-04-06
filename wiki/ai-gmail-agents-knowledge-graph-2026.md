# AI Gmail Agents — Knowledge Graph + Semantic Inbox (2026)

**Date:** 2026-04-05  
**Sources:** digitalhen/gmail-mcp, taylorwilsdon/google_workspace_mcp, NotebookLM synthesis, aaronsb/google-workspace-mcp

---

## The Problem: Email as Unstructured Graph

Email inboxes are not flat lists — they are relationship graphs. Sender → thread → topic → decision → follow-up. Treating email as a search corpus misses the structure. The state of the art in 2026 is building a **knowledge graph over the inbox**, not just indexing it.

`digitalhen/gmail-mcp` (31 tools) is the reference implementation: semantic search + AI knowledge graph extracted from email content.

---

## Architecture: Three Layers Over Gmail

### Layer 1 — OAuth 2.1 + Gmail API Access

All serious Gmail agents use OAuth 2.1 with:
- `credentials.json` from Google Cloud Console (downloaded once)
- `token.json` auto-refreshed via `google-auth-oauthlib`
- Scopes: `gmail.readonly`, `gmail.send`, `gmail.modify`, `gmail.labels`
- Incremental sync via `historyId` — don't re-fetch the whole inbox

```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)
```

### Layer 2 — Vector Embeddings (pgvector / ChromaDB)

Semantic search over email requires embeddings. Two popular approaches:

**pgvector** (Postgres extension) — used when you already have a Postgres DB:
```sql
CREATE EXTENSION vector;
CREATE TABLE email_embeddings (
  message_id TEXT PRIMARY KEY,
  subject TEXT,
  sender TEXT,
  body_excerpt TEXT,
  embedding vector(1536),
  created_at TIMESTAMP
);
CREATE INDEX ON email_embeddings USING ivfflat (embedding vector_cosine_ops);
```

**ChromaDB** — simpler, no Postgres required:
```python
import chromadb
client = chromadb.PersistentClient(path="./email_store")
collection = client.get_or_create_collection("inbox")
collection.add(
    ids=[message_id],
    documents=[email_body],
    metadatas=[{"sender": sender, "subject": subject, "date": date}]
)
```

Query:
```python
results = collection.query(
    query_texts=["follow up on the contract"],
    n_results=10,
    where={"sender": "partner@company.com"}  # optional filter
)
```

### Layer 3 — Knowledge Graph Extraction

The differentiator in `digitalhen/gmail-mcp` — LLM extracts entities and relationships from email content, building a graph of:
- **People**: sender, CC, mentioned contacts
- **Organizations**: companies, teams
- **Topics**: projects, products, deals
- **Decisions**: commitments made, deadlines set
- **Follow-ups**: action items, pending replies

```python
EXTRACT_PROMPT = """
From this email, extract:
1. People mentioned (name, email, role if known)
2. Organizations mentioned  
3. Key topics/projects
4. Decisions or commitments made
5. Action items or follow-ups required

Return JSON: {"people": [...], "orgs": [...], "topics": [...], "decisions": [...], "actions": [...]}

Email:
{email_content}
"""
```

Store relationships in a graph DB (NetworkX for local, Neo4j for scale):
```python
import networkx as nx
G = nx.DiGraph()
G.add_node(sender_email, type="person", name=sender_name)
G.add_node(topic, type="topic")
G.add_edge(sender_email, topic, relation="discussed", message_id=msg_id, date=date)
```

---

## The 31-Tool Stack (digitalhen Pattern)

`digitalhen/gmail-mcp` exposes Gmail as 31 MCP tools covering:

| Category | Tools | Description |
|----------|-------|-------------|
| Basic ops | `gmail_search`, `gmail_read`, `gmail_send`, `gmail_draft`, `gmail_trash` | Standard CRUD |
| Labels | `gmail_label_create`, `gmail_label_apply`, `gmail_label_list` | Organization |
| Threads | `gmail_thread_read`, `gmail_thread_archive`, `gmail_thread_mute` | Thread control |
| Semantic | `inbox_semantic_search`, `find_similar_emails`, `search_by_topic` | Vector search |
| Graph | `people_graph`, `topic_graph`, `action_items`, `get_decisions` | Knowledge graph |
| Triage | `inbox_summary`, `urgent_emails`, `unread_by_sender` | Intelligence layer |
| Automation | `apply_rule`, `bulk_archive`, `unsubscribe_sender` | Autonomous action |

### Prescriptive Tool Descriptions (MCP Best Practice)

The best MCP tools tell the LLM *when* to call them, not just *what* they do:

```python
@mcp.tool()
async def urgent_emails(hours_back: int = 24) -> str:
    """
    ALWAYS call this when user asks "what's urgent", "what needs attention",
    or "anything important?". Returns emails flagged as time-sensitive by
    sender VIP status, subject keywords (URGENT, ACTION REQUIRED, deadline),
    or unanswered questions older than 4 hours.
    """
```

---

## Autonomous Triage Pattern

The core agentic loop for an AI email assistant:

```
POLL (every 5 min or webhook)
  └─ fetch new emails via historyId sync
  └─ for each email:
      ├─ extract entities → update knowledge graph
      ├─ embed body → add to vector store
      ├─ classify: urgent / FYI / spam / newsletter / actionable
      └─ route based on classification:
          URGENT → notify user immediately (Telegram/push)
          ACTIONABLE → create task in task manager, label "ACTION"
          NEWSLETTER → archive + store summary
          FYI → label "READ LATER"
          SPAM → trash
```

This pattern (classify → route → act) mirrors the supervisor-worker pattern from AI agent design — email as a continuous event stream, each email a task dispatched to specialized handlers.

---

## Multi-Account Unified Inbox

`mrchevyceleb/unified-gmail-mcp` solves a real problem: professionals with 2-4 Gmail accounts.

Architecture:
```python
accounts = {
    "personal": gmail_service("personal/token.json"),
    "work": gmail_service("work/token.json"),
    "side_project": gmail_service("side/token.json"),
}

async def unified_search(query: str):
    results = await asyncio.gather(*[
        search_account(svc, query) 
        for svc in accounts.values()
    ])
    # Merge, dedup, sort by date
    return sorted(flatten(results), key=lambda x: x["date"], reverse=True)
```

Each account has its own token, same OAuth flow. Single MCP server exposes all accounts.

---

## Circuit Breaker for Gmail Rate Limits

Gmail API rate limits: 250 quota units/second, 1B units/day. Agents that hammer the API get blocked. Use a circuit breaker:

```python
class GmailCircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failures = 0
        self.threshold = failure_threshold
        self.timeout = timeout  # seconds
        self.state = "CLOSED"  # CLOSED=normal, OPEN=blocked, HALF-OPEN=testing
        self.last_failure = None

    async def call(self, fn, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure > self.timeout:
                self.state = "HALF-OPEN"
            else:
                raise Exception("Circuit OPEN — Gmail API rate limited, backing off")
        try:
            result = await fn(*args, **kwargs)
            if self.state == "HALF-OPEN":
                self.state = "CLOSED"
                self.failures = 0
            return result
        except HttpError as e:
            if e.resp.status in (429, 503):
                self.failures += 1
                self.last_failure = time.time()
                if self.failures >= self.threshold:
                    self.state = "OPEN"
            raise
```

---

## Competitive Landscape (Apr 2026)

| Repo | Stars | Differentiator |
|------|-------|----------------|
| `taylorwilsdon/google_workspace_mcp` | 2K | Breadth: 100+ tools, all Workspace apps |
| `digitalhen/gmail-mcp` | — | Depth: knowledge graph + semantic search |
| `aaronsb/google-workspace-mcp` | — | Auth + reliability focus |
| `mrchevyceleb/unified-gmail-mcp` | — | Multi-account support |
| Official Google Workspace MCP | N/A | Managed, enterprise-grade, OAuth 2.1 |

**Pattern emerging**: Breadth tools (taylorwilsdon) win stars. Depth tools (digitalhen) win for specific power users who need AI-native inbox management.

---

## What to Build Next

The gap in the ecosystem (per NotebookLM synthesis):
1. **Google Meet** — no MCP creates meeting links or extracts transcripts
2. **Google Analytics** — no direct traffic/conversion data querying
3. **Gmail → Notion/Linear sync** — route email action items directly to project management
4. **Email relationship CRM** — use the knowledge graph to surface "you haven't replied to X in 14 days"

The third gap is the most valuable for productivity agents: email action items auto-created as tasks, no human copy-paste.

---

## Key Takeaway

Email agents in 2026 aren't just "read email + send reply." The state of the art:

1. **OAuth 2.1** for access (not API keys — Google doesn't offer them for Gmail)
2. **Vector embeddings** for semantic search (pgvector or ChromaDB)
3. **Knowledge graph extraction** via LLM — turn email into a structured graph of people, topics, decisions
4. **Prescriptive tool descriptions** — tell the LLM when to call the tool, not just what it does
5. **Circuit breakers** — protect against rate limits in autonomous agents
6. **Multi-account unification** — single interface over N accounts

The inbox is a graph. Build graph tools, not list tools.
