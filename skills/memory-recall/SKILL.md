---
name: memory-recall
description: Recall and synthesize past discussions on a topic
argument-hint: <topic>
user-invocable: true
---

Run `memory search "$ARGUMENTS" --json --limit 20` to find past discussions about "$ARGUMENTS".

Then synthesize the results into a coherent summary that answers:
1. What decisions were made about this topic
2. What constraints or tradeoffs came up
3. What's the current state
4. Any open questions or unresolved threads

Cite specific dates and sessions for each claim.
