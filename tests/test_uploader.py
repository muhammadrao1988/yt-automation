"""Tests for YouTube uploader tool."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from src.tools.uploader import app

runner = CliRunner()


def test_upload_requires_existing_video(tmp_path: Path) -> None:
    """Upload command fails gracefully for non-existent video."""
    result = runner.invoke(app, [
        "upload",
        "--video", str(tmp_path / "nonexistent.mp4"),
        "--title", "Test",
    ])
    assert result.exit_code != 0


@patch("src.tools.uploader.get_credentials")
@patch("src.tools.uploader.build")
def test_upload_calls_youtube_api(mock_build: MagicMock, mock_creds: MagicMock, tmp_path: Path) -> None:
    """Upload command calls YouTube API with correct parameters."""
    # Create a fake video file
    video = tmp_path / "test.mp4"
    video.write_bytes(b"\x00" * 1024)

    mock_youtube = MagicMock()
    mock_build.return_value = mock_youtube

    # Mock the insert chain
    mock_request = MagicMock()
    mock_request.next_chunk.return_value = (None, {"id": "test123"})
    mock_youtube.videos.return_value.insert.return_value = mock_request

    result = runner.invoke(app, [
        "upload",
        "--video", str(video),
        "--title", "Test Video",
        "--tags", "test,video",
    ])

    assert result.exit_code == 0
    assert "test123" in result.output
