"""Stock video fetcher — downloads clips from Pexels API."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv
import httpx
import typer

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

app = typer.Typer()

PEXELS_BASE = "https://api.pexels.com/videos/search"


def fetch_videos(
    api_key: str,
    keywords: str,
    count: int,
    orientation: str,
    output_dir: Path,
    min_duration: int = 5,
    max_duration: int = 30,
) -> list[Path]:
    """Search and download stock videos from Pexels."""
    output_dir.mkdir(parents=True, exist_ok=True)

    headers = {"Authorization": api_key}
    params = {
        "query": keywords,
        "per_page": count * 2,  # fetch extra in case some are filtered
        "orientation": orientation,
    }

    with httpx.Client(timeout=60) as client:
        resp = client.get(PEXELS_BASE, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()

    videos = data.get("videos", [])
    downloaded: list[Path] = []

    for video in videos:
        if len(downloaded) >= count:
            break

        duration = video.get("duration", 0)
        if duration < min_duration or duration > max_duration:
            continue

        # Pick the best quality file matching orientation
        video_files = video.get("video_files", [])
        best_file = _pick_best_file(video_files, orientation)
        if not best_file:
            continue

        url = best_file["link"]
        filename = f"clip_{video['id']}.mp4"
        out_path = output_dir / filename

        typer.echo(f"Downloading {url}...")
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", url) as stream:
                stream.raise_for_status()
                with open(out_path, "wb") as f:
                    for chunk in stream.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        downloaded.append(out_path)
        typer.echo(f"Saved {out_path} ({duration}s)")

    return downloaded


def _pick_best_file(video_files: list[dict], orientation: str) -> dict | None:
    """Select the best video file by resolution."""
    target_height = 1920 if orientation == "portrait" else 1080
    sorted_files = sorted(
        video_files,
        key=lambda f: abs((f.get("height", 0)) - target_height),
    )
    return sorted_files[0] if sorted_files else None


@app.command()
def download(
    keywords: str = typer.Option(..., help="Comma-separated search keywords"),
    count: int = typer.Option(3, help="Number of clips to download"),
    orientation: str = typer.Option("portrait", help="portrait or landscape"),
    output_dir: Path = typer.Option(..., help="Directory to save clips"),
    api_key: str = typer.Option(None, envvar="PEXELS_API_KEY"),
    min_duration: int = typer.Option(5, help="Minimum clip duration in seconds"),
    max_duration: int = typer.Option(30, help="Maximum clip duration in seconds"),
) -> None:
    """Download stock videos from Pexels for video assembly."""
    if not api_key:
        typer.echo("Error: PEXELS_API_KEY required. Set in .env or pass --api-key", err=True)
        raise typer.Exit(1)

    paths = fetch_videos(api_key, keywords, count, orientation, output_dir, min_duration, max_duration)
    typer.echo(f"\nDownloaded {len(paths)} clips to {output_dir}")

    if len(paths) < count:
        typer.echo(f"Warning: only found {len(paths)} of {count} requested clips", err=True)


if __name__ == "__main__":
    app()
