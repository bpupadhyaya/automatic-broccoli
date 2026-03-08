from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
from typing import Any

from yt_dlp import YoutubeDL

from app.config import settings


class YouTubeDownloadService:
    def download_best_video(self, youtube_url: str) -> dict[str, Any]:
        output_dir = self._resolve_output_dir()
        outtmpl = str(output_dir / "%(title).200B-%(id)s.%(ext)s")
        options = {
            "format": "bv*+ba/b",
            "noplaylist": True,
            "merge_output_format": "mp4",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": False,
        }

        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            downloaded_path = self._resolve_downloaded_path(info)

        if downloaded_path is None or not downloaded_path.exists():
            raise RuntimeError("Unable to resolve downloaded file path from yt-dlp output.")

        host_output_dir = self._resolve_host_output_dir()
        public_output_path = self._map_to_host_path(downloaded_path, output_dir, host_output_dir)
        stat = downloaded_path.stat()
        return {
            "youtube_url": youtube_url,
            "video_title": str(info.get("title") or downloaded_path.stem),
            "output_file_path": public_output_path,
            "output_dir": str(host_output_dir.resolve()) if host_output_dir is not None else str(output_dir.resolve()),
            "file_size_bytes": int(stat.st_size),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }

    def _resolve_output_dir(self) -> Path:
        output_dir = Path(settings.youtube_download_root).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        if not output_dir.is_dir():
            raise RuntimeError(f"Configured YouTube download path is not a directory: {output_dir}")
        if not os.access(output_dir, os.W_OK):
            raise RuntimeError(f"Configured YouTube download path is not writable: {output_dir}")
        return output_dir

    def _resolve_downloaded_path(self, info: dict[str, Any]) -> Path | None:
        requested = info.get("requested_downloads")
        if isinstance(requested, list):
            for item in requested:
                if not isinstance(item, dict):
                    continue
                filepath = item.get("filepath")
                if isinstance(filepath, str) and filepath.strip():
                    return Path(filepath)

        filepath = info.get("_filename")
        if isinstance(filepath, str) and filepath.strip():
            candidate = Path(filepath)
            if candidate.exists():
                return candidate

        title = str(info.get("title") or "").strip()
        video_id = str(info.get("id") or "").strip()
        if title and video_id:
            sanitized = self._sanitize_filename_part(title)
            root = Path(settings.youtube_download_root).expanduser()
            matches = sorted(
                root.glob(f"{sanitized}-{video_id}.*"),
                key=lambda path: path.stat().st_mtime,
                reverse=True,
            )
            if matches:
                return matches[0]

        return None

    def _resolve_host_output_dir(self) -> Path | None:
        configured = settings.youtube_download_host_path
        if not configured or not configured.strip():
            return None
        return Path(configured).expanduser()

    def _map_to_host_path(self, downloaded_path: Path, output_dir: Path, host_output_dir: Path | None) -> str:
        resolved_downloaded = downloaded_path.resolve()
        if host_output_dir is None:
            return str(resolved_downloaded)
        try:
            relative = resolved_downloaded.relative_to(output_dir.resolve())
            return str((host_output_dir.resolve() / relative).resolve())
        except ValueError:
            return str(resolved_downloaded)

    def _sanitize_filename_part(self, value: str) -> str:
        normalized = value.strip()
        normalized = re.sub(r"[\\/:*?\"<>|]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized[:200] if normalized else "video"
