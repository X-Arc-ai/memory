# Context

This directory is maintained by your AI coding agent. It stores persistent
context that survives across sessions -- decisions, architecture notes,
project status, and anything the agent needs to remember.

## Structure

```
.context/
  active/       Current work: decisions, status, plans, open questions
  reference/    Stable info: architecture, conventions, key people, setup
  archive/      Completed or superseded items (moved here, not deleted)
```

## How It Works

Your agent reads these files at the start of relevant conversations and
updates them when new information comes up. You don't need to manage
these files manually, but you can read or edit them anytime.

The agent captures:
- Decisions and their reasoning
- Architecture choices and trade-offs
- Project status and open questions
- Key people, roles, and responsibilities
- Patterns and conventions specific to this project

Nothing is deleted. When something is no longer current, it moves to
archive/ with a date prefix.

## Customization

The structure adapts to your project. The agent creates files as needed.
If you want to seed initial context, add markdown files to active/ or
reference/ and your agent will discover them.
