---
description: Search past Claude Code conversations using agent-memory
argument-hint: <query>
---

Run `memory search "$ARGUMENTS" --json --limit 10` and present the results to me.

For each result, show:
- The date
- The session summary
- The matched text excerpt
- The relevance score

If there are no results, suggest alternative queries the user could try.
