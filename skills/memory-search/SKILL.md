---
name: memory-search
description: Search past Claude Code conversations using xarc-memory
argument-hint: <query>
user-invocable: true
---

Run `memory search "$ARGUMENTS" --json --limit 10` and present the results to me.

For each result, show:
- The date
- The session summary
- The matched text excerpt
- The relevance score

If there are no results, suggest alternative queries the user could try.
