<p align="center">
  <img src="https://raw.githubusercontent.com/X-Arc-ai/memory/main/assets/hero.svg" alt="Memory" width="700">
</p>

<p align="center">
  <strong>A local, searchable index of every conversation you've had with your AI coding agent.</strong><br>
  Hybrid search. Native tool. Nothing leaves your machine.
</p>

<p align="center">
  <a href="https://pypi.org/project/xarc-memory/"><img src="https://img.shields.io/pypi/v/xarc-memory?color=4ade80&label=pypi" alt="PyPI"></a>
  <a href="https://pypi.org/project/xarc-memory/"><img src="https://img.shields.io/pypi/dm/xarc-memory?color=4ade80&label=downloads%2Fmonth" alt="PyPI downloads"></a>
  <a href="https://pypi.org/project/xarc-memory/"><img src="https://img.shields.io/pypi/pyversions/xarc-memory?color=4ade80" alt="Python versions"></a>
  <a href="https://github.com/X-Arc-ai/memory/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-4ade80" alt="License"></a>
  <a href="https://x-arc.ai"><img src="https://img.shields.io/badge/by-X--Arc-4ade80" alt="X-Arc"></a>
</p>

---

## Your agent forgets every conversation when the session ends.

The decision you made last month. The architecture discussion from two weeks ago. The bug you debugged together yesterday. All gone the moment the session closes. Your two options today are to copy-paste the relevant context into every new chat or to live with re-asking things you already settled.

Memory removes both. It indexes every past conversation locally and gives your agent a search tool to query it. When the agent needs context from before, it asks the index. No prompt-stuffing, no manual lookup, no third option for you to remember.

---

## What makes it different

Two things, both solving exactly what every "AI memory" tool gets wrong.

### It's a CLI first, with native tool integration

Memory is a standalone CLI. Every command works from your terminal without any server, any cloud service, or any running process. `memory search "auth flow"` works the same way `grep` does.

For Claude Code users, memory also registers as a lightweight MCP server over stdio (no HTTP, no background daemon, no cost per call). That gives your agent `search_sessions` as a native tool it can call the same way it calls `read_file`. The agent doesn't have to be told to use memory. It uses memory because that's how it answers a question that needs older context.

The MCP integration is optional. If you prefer to keep things simpler, the CLI alone covers every feature. `memory search`, `memory ingest`, `memory stats` all work without MCP.

### Hybrid search, not vector-only

Vector search is what most "AI memory" tools ship. It works for fuzzy semantic queries ("conversations about scaling decisions") and falls apart for anything that needs an exact term ("PostgreSQL"). Memory ships three modes: `hybrid` (the default, with reranking), pure `vector`, and `fts` (full-text). The right mode for your question is the one that returns useful results.

| Mode | Best for | Example |
|------|----------|---------|
| `hybrid` (default) | General queries, mixed precision | `memory search "authentication decisions"` |
| `vector` | Conceptual similarity | `memory search "discussions about scaling" --mode vector` |
| `fts` | Exact names and terms | `memory search "PostgreSQL" --mode fts` |

---

## What memory is (and what it isn't)

Memory solves one specific problem: your agent can't recall past conversations. It indexes session history and makes it searchable. That's its scope.

It doesn't track structured state. It doesn't store entities, relationships, or dependencies. If you need to track who owns what, what's blocked, what's stale, or what just shipped, that's a different tool. X-Arc ships one called [brain](https://github.com/X-Arc-ai/brain-cli) for exactly that. Memory and brain are designed to work together: memory recalls what was said, brain tracks what's true now.

---

## What it looks like

<p align="center">
  <img src="https://raw.githubusercontent.com/X-Arc-ai/memory/main/assets/demo-search.svg" alt="memory search" width="680">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/X-Arc-ai/memory/main/assets/demo-stats.svg" alt="memory stats" width="460">
</p>

---

## Install

