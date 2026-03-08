from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

from yt_dlp import YoutubeDL

from app.config import settings


class YouTubeDownloadService:
    def download_best_video(self, youtube_url: str) -> dict[str, Any]:
        output_dir = self._resolve_output_dir()
        outtmpl = str(output_dir / "%(title).200B-%(id)s.%(ext)s")
        options = {
            "format": "bestvideo*+bestaudio/best",
            "noplaylist": True,
            "merge_output_format": "mp4",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": False,
        }

        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            downloaded_path = self._resolve_downloaded_path(info, output_dir=output_dir)

        if downloaded_path is None or not downloaded_path.exists():
            raise RuntimeError("Unable to resolve downloaded file path from yt-dlp output.")
        if not self._has_video_stream(downloaded_path):
            raise RuntimeError("Downloaded media does not contain a video stream.")

        compatible_path = self._transcode_to_quicktime_compatible_mp4(downloaded_path)

        host_output_dir = self._resolve_host_output_dir()
        public_output_path = self._map_to_host_path(compatible_path, output_dir, host_output_dir)
        stat = compatible_path.stat()
        return {
            "youtube_url": youtube_url,
            "video_title": str(info.get("title") or compatible_path.stem),
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

    def _resolve_downloaded_path(self, info: dict[str, Any], output_dir: Path) -> Path | None:
        candidates = self._collect_download_candidates(info, output_dir)
        if not candidates:
            return None

        scored: list[tuple[int, int, float, Path]] = []
        for candidate in candidates:
            has_video = self._has_video_stream(candidate)
            mp4_bonus = 2 if candidate.suffix.lower() == ".mp4" else 0
            video_bonus = 5 if has_video else 0
            file_size = int(candidate.stat().st_size)
            scored.append((video_bonus + mp4_bonus, file_size, candidate.stat().st_mtime, candidate))

        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return scored[0][3]

    def _collect_download_candidates(self, info: dict[str, Any], output_dir: Path) -> list[Path]:
        candidates: list[Path] = []

        requested = info.get("requested_downloads")
        if isinstance(requested, list):
            for item in requested:
                if not isinstance(item, dict):
                    continue
                filepath = item.get("filepath")
                if isinstance(filepath, str) and filepath.strip():
                    candidate = Path(filepath)
                    if candidate.exists() and candidate.is_file():
                        candidates.append(candidate)

        filepath = info.get("filepath")
        if isinstance(filepath, str) and filepath.strip():
            candidate = Path(filepath)
            if candidate.exists() and candidate.is_file():
                candidates.append(candidate)

        filepath = info.get("_filename")
        if isinstance(filepath, str) and filepath.strip():
            candidate = Path(filepath)
            if candidate.exists() and candidate.is_file():
                candidates.append(candidate)

        title = str(info.get("title") or "").strip()
        video_id = str(info.get("id") or "").strip()
        if title and video_id:
            sanitized = self._sanitize_filename_part(title)
            matches = output_dir.glob(f"{sanitized}-{video_id}.*")
            for match in matches:
                if match.exists() and match.is_file():
                    candidates.append(match)

        dedup: dict[Path, Path] = {}
        for candidate in candidates:
            resolved = candidate.resolve()
            dedup[resolved] = resolved
        return list(dedup.values())

    def _has_video_stream(self, media_path: Path) -> bool:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "json",
                str(media_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False
        try:
            payload = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return False
        streams = payload.get("streams")
        return isinstance(streams, list) and len(streams) > 0

    def _transcode_to_quicktime_compatible_mp4(self, source_path: Path) -> Path:
        final_path = source_path.with_suffix(".mp4")
        if final_path.resolve() == source_path.resolve():
            temp_path = source_path.with_name(f"{source_path.stem}.qt_tmp.mp4")
        else:
            temp_path = final_path

        if temp_path.exists():
            temp_path.unlink()

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-profile:v",
            "high",
            "-level",
            "4.1",
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(temp_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to encode MP4 for QuickTime/YouTube compatibility: {result.stderr.strip()}")

        if temp_path.resolve() != final_path.resolve():
            temp_path.replace(final_path)

        if source_path.resolve() != final_path.resolve() and source_path.exists():
            source_path.unlink()

        if not final_path.exists() or not self._has_video_stream(final_path):
            raise RuntimeError("Output MP4 does not contain a playable video stream.")

        return final_path

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
