"""Video assembly tool — FFmpeg-based clip + audio + subtitle compositor."""

import json
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer()


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of audio file using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", str(audio_path),
        ],
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


def concat_clips(clips_dir: Path, target_duration: float, resolution: tuple[int, int]) -> str:
    """Build FFmpeg filter for concatenating and looping clips to fill duration."""
    clips = sorted(clips_dir.glob("*.mp4"))
    if not clips:
        typer.echo("Error: no clips found in clips directory", err=True)
        raise typer.Exit(1)

    w, h = resolution
    inputs = []
    filter_parts = []

    for i, clip in enumerate(clips):
        inputs.extend(["-i", str(clip)])
        filter_parts.append(
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1[v{i}]"
        )

    # Concatenate all clips
    n = len(clips)
    concat_inputs = "".join(f"[v{i}]" for i in range(n))
    filter_parts.append(f"{concat_inputs}concat=n={n}:v=1:a=0[vconcat]")

    # Loop to fill audio duration
    filter_parts.append(
        f"[vconcat]loop=loop=-1:size=32767:start=0,"
        f"trim=duration={target_duration},setpts=PTS-STARTPTS[vout]"
    )

    return inputs, ";".join(filter_parts)


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
    # Parse resolution
    w, h = (int(x) for x in resolution.split("x"))

    # Load template
    template = {}
    if template_file and template_file.exists():
        template = json.loads(template_file.read_text(encoding="utf-8"))

    # Get audio duration
    duration = get_audio_duration(audio)
    typer.echo(f"Audio duration: {duration:.1f}s")

    # Build clip concatenation
    clip_inputs, clip_filter = concat_clips(clips_dir, duration, (w, h))

    # Build subtitle filter
    sub_filter = ""
    if subtitles and subtitles.exists():
        sub_filter = build_subtitle_filter(subtitles, template)

    # Build FFmpeg command
    cmd = ["ffmpeg", "-y"]
    cmd.extend(clip_inputs)
    cmd.extend(["-i", str(audio)])

    audio_input_idx = len([x for x in clip_inputs if x == "-i"])

    # Add music if provided
    music_input_idx = None
    if music and music.exists():
        cmd.extend(["-i", str(music)])
        music_input_idx = audio_input_idx + 1

    # Build filter complex
    full_filter = clip_filter
    if sub_filter:
        full_filter += f";[vout]{sub_filter}[vfinal]"
        video_out = "[vfinal]"
    else:
        video_out = "[vout]"

    # Audio mixing
    if music_input_idx is not None:
        full_filter += (
            f";[{music_input_idx}:a]volume={music_volume},"
            f"atrim=duration={duration},asetpts=PTS-STARTPTS[bgm];"
            f"[{audio_input_idx}:a][bgm]amix=inputs=2:duration=first[aout]"
        )
        audio_out = "[aout]"
    else:
        audio_out = f"{audio_input_idx}:a"

    cmd.extend(["-filter_complex", full_filter])
    cmd.extend(["-map", video_out, "-map", audio_out])
    cmd.extend([
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(output),
    ])

    output.parent.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Assembling video...")
    typer.echo(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        typer.echo(f"FFmpeg error:\n{result.stderr}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Video saved to {output}")


if __name__ == "__main__":
    app()