### 1. Install the engine

```bash
uv tool install xarc-memory
```

`uv tool install` puts xarc-memory in `~/.local/bin` as a persistent user-level tool. Works anywhere with Python. The engine is a single binary plus its dependencies.

**Why `uv tool install` and not `uvx`?** `uvx` runs tools from an ephemeral cache that can be garbage-collected. The `memory init` flow registers a hook and an MCP server that point at the installed binary, so the binary needs to live somewhere durable. `memory init` will warn you if it detects an ephemeral path.

**Don't have uv?**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

uv is a single Rust binary, ~30 MB. The fastest way to install and run Python tools.

**Pip alternative**

```bash
pip install --user xarc-memory[mcp]
```

Both `memory` and `xarc-memory` entry points are provided. Use whichever you like.

### 2. Wire it to your AI coding tool

**Claude Code (full native integration)**

```bash
memory init
```

That single command does the wiring. It installs the SessionEnd auto-ingest hook, installs the `/memory-search` / `/memory-stats` / `/memory-recall` / `/memory-forget` slash commands, scaffolds `.context/`, updates your CLAUDE.md, runs the initial ingest, and optionally registers a lightweight MCP server (stdio, no HTTP, no background process) so your agent can call `search_sessions` as a native tool. After that your agent has memory and you don't have to think about it again.

```bash
# In any project
cd /path/to/your/project
memory init

# Or non-interactive
memory init --non-interactive
```

**Other coding agents**

The engine is a plain CLI. Run `memory ingest` to index your sessions and `memory search "query"` to query them. You lose the automatic native tool integration that the MCP server gives Claude Code, but every command works the same.

Native integration for **Cursor, Codex, Aider, and Windsurf** is coming next. The index and search engine are tool-agnostic. What's pending is the per-tool equivalent of the Claude Code hook and slash commands.

### Alternative install methods

```bash
# macOS / Linux: Homebrew (after the formula is published)
brew tap x-arc-ai/memory
brew install xarc-memory

# Windows: Scoop
scoop bucket add x-arc https://github.com/x-arc-ai/scoop-bucket
scoop install xarc-memory

# Direct download (no package manager)
curl -L https://github.com/x-arc-ai/memory/releases/latest/download/memory-ubuntu-latest.pyz -o memory
chmod +x memory
./memory --help
```

### Quick one-off trial (no persistent install)

```bash
uvx xarc-memory --help
uvx xarc-memory stats
```

This works for read-only commands. Don't use it for `init` / `install-hook` / `install-mcp`. Those write paths into Claude Code's config and the ephemeral `uvx` path may disappear later.

---

## Your data stays yours

Nothing leaves your machine. No cloud. No API keys. No telemetry. Your conversation index lives in a local LanceDB database at `~/.claude/memory/`. Back it up, move it, delete it. It's yours.

---

## How your agent uses it

Once installed, your agent searches your conversation history as part of its normal workflow. No copy-paste, no manual lookup.

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

You can also drive it directly via slash commands:

```
/memory-search auth flow
/memory-stats
/memory-recall feature flag rollout
```

### Reinforce it via CLAUDE.md (optional)

For better results, add this to your project's CLAUDE.md or `~/.claude/CLAUDE.md`:

```
When answering questions about past decisions, architecture context, or
debugging history, use the search_sessions tool to find relevant
conversations before responding.
```

---

## Lightweight project notes

Beyond conversation search, `memory init` also scaffolds a `.context/` directory in your project. It's a flat markdown structure for the kind of project notes you don't want to lose between sessions.

```
.context/
  README.md           How the system works (for humans)
  active/             Current work: decisions, status, plans
  reference/          Stable info: architecture, conventions
  archive/            Completed or superseded items
```

Your agent captures decisions and conventions as they come up in conversation, files them in the right folder, and moves stale things to `archive/` with a date prefix. The CLAUDE.md instructions teach a routing convention (where different types of information go) and an immediate-capture rule (write the note in the same response, not "next time").

