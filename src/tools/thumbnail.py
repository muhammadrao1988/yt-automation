"""Thumbnail generator — extracts frame from video and adds text overlay."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer
from PIL import Image, ImageDraw, ImageFont

app = typer.Typer()

# Fallback font paths for Urdu-compatible fonts
FONT_SEARCH_PATHS = [
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
    "/usr/share/fonts/google-noto/NotoNaskhArabic-Bold.ttf",
]


def extract_frame(video_path: Path, output_path: Path, timestamp: str = "00:00:03") -> None:
    """Extract a single frame from video at given timestamp."""
    cmd = [
        "ffmpeg", "-y", "-ss", timestamp, "-i", str(video_path),
        "-vframes", "1", "-q:v", "2", str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        typer.echo(f"Frame extraction failed: {result.stderr}", err=True)
        raise typer.Exit(1)


def find_font(template: dict) -> str | None:
    """Find a suitable font file."""
    font_file = template.get("font_file", "")
    if font_file and Path(font_file).exists():
        return font_file

    assets_font_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"
    for f in assets_font_dir.glob("*.ttf"):
        return str(f)

    for path in FONT_SEARCH_PATHS:
        if Path(path).exists():
            return path

    return None


def add_text_overlay(
    image_path: Path,
    title: str,
    output_path: Path,
    template: dict,
) -> None:
    """Add bold title text overlay to thumbnail image."""
    img = Image.open(image_path)

    # Darken the image slightly for text readability
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 100))
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    font_size = template.get("thumbnail_font_size", 72)
    font_color = template.get("thumbnail_font_color", "white")
    outline_color = template.get("thumbnail_outline_color", "black")

    font_path = find_font(template)
    if font_path:
        font = ImageFont.truetype(font_path, font_size)
    else:
        font = ImageFont.load_default()
        typer.echo("Warning: no Urdu-compatible font found, using default", err=True)

    # Center text with word wrapping
    max_width = int(img.width * 0.85)
    lines = _wrap_text(draw, title, font, max_width)
    text_block = "\n".join(lines)

    bbox = draw.multiline_textbbox((0, 0), text_block, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (img.width - text_w) // 2
    y = img.height - text_h - int(img.height * 0.15)

    # Draw outline
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            draw.multiline_text((x + dx, y + dy), text_block, font=font, fill=outline_color, align="center")

    # Draw main text
    draw.multiline_text((x, y), text_block, font=font, fill=font_color, align="center")

    img = img.convert("RGB")
    img.save(output_path, "JPEG", quality=95)
    typer.echo(f"Thumbnail saved to {output_path}")


def _wrap_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text to fit within max_width."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines


@app.command()
def create(
    title: str = typer.Option(..., help="Title text for the thumbnail"),
    template_file: Path = typer.Option(None, help="Template JSON file"),
    video: Path = typer.Option(None, help="Video to extract frame from"),
    frame: Path = typer.Option(None, help="Pre-extracted frame image"),
    timestamp: str = typer.Option("00:00:03", help="Timestamp to extract frame at"),
    output: Path = typer.Option(..., help="Output thumbnail path"),
) -> None:
    """Generate a YouTube thumbnail with text overlay."""
    template = {}
    if template_file and template_file.exists():
        template = json.loads(template_file.read_text(encoding="utf-8"))

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if frame and frame.exists():
        frame_path = frame.resolve()
    elif video and video.exists():
        frame_path = output.parent / "_temp_frame.jpg"
        extract_frame(video.resolve(), frame_path, timestamp)
    else:
        typer.echo("Error: provide --video or --frame", err=True)
        raise typer.Exit(1)

    add_text_overlay(frame_path, title, output, template)

    # Clean up temp frame
    temp_frame = output.parent / "_temp_frame.jpg"
    if temp_frame.exists() and frame_path == temp_frame:
        temp_frame.unlink()


if __name__ == "__main__":
    app()
