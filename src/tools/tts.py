"""Text-to-Speech tool — Google TTS (free) or ElevenLabs (premium)."""

import sys
from pathlib import Path

from dotenv import load_dotenv
import typer

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

app = typer.Typer()


def google_tts(text: str, output: Path, lang: str = "ur") -> None:
    """Generate speech using Google TTS (free, no API key)."""
    from gtts import gTTS

    tts = gTTS(text=text, lang=lang, slow=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    tts.save(str(output))
    typer.echo(f"Google TTS saved to {output}")


def elevenlabs_tts(text: str, output: Path, api_key: str, voice_id: str) -> None:
    """Generate speech using ElevenLabs API."""
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id="eleven_multilingual_v2",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "wb") as f:
        for chunk in audio:
            f.write(chunk)
    typer.echo(f"ElevenLabs TTS saved to {output}")


@app.command()
def generate(
    text: str = typer.Option(None, help="Text to convert to speech"),
    text_file: Path = typer.Option(None, help="File containing text to convert"),
    engine: str = typer.Option("google", help="TTS engine: google or elevenlabs"),
    lang: str = typer.Option("ur", help="Language code for Google TTS"),
    output: Path = typer.Option(..., help="Output audio file path"),
    api_key: str = typer.Option(None, envvar="ELEVENLABS_API_KEY"),
    voice_id: str = typer.Option("pNInz6obpgDQGcFmaJgB", envvar="ELEVENLABS_VOICE_ID"),
) -> None:
    """Generate speech from text using Google TTS or ElevenLabs."""
    if text is None and text_file is None:
        typer.echo("Error: provide --text or --text-file", err=True)
        raise typer.Exit(1)

    content = text if text else text_file.read_text(encoding="utf-8")

    if not content.strip():
        typer.echo("Error: empty text input", err=True)
        raise typer.Exit(1)

    if engine == "elevenlabs":
        if not api_key:
            typer.echo("Error: ELEVENLABS_API_KEY required for elevenlabs engine", err=True)
            raise typer.Exit(1)
        elevenlabs_tts(content, output, api_key, voice_id)
    else:
        google_tts(content, output, lang)


if __name__ == "__main__":
    app()