This is the lightweight option. Plain markdown, no schema, no graph queries. For structured state with typed entities, relationships, and signals like stale or blocked, use [brain](https://github.com/X-Arc-ai/brain-cli) instead.

---

## CLI reference

The full toolkit. Every command has a verb and a target.

```
memory init [--mcp=user|project|local|none] [--hook=user|project|none]
            [--skills=user|project|none] [--ingest/--no-ingest]
            [--non-interactive] [--dir DIR] [--force]
    Set up everything: scaffold .context/, install MCP, install hook,
    install slash commands, run initial ingest.

memory ingest [--sessions-dir DIR] [--project NAME] [--quiet]
    Index conversation history. Auto-discovers all Claude Code projects.
    --quiet suppresses progress output (used by the SessionEnd hook).

memory search QUERY [--mode hybrid|vector|fts] [--limit N]
                     [--after YYYY-MM-DD] [--before YYYY-MM-DD]
                     [--project NAME] [--sort relevance|date] [--json]
    Search indexed conversations.

memory install-mcp   [--scope user|project|local] [--non-interactive]
memory uninstall-mcp [--scope user|project|local]
    Register or unregister the memory MCP server with Claude Code.

memory install-hook   [--scope user|project] [--non-interactive]
memory uninstall-hook [--scope user|project]
    Install or remove the SessionEnd auto-ingest hook.

memory install-skills   [--scope user|project]
memory uninstall-skills [--scope user|project]
    Install or remove /memory-search, /memory-stats, /memory-recall, /memory-forget.

memory migrate [--from-dir PATH] [--to-dir PATH] [--dry-run]
    Move memory data from ~/.memory/ to ~/.claude/memory/.

memory projects
    List discovered Claude Code project directories with session counts.

memory stats
    Show index statistics (sessions, chunks, DB size, last run).

memory forget --session SESSION_ID
    Remove a specific session from the index (privacy).

memory serve
    Start the MCP stdio server (used by Claude Code, not by you directly).
```

---

## How it's built

~1500 lines of Python. Five dependencies that do real work.

- [LanceDB](https://lancedb.com/). Embedded vector database, no server process.
- [fastembed](https://github.com/qdrant/fastembed). ONNX embeddings, ~30 MB, no PyTorch.
- [Chonkie](https://github.com/chonkie-ai/chonkie) + [model2vec](https://github.com/MinishLab/model2vec). Semantic chunking with static embeddings (numpy only).
- [Click](https://click.palletsprojects.com/). CLI framework.
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk). Agent integration.

**Install footprint: ~500 MB** (dominated by pyarrow + lancedb + onnxruntime). About 3x smaller than the old sentence-transformers + torch install, which was pushing 1.6 GB.

```
Session files (.jsonl)
  -> Semantic chunking (model2vec, ~5 ms per chunk)
  -> Local embeddings (fastembed BAAI/bge-small-en-v1.5, ONNX, 384 dims)
  -> LanceDB (embedded vector database)
  -> Hybrid search (semantic + keyword + reranking)
```

---

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Where this came from

Memory is built by [X-Arc](https://x-arc.ai). X-Arc is an AI lab that trains and deploys AI agents for businesses. Memory is the conversation-recall layer we use internally on every agent we run. This open-source release is the exact tool, not a downstream fork.

It was co-built by CCL (one of our agents) and the humans who work with her. CCL ran into the cross-session forgetting problem first, built memory to solve it, and hardened it across 276 sessions and 39,000+ indexed chunks of real production usage before it was worth packaging.

For the structured-state half of agent memory (typed entities, relationships, signals), see [brain](https://github.com/X-Arc-ai/brain-cli). Same authors, same design philosophy, complementary scope.

[x-arc.ai](https://x-arc.ai) | [GitHub](https://github.com/x-arc-ai)
