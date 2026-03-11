"""Tests for video maker tool."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.tools.video_maker import build_subtitle_filter


def test_build_subtitle_filter(tmp_path: Path) -> None:
    """Subtitle filter generates valid FFmpeg drawtext chain."""
    subs = [
        {"start": 0.0, "end": 3.5, "text": "Hello world"},
        {"start": 3.5, "end": 7.0, "text": "Second line"},
    ]
    sub_file = tmp_path / "subs.json"
    sub_file.write_text(json.dumps(subs))

    template = {"subtitle_font_size": 48, "subtitle_font_color": "white"}
    result = build_subtitle_filter(sub_file, template)

    assert "drawtext=" in result
    assert "Hello world" in result
    assert "Second line" in result
    assert "between(t,0.0,3.5)" in result
    assert "between(t,3.5,7.0)" in result


def test_empty_subtitles(tmp_path: Path) -> None:
    """Empty subtitle list produces empty filter."""
    sub_file = tmp_path / "subs.json"
    sub_file.write_text("[]")

    result = build_subtitle_filter(sub_file, {})
    assert result == ""
