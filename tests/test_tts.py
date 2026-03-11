"""Tests for TTS tool."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from src.tools.tts import app, google_tts

runner = CliRunner()


def test_google_tts_creates_file(tmp_path: Path) -> None:
    """Google TTS generates an mp3 file."""
    output = tmp_path / "test.mp3"
    google_tts("Hello world test", output, lang="en")
    assert output.exists()
    assert output.stat().st_size > 0


def test_cli_requires_text_or_file() -> None:
    """CLI errors when neither --text nor --text-file is provided."""
    result = runner.invoke(app, ["--output", "/tmp/test.mp3"])
    assert result.exit_code != 0


def test_cli_errors_on_empty_text(tmp_path: Path) -> None:
    """CLI errors on empty text input."""
    result = runner.invoke(app, ["--text", "   ", "--output", str(tmp_path / "out.mp3")])
    assert result.exit_code != 0


def test_cli_google_tts(tmp_path: Path) -> None:
    """CLI generates audio with Google TTS engine."""
    output = tmp_path / "voice.mp3"
    result = runner.invoke(app, [
        "--text", "Testing one two three",
        "--engine", "google",
        "--lang", "en",
        "--output", str(output),
    ])
    assert result.exit_code == 0
    assert output.exists()
