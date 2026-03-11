"""CLI entry point — spawns Claude Code team lead for video generation."""

import subprocess
import sys
from datetime import date
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(name="yt-auto", help="YouTube Automation Pipeline — Roman Urdu content generator")
console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = PROJECT_ROOT / "prompts"

CATEGORIES = ["motivation", "cooking", "hot_topics"]


def _read_prompt(name: str) -> str:
    """Read a prompt file and replace {date} placeholder."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        console.print(f"[red]Error: prompt file not found: {path}[/red]")
        raise typer.Exit(1)
    content = path.read_text(encoding="utf-8")
    return content.replace("{date}", date.today().isoformat())


def _spawn_claude(prompt: str, interactive: bool = False) -> int:
    """Spawn a Claude Code session with the given prompt."""
    cmd = ["claude"]
    if not interactive:
        cmd.append("--print")
    cmd.extend(["--prompt", prompt, "--allowedTools", "Bash,Read,Write,Glob,Grep,Agent"])

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


@app.command()
def generate(
    category: str = typer.Argument(
        "all",
        help="Category to generate: motivation, cooking, hot_topics, or all",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the prompt without executing"),
    interactive: bool = typer.Option(False, "-i", "--interactive", help="Run in interactive mode"),
) -> None:
    """Generate YouTube videos for one or all categories."""
    today = date.today().isoformat()

    if category == "all":
        console.print(f"[bold green]Generating all 3 categories for {today}[/bold green]")
        lead_prompt = _read_prompt("lead")

        # Inject teammate prompts into the lead prompt
        teammate_section = "\n\n## Teammate Prompts\n\n"
        for cat in CATEGORIES:
            teammate_section += f"### {cat}\n```\n{_read_prompt(cat)}\n```\n\n"

        full_prompt = lead_prompt + teammate_section

        if dry_run:
            console.print(full_prompt)
            return

        _spawn_claude(full_prompt, interactive)
    elif category in CATEGORIES or category.replace("-", "_") in CATEGORIES:
        cat = category.replace("-", "_")
        console.print(f"[bold green]Generating {cat} video for {today}[/bold green]")
        prompt = _read_prompt(cat)

        if dry_run:
            console.print(prompt)
            return

        _spawn_claude(prompt, interactive)
    else:
        console.print(f"[red]Unknown category: {category}[/red]")
        console.print(f"Available: {', '.join(CATEGORIES)} or all")
        raise typer.Exit(1)


@app.command()
def research(
    category: str = typer.Argument(..., help="Category to research"),
) -> None:
    """Research trending topics for a category (no video generation)."""
    cat = category.replace("-", "_")
    if cat not in CATEGORIES:
        console.print(f"[red]Unknown category: {category}[/red]")
        raise typer.Exit(1)

    prompt = (
        f"Research trending topics for {cat} YouTube content in Pakistan. "
        f"Use Playwright MCP to browse Google Trends Pakistan, YouTube trending, "
        f"and social media. Report the top 5 trending topics with brief descriptions. "
        f"Language context: Roman Urdu (Pakistani youth audience)."
    )

    console.print(f"[bold]Researching {cat} topics...[/bold]")
    _spawn_claude(prompt)


@app.command()
def upload(
    video: Path = typer.Argument(..., help="Video file to upload"),
    title: str = typer.Option(..., help="Video title"),
    description: str = typer.Option("", help="Video description"),
    tags: str = typer.Option("", help="Comma-separated tags"),
    thumbnail: Path = typer.Option(None, help="Thumbnail image"),
    shorts: bool = typer.Option(False, help="Upload as Shorts"),
) -> None:
    """Manually upload a video to YouTube."""
    cmd = [
        sys.executable, "-m", "src.tools.uploader", "upload",
        "--video", str(video),
        "--title", title,
    ]
    if description:
        cmd.extend(["--description", description])
    if tags:
        cmd.extend(["--tags", tags])
    if thumbnail:
        cmd.extend(["--thumbnail", str(thumbnail)])
    if shorts:
        cmd.append("--shorts")

    subprocess.run(cmd, cwd=str(PROJECT_ROOT))


@app.command()
def setup() -> None:
    """Run YouTube OAuth2 setup flow."""
    subprocess.run(
        [sys.executable, "-m", "src.tools.uploader", "setup"],
        cwd=str(PROJECT_ROOT),
    )


if __name__ == "__main__":
    app()
