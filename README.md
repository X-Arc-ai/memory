<p align="center">
  <img src="assets/hero.svg" alt="Memory" width="700">
</p>

<p align="center">
  <strong>Give your AI coding agent memory across sessions.</strong><br>
  Search past conversations. Maintain structured context. All local.
</p>

---

## Quick Start

### Search Past Conversations

```bash
pip install agent-memory
memory ingest              # Index your conversation history
memory search "auth flow"  # Find past discussions
```

### Structured Context

```bash
memory init                # Scaffold .context/ in your project
```

Your agent now maintains context across sessions. Decisions, architecture
notes, and project status are captured automatically via CLAUDE.md instructions.

---

## Give Your Agent Memory (MCP)

Your agent can search your conversation history as a native tool.
No copy-paste, no manual lookup.

### 1. Install with MCP support

```bash
pip install agent-memory[mcp]
memory ingest  # Index first, if you haven't
```

### 2. Add to Claude Code

Add to `~/.claude/settings.json` (all projects) or `.claude/settings.json` (one project):

```json
{
  "mcpServers": {
    "memory": {
      "command": "memory",
      "args": ["serve"]
    }
  }
}
```

### 3. Use it

Start a new Claude Code session. Your agent now has access to `search_sessions`.
It will search your conversation history when relevant.

```
You: Why did we switch from MongoDB to PostgreSQL?

Agent: Let me search your conversation history for that discussion.
       [invokes search_sessions("MongoDB PostgreSQL migration")]

Agent: On March 15, you discussed this with your agent. The key reasons were:
       1. Need for ACID transactions in the billing pipeline
       2. PostGIS for location queries
       3. Team familiarity with PostgreSQL
       The migration was completed on March 22 via PR #47.
```

### Enhance with CLAUDE.md (Optional)

For better results, add this to your project's CLAUDE.md or `~/.claude/CLAUDE.md`:

```
When answering questions about past decisions, architecture context, or
debugging history, use the search_sessions tool to find relevant
conversations before responding.
```

---

## Context Management

`memory init` scaffolds a `.context/` directory and adds instructions to
your CLAUDE.md. Your agent then maintains structured context automatically.

```
.context/
  README.md           How the system works (for humans)
  active/             Current work: decisions, status, plans
  reference/          Stable info: architecture, conventions, people
  archive/            Completed or superseded items
```

The agent captures decisions, architecture choices, project status, and
conventions as they come up in conversation. Nothing is deleted. When
something is no longer current, it moves to archive/ with a date prefix.

**What makes it work:** The CLAUDE.md instructions teach the agent a routing
convention (where different types of information go) and an immediate capture
rule (write context in the same response, not "next time"). The structure
adapts to your project. A solo developer gets different context than a
team lead managing multiple services.

```bash
# Initialize in any project
cd /path/to/your/project
memory init

# Or specify a directory
memory init --dir /path/to/project

# Reinitialize (overwrites .context/)
memory init --force
```

---

## What It Looks Like

<p align="center">
  <img src="assets/demo-search.svg" alt="Memory search" width="680">
</p>

<p align="center">
  <img src="assets/demo-stats.svg" alt="Memory stats" width="460">
</p>

---

## Search Modes

| Mode | Best For | Example |
|------|----------|---------|
| `hybrid` (default) | General queries | `memory search "authentication decisions"` |
| `vector` | Conceptual similarity | `memory search "discussions about scaling" --mode vector` |
| `fts` | Exact names and terms | `memory search "PostgreSQL" --mode fts` |

---

## CLI Reference

```
memory init [--dir DIR] [--force]
    Initialize context management in your project.
    Creates .context/ directory and adds instructions to CLAUDE.md.

memory ingest [--sessions-dir DIR] [--project NAME]
    Index conversation history. Auto-discovers all Claude Code projects.
    Only processes new or changed sessions (incremental).

memory search QUERY [--mode hybrid|vector|fts] [--limit N]
                     [--after YYYY-MM-DD] [--before YYYY-MM-DD]
                     [--project NAME] [--sort relevance|date] [--json]
    Search indexed conversations.

memory projects
    List discovered Claude Code project directories with session counts.

memory stats
    Show index statistics (sessions, chunks, DB size, last run).

memory forget --session SESSION_ID
    Remove a specific session from the index (privacy).

memory serve
    Start MCP server for agent integration (requires: pip install agent-memory[mcp]).
```

---

## How It's Built

- [LanceDB](https://lancedb.com/) -- embedded vector database, no server process
- [sentence-transformers](https://www.sbert.net/) -- local embeddings, no API needed
- [Chonkie](https://github.com/chonkie-ai/chonkie) -- semantic chunking
- [Click](https://click.palletsprojects.com/) -- CLI framework
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) -- agent integration

~800 lines of Python. Fully auditable. No magic.

**Nothing leaves your machine.** No cloud. No API keys. No telemetry.

```
Session files (.jsonl)
  -> Semantic chunking (groups related content)
  -> Local embeddings (BAAI/bge-small-en-v1.5, 384 dims)
  -> LanceDB (embedded vector database)
  -> Hybrid search (semantic + keyword + reranking)
```

---

## Roadmap

**v1 (current):** Claude Code session search + context management + MCP server

**v2:**
- Multi-tool support (Codex, Cursor, Aider, Windsurf)
- Auto-ingestion on session end (Claude Code hook)
- MCP HTTP transport for remote setups

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## How This Was Built

This project was built by CCL, an AI agent deployed by X-Arc that runs operations across multiple entities. You can see CCL as a contributor on this repo.

X-Memory started as an internal tool for CCL's own session memory. Once it proved valuable in production (276 sessions, 39K+ chunks indexed daily), CCL packaged and open-sourced it.

X-Arc deploys AI agents that ship real work. Manage it like a hire. It works like ten.

[x-arc.ai](https://x-arc.ai) | [GitHub](https://github.com/x-arc-ai)
