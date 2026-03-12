"""Video assembly tool — FFmpeg-based clip + audio + subtitle compositor."""

import json
import subprocess
from pathlib import Path

import typer

app = typer.Typer()

TARGET_FPS = 30


def get_media_duration(path: Path) -> float:
    """Get duration of a media file using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def build_subtitle_filter(subtitles_path: Path, template: dict) -> str:
    """Build FFmpeg drawtext filter chain from subtitle JSON."""
    subs = json.loads(subtitles_path.read_text(encoding="utf-8"))
    font_size = template.get("subtitle_font_size", 48)
    font_color = template.get("subtitle_font_color", "white")
    outline_color = template.get("subtitle_outline_color", "black")
    font_file = template.get("font_file", "")

    filters = []
    for seg in subs:
        start = seg["start"]
        end = seg["end"]
        text = seg["text"].replace("'", "\u2019").replace(":", "\\:")
        font_arg = f":fontfile={font_file}" if font_file else ""
        filters.append(
            f"drawtext=text='{text}':fontsize={font_size}:fontcolor={font_color}"
            f":borderw=3:bordercolor={outline_color}"
            f":x=(w-text_w)/2:y=h-h/5"
            f"{font_arg}"
            f":enable='between(t,{start},{end})'"
        )
    return ",".join(filters)


def normalize_clips(clips_dir: Path, w: int, h: int) -> list[Path]:
    """Re-encode all clips to identical format for reliable concatenation."""
    clips = sorted(clips_dir.glob("*.mp4"))
    if not clips:
        typer.echo("Error: no clips found in clips directory", err=True)
        raise typer.Exit(1)

    norm_dir = clips_dir / "_normalized"
    norm_dir.mkdir(exist_ok=True)

    normalized = []
    for i, clip in enumerate(clips):
        out = norm_dir / f"clip_{i:03d}.ts"
        if out.exists():
            normalized.append(out)
            continue

        cmd = [
            "ffmpeg", "-y", "-i", str(clip.resolve()),
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                   f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,"
                   f"fps={TARGET_FPS}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an",  # strip audio from clips
            "-f", "mpegts",
            str(out),
        ]
        typer.echo(f"Normalizing clip {i+1}/{len(clips)}: {clip.name}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            typer.echo(f"Warning: failed to normalize {clip.name}: {result.stderr[-200:]}", err=True)
            continue
        normalized.append(out)

    return normalized


def concat_normalized(clips: list[Path], target_duration: float, output: Path) -> None:
    """Concatenate normalized .ts clips using concat protocol, looping to fill duration."""
    # Build concat string repeating clips to exceed target duration
    accumulated = 0.0
    parts = []
    durations = [(c, get_media_duration(c)) for c in clips]

    while accumulated < target_duration:
        for clip, dur in durations:
            parts.append(str(clip.resolve()))
            accumulated += dur
            if accumulated >= target_duration:
                break

    concat_input = "concat:" + "|".join(parts)

    cmd = [
        "ffmpeg", "-y",
        "-i", concat_input,
        "-t", str(target_duration),
        "-c", "copy",
        "-f", "mpegts",
        str(output),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        typer.echo(f"Concat error: {result.stderr[-300:]}", err=True)
        raise typer.Exit(1)


@app.command()
def assemble(
    clips_dir: Path = typer.Option(..., help="Directory containing video clips"),
    audio: Path = typer.Option(..., help="Voice-over audio file"),
    subtitles: Path = typer.Option(None, help="Subtitle JSON file"),
    template_file: Path = typer.Option(None, help="Template JSON file"),
    music: Path = typer.Option(None, help="Background music file"),
    music_volume: float = typer.Option(0.15, help="Background music volume (0-1)"),
    output: Path = typer.Option(..., help="Output video file path"),
    resolution: str = typer.Option("1080x1920", help="WxH resolution"),
) -> None:
    """Assemble final video from clips, audio, subtitles, and music."""
    w, h = (int(x) for x in resolution.split("x"))
    clips_dir = clips_dir.resolve()
    audio = audio.resolve()
    output = output.resolve()

    template = {}
    if template_file and template_file.exists():
        template = json.loads(template_file.read_text(encoding="utf-8"))

    duration = get_media_duration(audio)
    typer.echo(f"Audio duration: {duration:.1f}s")

    # Step 1: Normalize all clips to same resolution/fps/codec
    typer.echo("Step 1: Normalizing clips...")
    normalized = normalize_clips(clips_dir, w, h)
    if not normalized:
        typer.echo("Error: no clips could be normalized", err=True)
        raise typer.Exit(1)

    # Step 2: Concatenate normalized clips (fast, stream copy)
    typer.echo("Step 2: Concatenating clips...")
    concat_output = clips_dir / "_concat.ts"
    concat_normalized(normalized, duration, concat_output)

    # Step 3: Final assembly — add subtitles + audio + music
    typer.echo("Step 3: Final assembly...")
    cmd = ["ffmpeg", "-y"]
    cmd.extend(["-i", str(concat_output)])  # input 0: concatenated video
    cmd.extend(["-i", str(audio)])  # input 1: voice-over

    music_idx = None
    if music and music.exists():
        cmd.extend(["-i", str(music.resolve())])
        music_idx = 2

    # Subtitle filter
    sub_filter = ""
    if subtitles and subtitles.exists():
        sub_filter = build_subtitle_filter(subtitles.resolve(), template)

    if music_idx is not None:
        vf = sub_filter if sub_filter else "null"
        afilter = (
            f"[{music_idx}:a]volume={music_volume},atrim=duration={duration},"
            f"asetpts=PTS-STARTPTS[bgm];[1:a][bgm]amix=inputs=2:duration=first[aout]"
        )
        cmd.extend(["-filter_complex", f"[0:v]{vf}[vout];{afilter}"])
        cmd.extend(["-map", "[vout]", "-map", "[aout]"])
    else:
        if sub_filter:
            cmd.extend(["-vf", sub_filter])
        cmd.extend(["-map", "0:v", "-map", "1:a"])

    cmd.extend([
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output),
    ])

    output.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Cleanup temp files
    for f in (clips_dir / "_normalized").glob("*.ts"):
        f.unlink(missing_ok=True)
    (clips_dir / "_normalized").rmdir()
    concat_output.unlink(missing_ok=True)

    if result.returncode != 0:
        typer.echo(f"FFmpeg error:\n{result.stderr[-500:]}", err=True)
        raise typer.Exit(1)

    size_mb = output.stat().st_size / (1024 * 1024)
    typer.echo(f"Video saved to {output} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    app()
