"""Application configuration loaded from .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    pexels_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "pNInz6obpgDQGcFmaJgB"
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    tts_engine: str = "google"  # "google" or "elevenlabs"

    output_dir: Path = PROJECT_ROOT / "output"
    assets_dir: Path = PROJECT_ROOT / "assets"
    templates_dir: Path = PROJECT_ROOT / "templates"

    # Video defaults
    shorts_resolution: tuple[int, int] = (1080, 1920)
    landscape_resolution: tuple[int, int] = (1920, 1080)
    default_music_volume: float = 0.15

    model_config = {"env_file": PROJECT_ROOT / ".env", "env_file_encoding": "utf-8"}


settings = Settings()
