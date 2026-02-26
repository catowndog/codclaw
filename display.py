"""
Rich CLI display module — colored output, panels, spinners, markdown rendering.
"""

import json
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.table import Table
from rich.rule import Rule
from rich import box

console = Console()


def show_banner(agent_name: str = "CLI Agent"):
    """Display startup banner with agent name."""
    banner = Text()
    banner.append(f"  {agent_name}  ", style="bold white on blue")
    console.print()
    console.print(Panel(banner, box=box.DOUBLE, style="blue", expand=False))
    console.print()


def show_config(model: str, project_path: str, effort: str, mcp_tools_count: int, skills_count: int):
    """Display configuration summary."""
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value", style="bold")
    table.add_row("Model", model)
    table.add_row("Project", project_path)
    table.add_row("Effort", effort)
    table.add_row("MCP Tools", str(mcp_tools_count))
    table.add_row("Skills", str(skills_count))
    console.print(Panel(table, title="[bold]Configuration", box=box.ROUNDED, style="cyan"))
    console.print()


def show_mcp_connected(server_name: str, tools: list[str]):
    """Show MCP server connection info."""
    tools_str = ", ".join(tools) if tools else "(no tools)"
    console.print(
        f"  [green]\u2713[/green] MCP [bold]{server_name}[/bold]: {tools_str}",
    )


def show_mcp_error(server_name: str, error: str):
    """Show MCP server connection error."""
    console.print(f"  [red]\u2717[/red] MCP [bold]{server_name}[/bold]: {error}")


def show_skills_list(skills: list[dict]):
    """Show available skills."""
    if not skills:
        console.print("  [dim]No skills found[/dim]")
        return
    for skill in skills:
        console.print(f"  [magenta]\u25cf[/magenta] [bold]{skill['name']}[/bold]: {skill['description']}")


def show_iteration_header(iteration: int):
    """Show iteration header."""
    console.print()
    console.print(Rule(f"[bold yellow]Iteration #{iteration}[/bold yellow]", style="yellow"))
    console.print()


def show_thinking(text: str):
    """Display thinking block in dim italic panel."""
    display_text = text
    if len(display_text) > 2000:
        display_text = display_text[:2000] + "\n\n... (truncated)"
    console.print(
        Panel(
            Text(display_text, style="dim italic"),
            title="[dim]\U0001f4ad Thinking[/dim]",
            border_style="dim",
            box=box.ROUNDED,
        )
    )


def show_redacted_thinking():
    """Display redacted thinking block."""
    console.print(
        Panel(
            Text("[encrypted thinking block]", style="dim italic"),
            title="[dim]\U0001f512 Redacted Thinking[/dim]",
            border_style="dim red",
            box=box.ROUNDED,
        )
    )


def show_text_response(text: str):
    """Display text response with markdown rendering."""
    console.print(
        Panel(
            Markdown(text),
            title="[bold green]\U0001f916 Response[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        )
    )


def show_tool_call(tool_name: str, tool_args: dict):
    """Display tool call with name and arguments."""
    args_str = json.dumps(tool_args, indent=2, ensure_ascii=False)
    if len(args_str) > 1000:
        args_str = args_str[:1000] + "\n... (truncated)"
    console.print(
        Panel(
            Text(args_str, style="white"),
            title=f"[bold cyan]\U0001f527 Tool: {tool_name}[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )


def show_tool_result(tool_name: str, result: str):
    """Display tool result summary."""
    display = result
    if len(display) > 500:
        display = display[:500] + "\n... (truncated)"
    console.print(
        Panel(
            Text(display, style="dim"),
            title=f"[dim]\u2190 Result: {tool_name}[/dim]",
            border_style="dim cyan",
            box=box.SIMPLE,
        )
    )


def show_skill_loaded(skill_name: str):
    """Show skill loading indicator."""
    console.print(f"  [magenta]\U0001f4d6 Skill loaded:[/magenta] [bold]{skill_name}[/bold]")


def show_skill_created(skill_name: str, size: int):
    """Show skill creation indicator."""
    console.print(
        f"  [green]\u2728 Skill created:[/green] [bold]{skill_name}[/bold] ({size:,} chars)"
    )


def show_token_usage(input_tokens: int, output_tokens: int):
    """Display token usage."""
    console.print(
        f"  [dim]Tokens: input={input_tokens:,}  output={output_tokens:,}  "
        f"total={input_tokens + output_tokens:,}[/dim]"
    )


def show_error(message: str):
    """Display error message."""
    console.print(f"  [bold red]\u2717 Error:[/bold red] {message}")


def show_warning(message: str):
    """Display warning message."""
    console.print(f"  [yellow]\u26a0 Warning:[/yellow] {message}")


def show_info(message: str):
    """Display info message."""
    console.print(f"  [blue]\u2139[/blue] {message}")


def show_stats(summary: str):
    """Display periodic token usage statistics."""
    console.print()
    console.print(
        Panel(
            Text(summary, style="bold"),
            title="[bold yellow]\U0001f4ca Stats[/bold yellow]",
            border_style="yellow",
            box=box.DOUBLE,
        )
    )
    console.print()


def show_research_start(url: str, current: int, total: int):
    """Display research phase start for a site."""
    console.print()
    console.print(Rule(
        f"[bold magenta]\U0001f50d Research [{current}/{total}]: {url}[/bold magenta]",
        style="magenta",
    ))


def show_research_done(url: str):
    """Display research completion for a site."""
    console.print(f"  [green]\u2713[/green] Research complete: [bold]{url}[/bold]")


def show_research_summary(total: int, researched: int, cached: int):
    """Display research phase summary."""
    console.print()
    console.print(
        Panel(
            Text(
                f"Sites: {total} total | {researched} researched | {cached} cached\n"
                f"Reports saved to .temp/references/",
                style="bold",
            ),
            title="[bold magenta]\U0001f50d Research Complete[/bold magenta]",
            border_style="magenta",
            box=box.ROUNDED,
        )
    )
    console.print()


def show_shutdown():
    """Display shutdown message."""
    console.print()
    console.print(Rule("[bold red]Shutting down[/bold red]", style="red"))
    console.print()


def get_status_context(message: str):
    """Get a rich Status context manager for spinners."""
    return console.status(f"[bold blue]{message}[/bold blue]", spinner="dots")
