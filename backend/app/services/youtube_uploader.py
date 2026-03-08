from __future__ import annotations

from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.config import settings


class YouTubeUploaderService:
    """Upload generated remix videos to YouTube using pre-provisioned OAuth credentials."""

    _SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        privacy_status: str = "private",
    ) -> dict:
        client_secret_path = settings.youtube_client_secrets_path
        token_path = settings.youtube_token_path
        if not client_secret_path or not token_path:
            raise RuntimeError(
                "YouTube upload is not configured. Set YOUTUBE_CLIENT_SECRETS_PATH and YOUTUBE_TOKEN_PATH."
            )

        credentials_file = Path(token_path).expanduser()
        if not credentials_file.exists():
            raise RuntimeError(f"YouTube token file not found: {credentials_file}")

        client_secret_file = Path(client_secret_path).expanduser()
        if not client_secret_file.exists():
            raise RuntimeError(f"YouTube client secrets file not found: {client_secret_file}")

        credentials = Credentials.from_authorized_user_file(str(credentials_file), self._SCOPES)
        if not credentials.valid:
            raise RuntimeError(
                "YouTube OAuth token is invalid or expired. Refresh credentials in YOUTUBE_TOKEN_PATH."
            )

        youtube = build("youtube", "v3", credentials=credentials)
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "categoryId": "10",
                },
                "status": {"privacyStatus": privacy_status},
            },
            media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True),
        )
        response = request.execute()
        video_id = response.get("id")
        return {
            "video_id": video_id,
            "watch_url": (f"https://www.youtube.com/watch?v={video_id}" if video_id else None),
            "privacy_status": privacy_status,
        }
