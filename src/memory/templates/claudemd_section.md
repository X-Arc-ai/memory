## Context Management

This project uses structured context files in `.context/` to maintain
memory across sessions. Follow these rules:

### Reading Context
Before answering questions about this project's architecture, decisions,
status, or history, check `.context/` for relevant files:
- `.context/active/` -- current decisions, status, open questions
- `.context/reference/` -- architecture, conventions, key info
- `.context/archive/` -- past decisions (check when asked about history)

### Writing Context
After any response where new information was shared, capture it:

| New Information | Where It Goes |
|----------------|---------------|
| Decision made | `.context/active/decisions.md` (append with date) |
| Architecture choice | `.context/reference/architecture.md` |
| Project status change | `.context/active/status.md` |
| Convention established | `.context/reference/conventions.md` |
| Person/role info | `.context/reference/people.md` |
| Completed/superseded | Move to `.context/archive/` with date prefix |

Create files as needed. Don't pre-create empty files.

### Rules
- Capture immediately (same response, not "next time")
- One fact, one place (no duplicating across files)
- Archive, don't delete (move to `.context/archive/YYYY-MM-DD-topic.md`)
- Keep files focused (split when a file covers too many topics)
- Context files are markdown. Keep them scannable.
