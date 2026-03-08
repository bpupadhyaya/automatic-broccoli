from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

from yt_dlp import YoutubeDL

from app.config import settings
from app.models.project import Project


class LocalQuickRemixService:
    """Download source videos and build a local remixed MP4 artifact."""

    def run(self, project: Project, local_output_dir: str | None = None) -> dict:
        output_dir = self._resolve_output_dir(project.id, local_output_dir)
        downloads_dir = output_dir / "downloads"
        clips_dir = output_dir / "clips"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        clips_dir.mkdir(parents=True, exist_ok=True)

        target_video = self._download_youtube_video(str(project.target_original_video_url), downloads_dir / "target")
        example_original = self._download_youtube_video(str(project.example_original_video_url), downloads_dir / "example_original")
        example_remix = self._download_youtube_video(str(project.example_remix_video_url), downloads_dir / "example_remix")

        segment_specs = [
            ("target_intro", target_video, 0, 12),
            ("example_original_mid", example_original, 8, 8),
            ("example_remix_hook", example_remix, 12, 12),
        ]

        segment_paths: list[Path] = []
        for idx, (name, source_path, start_sec, duration_sec) in enumerate(segment_specs, start=1):
            segment_path = clips_dir / f"{idx:02d}_{name}.mp4"
            self._run_command(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(start_sec),
                    "-i",
                    str(source_path),
                    "-t",
                    str(duration_sec),
                    "-vf",
                    "scale=1280:720:force_original_aspect_ratio=decrease,"
                    "pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                    "-r",
                    "30",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "22",
                    "-c:a",
                    "aac",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    str(segment_path),
                ]
            )
            segment_paths.append(segment_path)

        concat_list = clips_dir / "concat_list.txt"
        concat_list.write_text("\n".join([f"file '{path.as_posix()}'" for path in segment_paths]), encoding="utf-8")

        output_video_path = output_dir / f"project_{project.id}_quick_remix.mp4"
        self._run_command(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "21",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                str(output_video_path),
            ]
        )

        return {
            "output_dir": str(output_dir.resolve()),
            "output_video_path": str(output_video_path.resolve()),
            "download_filename": output_video_path.name,
            "source_video_paths": {
                "target_original": str(target_video.resolve()),
                "example_original": str(example_original.resolve()),
                "example_remix": str(example_remix.resolve()),
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def _resolve_output_dir(self, project_id: int, local_output_dir: str | None) -> Path:
        base_root = Path(settings.quick_output_root).expanduser()
        if local_output_dir:
            candidate = Path(local_output_dir).expanduser()
            if not candidate.is_absolute():
                candidate = base_root / candidate
            output_dir = candidate
        else:
            output_dir = base_root / f"project_{project_id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _download_youtube_video(self, url: str, output_stem: Path) -> Path:
        output_stem.parent.mkdir(parents=True, exist_ok=True)
        outtmpl = f"{output_stem.as_posix()}.%(ext)s"
        with YoutubeDL(
            {
                "format": "mp4/bestvideo+bestaudio/best",
                "noplaylist": True,
                "merge_output_format": "mp4",
                "quiet": True,
                "no_warnings": True,
                "outtmpl": outtmpl,
            }
        ) as ydl:
            ydl.download([url])

        candidates = sorted(
            output_stem.parent.glob(f"{output_stem.name}.*"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise RuntimeError(f"Unable to download source video from {url}")

        preferred = [path for path in candidates if path.suffix.lower() == ".mp4"]
        return preferred[0] if preferred else candidates[0]

    def _run_command(self, command: list[str]) -> None:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(f"Command failed: {' '.join(command)}\n{stderr[:2000]}")
