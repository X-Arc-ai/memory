"""Terminal UI for Memory. X-Arc design system adapted for terminal.

Design tokens derived from x-arc.ai:
  Accent:     #4ade80 (bright green)
  Text:       #f0f0f0 (primary), #888888 (secondary), #555555 (muted)
  Surface:    #111113 (panels)
  Border:     #222225 (lines)
  Font:       Monospace (terminal native = JetBrains Mono equivalent)
  Pattern:    Minimal, no gradients, generous whitespace, green accent sparingly
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.style import Style
from rich import box

# X-Arc design tokens for terminal
ACCENT = "#4ade80"
ACCENT_DIM = "#22c55e"
TEXT_PRIMARY = "#f0f0f0"
TEXT_SECONDARY = "#888888"
TEXT_MUTED = "#555555"
BORDER = "#333338"
SURFACE = "#111113"

# Styles
STYLE_ACCENT = Style(color=ACCENT, bold=True)
STYLE_DIM_ACCENT = Style(color=ACCENT_DIM)
STYLE_PRIMARY = Style(color=TEXT_PRIMARY)
STYLE_SECONDARY = Style(color=TEXT_SECONDARY)
STYLE_MUTED = Style(color=TEXT_MUTED)
STYLE_SCORE = Style(color=ACCENT, bold=True)
STYLE_DATE = Style(color=TEXT_SECONDARY)
STYLE_LABEL = Style(color=TEXT_MUTED)

console = Console()

# Quiet mode toggle -- when True, print_* helpers become no-ops.
# Used by `memory ingest --quiet` and the SessionEnd hook.
_quiet = False


def set_quiet(value: bool):
    """Enable or disable quiet mode globally for this process."""
    global _quiet
    _quiet = value


def is_quiet() -> bool:
    return _quiet

# Box style matching X-Arc's minimal 1px borders
MEMORY_BOX = box.Box(
    "    \n"
    " ── \n"
    "    \n"
    " ── \n"
    " ── \n"
    " ── \n"
    "    \n"
    "    \n"
)


def brand_header():
    """Compact branded header for first-run or verbose output."""
    title = Text()
    title.append("MEMORY", style=Style(color=ACCENT, bold=True))
    title.append("  ", style=STYLE_MUTED)
    title.append("give your ai coding agent memory", style=STYLE_MUTED)
    console.print()
    console.print(title)
    console.print(Text("─" * 48, style=Style(color=BORDER)))


def print_empty_state(message: str, hint: str = ""):
    """Empty state with helpful guidance."""
    if _quiet:
        return
    console.print()
    console.print(f"  {message}", style=STYLE_SECONDARY)
    if hint:
        console.print(f"  {hint}", style=STYLE_MUTED)
    console.print()


def print_projects(projects: list[dict]):
    """Display discovered projects.

    projects: list of {"path": str, "display": str, "sessions": int}
    """
    brand_header()
    console.print()

    total_sessions = sum(p["sessions"] for p in projects)
    console.print(
        f"  {len(projects)} projects discovered",
        style=STYLE_SECONDARY,
    )
    console.print(
        f"  {total_sessions} sessions total",
        style=STYLE_MUTED,
    )
    console.print()

    for p in projects:
        count_style = STYLE_ACCENT if p["sessions"] > 0 else STYLE_MUTED
        line = Text()
        line.append("  ")
        count_text = str(p["sessions"]).rjust(4)
        line.append(count_text, style=count_style)
        line.append("  ", style=STYLE_MUTED)
        line.append(p["display"], style=STYLE_PRIMARY if p["sessions"] > 0 else STYLE_MUTED)
        console.print(line)

    console.print()


def print_ingest_start(session_count: int, project_count: int):
    """Ingest operation header."""
    if _quiet:
        return
    console.print()
    line = Text()
    line.append("  indexing ", style=STYLE_SECONDARY)
    line.append(str(session_count), style=STYLE_ACCENT)
    line.append(" sessions", style=STYLE_SECONDARY)
    line.append(" across ", style=STYLE_MUTED)
    line.append(str(project_count), style=STYLE_SECONDARY)
    line.append(" projects", style=STYLE_MUTED)
    console.print(line)
    console.print()


def print_ingest_session(index: int, total: int, session_id: str, turns: int, chunks: int):
    """Single session ingestion progress line."""
    if _quiet:
        return
    line = Text()
    line.append(f"  [{index}/{total}]", style=STYLE_MUTED)
    line.append(f" {session_id[:12]}", style=STYLE_SECONDARY)
    line.append(f"  {turns} turns", style=STYLE_MUTED)
    line.append(" -> ", style=Style(color=BORDER))
    line.append(f"{chunks} chunks", style=STYLE_DIM_ACCENT if chunks > 0 else STYLE_MUTED)
    console.print(line)


def print_ingest_complete(sessions: int, chunks: int):
    """Ingest completion summary."""
    if _quiet:
        return
    console.print()
    line = Text()
    line.append("  done. ", style=STYLE_SECONDARY)
    line.append(str(sessions), style=STYLE_ACCENT)
    line.append(" sessions, ", style=STYLE_SECONDARY)
    line.append(str(chunks), style=STYLE_ACCENT)
    line.append(" chunks indexed.", style=STYLE_SECONDARY)
    console.print(line)
    console.print()


def print_ingest_up_to_date():
    """Nothing to ingest."""
    if _quiet:
        return
    console.print()
    console.print("  all sessions up to date.", style=STYLE_MUTED)
    console.print()


def print_search_results(results: list, meta: dict):
    """Display search results with scores and previews."""
    console.print()

    if meta.get("truncated"):
        header = Text()
        header.append(f"  {meta['total_matches']} matches", style=STYLE_SECONDARY)
        header.append(f"  showing top {meta['returned']}", style=STYLE_MUTED)
        console.print(header)
        console.print()

    for i, r in enumerate(results):
        # Score badge + date + summary line
        header = Text()
        header.append("  ")
        header.append(f"{r.score:.2f}", style=STYLE_SCORE)
        header.append(f"  {r.date}", style=STYLE_DATE)
        if r.session_summary:
            header.append(f"  {r.session_summary}", style=STYLE_PRIMARY)
        console.print(header)

        # Preview text
        preview = r.text[:300].replace("\n", " ")
        if len(r.text) > 300:
            preview += "..."
        console.print(f"       {preview}", style=STYLE_MUTED)

        if i < len(results) - 1:
            console.print()

    console.print()


def print_stats(stats: dict):
    """Display index statistics."""
    console.print()

    items = [
        ("sessions", str(stats["sessions"])),
        ("projects", str(stats.get("projects", "N/A"))),
        ("chunks", str(stats["chunks"])),
        ("db size", stats["db_size"]),
        ("last indexed", stats["last_run"][:19] if stats["last_run"] != "Never" else "never"),
    ]

    for label, value in items:
        line = Text()
        line.append(f"  {label.rjust(14)}", style=STYLE_MUTED)
        line.append("  ", style=STYLE_MUTED)
        line.append(value, style=STYLE_ACCENT if label in ("sessions", "chunks") else STYLE_PRIMARY)
        console.print(line)

    console.print()


def print_forget(session_id: str, count: int):
    """Forget operation result."""
    console.print()
    if count:
        line = Text()
        line.append("  removed ", style=STYLE_SECONDARY)
        line.append(str(count), style=STYLE_ACCENT)
        line.append(f" chunks for session {session_id}.", style=STYLE_SECONDARY)
        console.print(line)
    else:
        console.print(f"  session {session_id} not found in index.", style=STYLE_MUTED)
    console.print()


def print_model_download(model_name: str):
    """Show model download notice."""
    if _quiet:
        return
    line = Text()
    line.append("  downloading ", style=STYLE_MUTED)
    line.append(model_name, style=STYLE_SECONDARY)
    line.append("...", style=STYLE_MUTED)
    console.print(line)


def print_embedding_progress(chunk_count: int):
    """Show embedding progress notice."""
    if _quiet:
        return
    line = Text()
    line.append("  embedding ", style=STYLE_MUTED)
    line.append(str(chunk_count), style=STYLE_SECONDARY)
    line.append(" chunks...", style=STYLE_MUTED)
    console.print(line)


def print_fts_building():
    """Show FTS index building notice."""
    if _quiet:
        return
    console.print("  building search index...", style=STYLE_MUTED)


def print_warning(message: str):
    """Warning message."""
    if _quiet:
        return
    console.print(f"  {message}", style=Style(color="#eab308"))


def print_deleted_old(count: int):
    """Old chunks deleted for updated sessions."""
    if _quiet:
        return
    console.print(
        f"  updated {count} existing sessions",
        style=STYLE_MUTED,
    )
