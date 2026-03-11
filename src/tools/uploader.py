"""YouTube uploader — OAuth2 + YouTube Data API v3."""

import json
import sys
from pathlib import Path

import typer
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = typer.Typer()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PATH = Path(__file__).resolve().parent.parent.parent / ".youtube_token.json"
CLIENT_SECRETS_PATH = Path(__file__).resolve().parent.parent.parent / "client_secrets.json"


def get_credentials() -> Credentials:
    """Get or refresh YouTube API credentials."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if not CLIENT_SECRETS_PATH.exists():
            typer.echo(
                "Error: client_secrets.json not found.\n"
                "Download from Google Cloud Console → APIs → Credentials → OAuth 2.0\n"
                f"Expected at: {CLIENT_SECRETS_PATH}",
                err=True,
            )
            raise typer.Exit(1)

        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS_PATH), SCOPES)
        creds = flow.run_local_server(port=0)

    # Save token for next time
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    thumbnail_path: Path | None,
    is_shorts: bool,
    privacy: str,
) -> str:
    """Upload video to YouTube and return video ID."""
    creds = get_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22",  # People & Blogs
            "defaultLanguage": "ur",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    if is_shorts:
        body["snippet"]["title"] = f"{title} #Shorts"

    media = MediaFileUpload(str(video_path), chunksize=256 * 1024, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    typer.echo(f"Uploading {video_path.name}...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            typer.echo(f"Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    typer.echo(f"Upload complete! Video ID: {video_id}")
    typer.echo(f"URL: https://www.youtube.com/watch?v={video_id}")

    # Set thumbnail if provided
    if thumbnail_path and thumbnail_path.exists():
        typer.echo("Setting custom thumbnail...")
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumbnail_path)),
        ).execute()
        typer.echo("Thumbnail set successfully")

    return video_id


@app.command()
def upload(
    video: Path = typer.Option(..., help="Video file to upload"),
    title: str = typer.Option(..., help="Video title"),
    description: str = typer.Option("", help="Video description"),
    tags: str = typer.Option("", help="Comma-separated tags"),
    thumbnail: Path = typer.Option(None, help="Custom thumbnail image"),
    shorts: bool = typer.Option(False, help="Upload as YouTube Shorts"),
    privacy: str = typer.Option("private", help="Privacy: private, unlisted, public"),
) -> None:
    """Upload a video to YouTube."""
    if not video.exists():
        typer.echo(f"Error: video file not found: {video}", err=True)
        raise typer.Exit(1)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    video_id = upload_video(video, title, description, tag_list, thumbnail, shorts, privacy)
    typer.echo(f"\nDone! https://www.youtube.com/watch?v={video_id}")


@app.command("setup")
def setup_oauth() -> None:
    """Run OAuth2 setup flow for YouTube API."""
    typer.echo("Starting YouTube OAuth2 setup...")
    creds = get_credentials()
    typer.echo(f"Authenticated successfully! Token saved to {TOKEN_PATH}")


if __name__ == "__main__":
    app()
