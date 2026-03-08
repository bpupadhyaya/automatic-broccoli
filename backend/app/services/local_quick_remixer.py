from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
import random
import re
from pathlib import Path
import subprocess
from typing import Any, Callable

import numpy as np
import cv2
from yt_dlp import YoutubeDL

from app.config import settings
from app.models.project import Project


class LocalQuickRemixService:
    """Learn remix patterns from example pair and apply them to the target video."""

    _NAME_POOL = {
        "english": {
            "female": ["Ariana Vale", "Lena Frost", "Clara Wynn", "Sophie Hale", "Evelyn Chase"],
            "male": ["Liam Cross", "Noah Blake", "Ethan Vale", "Caleb Shaw", "Mason Reed"],
        },
        "nepali": {
            "female": ["Sita Thapa", "Maya Karki", "Nisha Gurung", "Anisha Rai", "Prakriti Shah"],
            "male": ["Aayush Lama", "Rohan Khatri", "Bikash Rai", "Suman Shrestha", "Niraj Gurung"],
        },
        "hindi": {
            "female": ["Aditi Kapoor", "Kiara Mehra", "Riya Malhotra", "Sara Anand", "Ira Bedi"],
            "male": ["Arjun Malhotra", "Kabir Anand", "Rohan Kapoor", "Vivaan Mehta", "Yash Batra"],
        },
    }

    def run(
        self,
        project: Project,
        local_output_dir: str | None = None,
        remix_profile: str = "english",
        cast_preset: str = "mixed",
        heritage_mode: str = "preserve",
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict:
        processing_steps: list[dict[str, Any]] = []
        self._append_processing_step(
            processing_steps, "Initialize", "Preparing output workspace.", 0.02, callback=progress_callback
        )
        output_dir = self._resolve_output_dir(project.id, local_output_dir)
        downloads_dir = output_dir / "downloads"
        clips_dir = output_dir / "clips"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        clips_dir.mkdir(parents=True, exist_ok=True)

        self._append_processing_step(
            processing_steps,
            "Download Sources",
            "Downloading target original video.",
            0.08,
            callback=progress_callback,
        )
        target_video = self._download_youtube_video(str(project.target_original_video_url), downloads_dir / "target")
        self._append_processing_step(
            processing_steps,
            "Download Sources",
            "Downloading example original video.",
            0.16,
            callback=progress_callback,
        )
        example_original = self._download_youtube_video(str(project.example_original_video_url), downloads_dir / "example_original")
        self._append_processing_step(
            processing_steps,
            "Download Sources",
            "Downloading example remix video.",
            0.24,
            callback=progress_callback,
        )
        example_remix = self._download_youtube_video(str(project.example_remix_video_url), downloads_dir / "example_remix")

        self._append_processing_step(
            processing_steps,
            "Analyze Target",
            "Probing target structure for duration, frame rate, and render planning.",
            0.30,
            callback=progress_callback,
        )
        target_probe = self._probe_video(target_video)
        self._append_processing_step(
            processing_steps,
            "Learn Transformation",
            "Learning visual/audio deltas from example original to example remix.",
            0.40,
            callback=progress_callback,
        )
        transformation_profile = self._learn_transformation_profile(
            example_original=example_original,
            example_remix=example_remix,
            remix_profile=remix_profile,
        )
        self._append_processing_step(
            processing_steps,
            "Cast Synthesis",
            "Generating fictitious cast identities and heritage proportions.",
            0.50,
            callback=progress_callback,
        )
        cast_plan = self._build_cast_plan(
            project=project,
            remix_profile=remix_profile,
            cast_preset=cast_preset,
            heritage_mode=heritage_mode,
            target_duration=target_probe["duration_sec"],
        )
        self._append_processing_step(
            processing_steps,
            "Segment Planning",
            "Building shot-level remix timeline and performer assignment.",
            0.58,
            callback=progress_callback,
        )
        segment_plan = self._build_segment_plan(
            project_id=project.id,
            target_duration=target_probe["duration_sec"],
            transformation_profile=transformation_profile,
            cast_plan=cast_plan,
        )
        self._append_processing_step(
            processing_steps,
            "Render Segments",
            "Rendering transformed target segments with actor-style and voice filters.",
            0.62,
            callback=progress_callback,
        )
        output_video_path = output_dir / f"project_{project.id}_quick_remix.mp4"
        self._render_full_length_remix(
            target_video=target_video,
            output_video_path=output_video_path,
            example_remix_video=example_remix,
            transformation_profile=transformation_profile,
            cast_plan=cast_plan,
            segment_plan=segment_plan,
            processing_steps=processing_steps,
            progress_callback=progress_callback,
        )
        self._append_processing_step(
            processing_steps,
            "Compose Output",
            "Packaging full-length transformed stream into final remix export.",
            0.95,
            callback=progress_callback,
        )
        self._append_processing_step(
            processing_steps,
            "Finalize",
            "Finalizing remix metadata, status update, and download readiness.",
            0.98,
            callback=progress_callback,
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
            "processing_mode": "example_learned_transform",
            "render_strategy": "full_length_continuous_actor_transform",
            "transformation_profile": transformation_profile,
            "cast_plan": cast_plan,
            "segment_plan": segment_plan,
            "processing_steps": processing_steps,
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

    def _compute_worker_threads(self) -> int:
        host_cpus = os.cpu_count() or 10
        return max(10, min(int(host_cpus), 64))

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

    def _probe_video(self, video_path: Path) -> dict[str, float]:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=width,height,r_frame_rate",
                "-of",
                "json",
                str(video_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {"duration_sec": 120.0, "width": 1280.0, "height": 720.0, "fps": 30.0}

        try:
            payload = json.loads(result.stdout or "{}")
            streams = payload.get("streams") or []
            stream = streams[0] if streams else {}
            duration = float((payload.get("format") or {}).get("duration") or 120.0)
            width = float(stream.get("width") or 1280)
            height = float(stream.get("height") or 720)
            fps_value = str(stream.get("r_frame_rate") or "30/1")
            num, den = fps_value.split("/", 1)
            fps = float(num) / max(float(den), 1.0)
            return {
                "duration_sec": max(duration, 10.0),
                "width": width,
                "height": height,
                "fps": self._clamp(fps, 12.0, 120.0),
            }
        except Exception:
            return {"duration_sec": 120.0, "width": 1280.0, "height": 720.0, "fps": 30.0}

    def _sample_signal_stats(self, video_path: Path) -> dict[str, float]:
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostats",
                "-i",
                str(video_path),
                "-vf",
                "fps=1,scale=320:-1,signalstats,metadata=print",
                "-an",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        text = f"{result.stdout}\n{result.stderr}"
        yavg = self._average(self._extract_values(text, r"lavfi\.signalstats\.YAVG=([-0-9.]+)"), 120.0)
        satavg = self._average(self._extract_values(text, r"lavfi\.signalstats\.SATAVG=([-0-9.]+)"), 120.0)
        ylow = self._average(self._extract_values(text, r"lavfi\.signalstats\.YLOW=([-0-9.]+)"), 16.0)
        yhigh = self._average(self._extract_values(text, r"lavfi\.signalstats\.YHIGH=([-0-9.]+)"), 235.0)
        uavg = self._average(self._extract_values(text, r"lavfi\.signalstats\.UAVG=([-0-9.]+)"), 128.0)
        vavg = self._average(self._extract_values(text, r"lavfi\.signalstats\.VAVG=([-0-9.]+)"), 128.0)
        return {
            "yavg": yavg,
            "satavg": satavg,
            "ylow": ylow,
            "yhigh": yhigh,
            "uavg": uavg,
            "vavg": vavg,
        }

    def _sample_audio_drive(self, video_path: Path) -> float:
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostats",
                "-i",
                str(video_path),
                "-af",
                "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
                "-vn",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        text = f"{result.stdout}\n{result.stderr}"
        rms_db = self._extract_values(text, r"lavfi\.astats\.Overall\.RMS_level=([-0-9.]+)")
        if not rms_db:
            return 0.16

        linear = [10 ** (value / 20.0) for value in rms_db if value < 0]
        if not linear:
            return 0.16
        return self._clamp(self._average(linear, 0.16), 0.02, 0.9)

    def _estimate_scene_rate(self, video_path: Path, duration_sec: float) -> float:
        if duration_sec <= 0:
            return 12.0
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostats",
                "-i",
                str(video_path),
                "-vf",
                "select=gt(scene\\,0.35),showinfo",
                "-an",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        text = f"{result.stdout}\n{result.stderr}"
        cut_count = len(re.findall(r"showinfo", text))
        return self._clamp((cut_count / max(duration_sec, 1.0)) * 60.0, 6.0, 35.0)

    def _learn_transformation_profile(self, example_original: Path, example_remix: Path, remix_profile: str) -> dict[str, float | str]:
        original_probe = self._probe_video(example_original)
        remix_probe = self._probe_video(example_remix)
        original_signal = self._sample_signal_stats(example_original)
        remix_signal = self._sample_signal_stats(example_remix)
        original_audio_drive = self._sample_audio_drive(example_original)
        remix_audio_drive = self._sample_audio_drive(example_remix)
        remix_scene_rate = self._estimate_scene_rate(example_remix, remix_probe["duration_sec"])

        brightness_shift = self._clamp((remix_signal["yavg"] - original_signal["yavg"]) / 255.0, -0.16, 0.16)
        original_dynamic = max(original_signal["yhigh"] - original_signal["ylow"], 1.0)
        remix_dynamic = max(remix_signal["yhigh"] - remix_signal["ylow"], 1.0)
        contrast_gain = self._clamp(remix_dynamic / original_dynamic, 0.85, 1.4)
        saturation_gain = self._clamp(remix_signal["satavg"] / max(original_signal["satavg"], 1.0), 0.8, 1.7)
        hue_shift = self._clamp((remix_signal["uavg"] - original_signal["uavg"]) * 0.2, -18.0, 18.0)

        duration_ratio = self._clamp(
            original_probe["duration_sec"] / max(remix_probe["duration_sec"], 1.0),
            0.9,
            1.18,
        )
        audio_ratio = self._clamp(remix_audio_drive / max(original_audio_drive, 0.01), 0.8, 1.4)
        tempo_multiplier = self._clamp((duration_ratio * 0.6) + (audio_ratio * 0.4), 0.92, 1.12)

        style_prior = self._profile_prior(remix_profile)
        shot_interval = self._clamp(60.0 / max(remix_scene_rate, 8.0), 1.4, 4.8)

        return {
            "remix_profile": remix_profile,
            "brightness_shift": self._clamp(brightness_shift + style_prior["brightness_shift"], -0.2, 0.2),
            "contrast_gain": self._clamp(contrast_gain * style_prior["contrast_gain"], 0.85, 1.5),
            "saturation_gain": self._clamp(saturation_gain * style_prior["saturation_gain"], 0.8, 1.8),
            "hue_shift": self._clamp(hue_shift + style_prior["hue_shift"], -24.0, 24.0),
            "tempo_multiplier": tempo_multiplier,
            "audio_drive": self._clamp(remix_audio_drive, 0.03, 1.0),
            "target_shot_interval_sec": shot_interval,
            "example_scene_rate_per_min": remix_scene_rate,
            "example_original_duration_sec": round(original_probe["duration_sec"], 3),
            "example_remix_duration_sec": round(remix_probe["duration_sec"], 3),
            "duration_ratio_original_to_remix": round(duration_ratio, 4),
            "learning_mode": "example_original_to_remix_delta_profile",
        }

    def _profile_prior(self, remix_profile: str) -> dict[str, float]:
        profile = remix_profile.lower().strip()
        if profile == "nepali":
            return {"brightness_shift": 0.02, "contrast_gain": 1.04, "saturation_gain": 1.06, "hue_shift": 3.0}
        if profile == "hindi":
            return {"brightness_shift": 0.03, "contrast_gain": 1.1, "saturation_gain": 1.15, "hue_shift": 6.0}
        return {"brightness_shift": 0.01, "contrast_gain": 1.07, "saturation_gain": 1.12, "hue_shift": 0.0}

    def _build_cast_plan(
        self,
        project: Project,
        remix_profile: str,
        cast_preset: str,
        heritage_mode: str,
        target_duration: float,
    ) -> list[dict[str, Any]]:
        rng = random.Random(project.id * 7919)
        heritage_weights = self._heritage_weights(remix_profile, heritage_mode)
        leads = 2 if cast_preset == "mixed" else 1
        dancers = self._infer_dancer_count(project, target_duration)
        performer_count = max(4, leads + dancers)
        female_ratio = {"female": 0.78, "male": 0.24, "mixed": 0.52}.get(cast_preset, 0.52)
        female_target = int(round(performer_count * female_ratio))
        female_target = self._clamp_int(female_target, 1, performer_count - 1)

        cast: list[dict[str, Any]] = []
        used_names: set[str] = set()
        for index in range(performer_count):
            is_lead = index < leads
            role = "lead_vocal_performer" if is_lead else "dance_performer"
            if cast_preset == "female":
                gender = "female"
            elif cast_preset == "male":
                gender = "male"
            elif is_lead:
                gender = "female" if index % 2 == 0 else "male"
            else:
                current_female = sum(1 for item in cast if item["gender"] == "female")
                remaining = performer_count - index
                needed_female = max(female_target - current_female, 0)
                if needed_female >= remaining:
                    gender = "female"
                elif needed_female <= 0:
                    gender = "male"
                else:
                    gender = "female" if rng.random() < (needed_female / remaining) else "male"

            heritage = self._pick_weighted_heritage(heritage_weights, rng)
            name = self._next_name(heritage=heritage, gender=gender, rng=rng, used_names=used_names)
            age = rng.randint(18, 25) if gender == "female" else rng.randint(18, 30)
            appearance = self._appearance_descriptor(heritage=heritage, gender=gender)

            cast.append(
                {
                    "character_id": f"char_{index + 1:02d}",
                    "name": name,
                    "role": role,
                    "gender": gender,
                    "age": age,
                    "heritage": heritage,
                    "appearance": appearance,
                    "profile_alignment": remix_profile,
                }
            )
        return cast

    def _infer_dancer_count(self, project: Project, target_duration: float) -> int:
        base = int(max(3, min(10, target_duration // 22)))
        energy = (project.energy_level or "").lower()
        dance_style = (project.dance_style or "").lower()
        if "high" in energy or "driving" in str(project.beat_intensity).lower():
            base += 1
        if "low" in energy or "minimal" in dance_style:
            base -= 1
        if "folk" in dance_style or "bollywood" in dance_style:
            base += 1
        return self._clamp_int(base, 3, 12)

    def _heritage_weights(self, remix_profile: str, heritage_mode: str) -> dict[str, float]:
        profile = remix_profile.lower().strip()
        if heritage_mode == "swap_to_english":
            return {"english": 1.0}
        if heritage_mode == "swap_to_nepali":
            return {"nepali": 1.0}
        if heritage_mode == "swap_to_hindi":
            return {"hindi": 1.0}
        if heritage_mode == "mix":
            return {"english": 0.38, "nepali": 0.31, "hindi": 0.31}
        if profile == "hindi":
            return {"hindi": 0.82, "english": 0.1, "nepali": 0.08}
        if profile == "nepali":
            return {"nepali": 0.82, "english": 0.1, "hindi": 0.08}
        return {"english": 0.82, "nepali": 0.09, "hindi": 0.09}

    def _pick_weighted_heritage(self, weights: dict[str, float], rng: random.Random) -> str:
        total = sum(weights.values())
        threshold = rng.random() * max(total, 1e-6)
        cumulative = 0.0
        for heritage, weight in weights.items():
            cumulative += weight
            if threshold <= cumulative:
                return heritage
        return next(iter(weights.keys()))

    def _next_name(self, heritage: str, gender: str, rng: random.Random, used_names: set[str]) -> str:
        heritage_key = heritage if heritage in self._NAME_POOL else "english"
        gender_key = "female" if gender == "female" else "male"
        pool = self._NAME_POOL[heritage_key][gender_key]
        for _ in range(len(pool) * 2):
            candidate = pool[rng.randrange(0, len(pool))]
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
        fallback = f"{pool[0]} {len(used_names) + 1}"
        used_names.add(fallback)
        return fallback

    def _appearance_descriptor(self, heritage: str, gender: str) -> str:
        if gender == "female":
            if heritage == "english":
                return "Fictional very beautiful long-hair blonde performer with vivid blue eyes and cinematic styling."
            if heritage == "hindi":
                return "Fictional Hindi-heritage glamorous performer with expressive features and stage-ready elegance."
            return "Fictional Nepali-heritage graceful performer with modern cinematic styling and expressive movement."

        if heritage == "english":
            return "Fictional male performer age 18-30, blonde or brunette, blue-eyed, modern pop-cinematic styling."
        if heritage == "hindi":
            return "Fictional Hindi-heritage charismatic male performer age 18-30 with high-energy cinematic presence."
        return "Fictional Nepali-heritage charismatic male performer age 18-30 with cinematic dance presence."

    def _build_segment_plan(
        self,
        project_id: int,
        target_duration: float,
        transformation_profile: dict[str, float | str],
        cast_plan: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        duration = max(target_duration, 30.0)
        interval = float(transformation_profile.get("target_shot_interval_sec", 2.8))
        segment_duration_target = self._clamp(interval * 2.35, 4.2, 11.5)
        shot_count = int(duration / max(segment_duration_target, 1.0))
        shot_count = self._clamp_int(shot_count, 18, 180)

        rng = random.Random(project_id * 6131)
        base_tempo = float(transformation_profile.get("tempo_multiplier", 1.0))
        cursor = 0.0
        segments: list[dict[str, Any]] = []

        for idx in range(shot_count):
            remaining = duration - cursor
            if idx == shot_count - 1 or remaining <= 0.4:
                source_duration = max(remaining, 0.35)
            else:
                raw = segment_duration_target + rng.uniform(-0.8, 0.9)
                source_duration = self._clamp(raw, 3.0, min(12.0, remaining))

            performer = cast_plan[idx % len(cast_plan)] if cast_plan else None
            effect_mode = "normal"
            if idx % 11 == 5:
                effect_mode = "stutter"
            elif idx % 9 == 4:
                effect_mode = "mirror"

            segments.append(
                {
                    "segment_id": f"seg_{idx + 1:03d}",
                    "source_start_sec": round(cursor, 3),
                    "source_duration_sec": round(source_duration, 3),
                    "output_start_sec": round(cursor, 3),
                    "output_duration_sec": round(source_duration, 3),
                    "tempo_multiplier": round(self._clamp(base_tempo + rng.uniform(-0.06, 0.06), 0.9, 1.1), 3),
                    "effect_mode": effect_mode,
                    "performer": performer,
                }
            )
            cursor += source_duration
            if cursor >= duration:
                break

        if segments:
            last = segments[-1]
            correction = round(max(duration - float(last["source_start_sec"]), 0.35), 3)
            last["source_duration_sec"] = correction
            last["output_duration_sec"] = correction

        return segments

    def _render_full_length_remix(
        self,
        target_video: Path,
        output_video_path: Path,
        example_remix_video: Path,
        transformation_profile: dict[str, float | str],
        cast_plan: list[dict[str, Any]],
        segment_plan: list[dict[str, Any]],
        processing_steps: list[dict[str, Any]],
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        video_probe = self._probe_video(target_video)
        duration_sec = max(float(video_probe.get("duration_sec") or 0.0), 1.0)
        style_profile = self._build_actor_transform_blueprint(transformation_profile, cast_plan, segment_plan)
        video_filter = self._build_full_length_video_filter(style_profile)
        audio_filter = self._build_full_length_audio_filter(style_profile)
        styled_video_path = output_video_path.with_name(f"{output_video_path.stem}_styled_video.mp4")
        transformed_audio_path = output_video_path.with_name(f"{output_video_path.stem}_voice_track.m4a")
        actor_replaced_video_path = output_video_path.with_name(f"{output_video_path.stem}_actor_replaced.mp4")

        self._run_ffmpeg_with_progress(
            command=[
                "ffmpeg",
                "-y",
                "-i",
                str(target_video),
                "-filter_complex",
                video_filter,
                "-map",
                "[vout]",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "19",
                "-movflags",
                "+faststart",
                "-progress",
                "pipe:2",
                "-nostats",
                str(styled_video_path),
            ],
            duration_sec=duration_sec,
            processing_steps=processing_steps,
            progress_callback=progress_callback,
            progress_start=0.62,
            progress_end=0.74,
            stage="Render Segments",
            detail_prefix="Rendering cinematic base stream for actor replacement",
        )

        self._run_ffmpeg_with_progress(
            command=[
                "ffmpeg",
                "-y",
                "-i",
                str(target_video),
                "-filter_complex",
                audio_filter,
                "-map",
                "[aout]",
                "-vn",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-progress",
                "pipe:2",
                "-nostats",
                str(transformed_audio_path),
            ],
            duration_sec=duration_sec,
            processing_steps=processing_steps,
            progress_callback=progress_callback,
            progress_start=0.74,
            progress_end=0.80,
            stage="Render Voice",
            detail_prefix="Preserving original lyrics while transforming vocal identity",
        )

        self._run_frame_actor_replacement(
            styled_video=styled_video_path,
            actor_video=actor_replaced_video_path,
            example_remix_video=example_remix_video,
            cast_plan=cast_plan,
            segment_plan=segment_plan,
            processing_steps=processing_steps,
            progress_callback=progress_callback,
            progress_start=0.80,
            progress_end=0.90,
        )

        self._run_ffmpeg_with_progress(
            command=[
                "ffmpeg",
                "-y",
                "-i",
                str(actor_replaced_video_path),
                "-i",
                str(transformed_audio_path),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-movflags",
                "+faststart",
                "-shortest",
                "-progress",
                "pipe:2",
                "-nostats",
                str(output_video_path),
            ],
            duration_sec=duration_sec,
            processing_steps=processing_steps,
            progress_callback=progress_callback,
            progress_start=0.90,
            progress_end=0.92,
            stage="Render Segments",
            detail_prefix="Muxing transformed actors with remixed vocals",
        )

        self._safe_unlink(styled_video_path)
        self._safe_unlink(transformed_audio_path)
        self._safe_unlink(actor_replaced_video_path)

    def _build_actor_transform_blueprint(
        self,
        transformation_profile: dict[str, float | str],
        cast_plan: list[dict[str, Any]],
        segment_plan: list[dict[str, Any]],
    ) -> dict[str, float | str]:
        lead = next((member for member in cast_plan if member.get("role") == "lead_vocal_performer"), None)
        lead_gender = str((lead or {}).get("gender") or "female")
        lead_heritage = str((lead or {}).get("heritage") or "english")
        style_curve = "increase_contrast" if lead_gender == "female" else "medium_contrast"

        base_brightness = float(transformation_profile.get("brightness_shift", 0.02))
        base_contrast = float(transformation_profile.get("contrast_gain", 1.1))
        base_saturation = float(transformation_profile.get("saturation_gain", 1.15))
        base_hue = float(transformation_profile.get("hue_shift", 0.0))

        heritage_offset = {"english": 4.0, "nepali": 10.0, "hindi": 14.0}
        lead_offset = heritage_offset.get(lead_heritage, 8.0)
        variation_strength = self._clamp(0.9 + (len(segment_plan) / 180.0), 0.95, 1.4)

        pitch_factor = 1.13 if lead_gender == "female" else 0.9
        if lead_heritage == "hindi":
            pitch_factor += 0.03
        elif lead_heritage == "nepali":
            pitch_factor += 0.01

        return {
            "brightness": self._clamp(base_brightness + 0.02, -0.2, 0.22),
            "contrast": self._clamp(base_contrast * 1.18, 0.95, 1.85),
            "saturation": self._clamp(base_saturation * 1.28, 0.95, 2.2),
            "gamma": 1.02 if lead_gender == "female" else 0.98,
            "base_hue": self._clamp(base_hue + lead_offset, -30.0, 30.0),
            "hue_amp": self._clamp(8.0 * variation_strength, 4.0, 13.0),
            "hue_saturation": self._clamp(1.08 + (0.08 * variation_strength), 1.02, 1.24),
            "curve_preset": style_curve,
            "noise_level": self._clamp(4.4 * variation_strength, 3.0, 6.8),
            "identity_blend": 0.88 if lead_gender == "female" else 0.85,
            "pitch_factor": self._clamp(pitch_factor, 0.84, 1.22),
            "bass_gain": 1.8 if lead_gender == "male" else -1.0,
            "presence_gain": 2.9 if lead_gender == "female" else 1.9,
            "echo_delay": 60.0 if lead_gender == "female" else 72.0,
            "echo_decay": 0.19 if lead_gender == "female" else 0.17,
            "volume": 1.08 if lead_gender == "female" else 1.03,
        }

    def _build_full_length_video_filter(self, style: dict[str, float | str]) -> str:
        base_hue = float(style["base_hue"])
        hue_amp = float(style["hue_amp"])
        return (
            "[0:v]"
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            f"eq=brightness={float(style['brightness']):.4f}:"
            f"contrast={float(style['contrast']):.4f}:"
            f"saturation={float(style['saturation']):.4f}:"
            f"gamma={float(style['gamma']):.4f},"
            f"hue=h={base_hue:.3f}+{hue_amp:.3f}*sin(t*0.65):s={float(style['hue_saturation']):.4f},"
            f"curves=preset={style['curve_preset']},"
            f"noise=alls={float(style['noise_level']):.3f}:allf=t,"
            "unsharp=7:7:1.10:5:5:0.00,format=yuv420p[vout]"
        )

    def _build_full_length_audio_filter(self, style: dict[str, float | str]) -> str:
        pitch = float(style["pitch_factor"])
        return (
            "[0:a]"
            f"rubberband=pitch={pitch:.4f}:tempo=1.0:transients=crisp:detector=compound:"
            "phase=independent:window=short:formant=shifted:pitchq=quality,"
            "firequalizer=gain='if(lt(f,220),-1.0,if(lt(f,900),0.8,if(lt(f,3400),2.1,0.4)))',"
            f"equalizer=f=180:t=q:w=0.9:g={float(style['bass_gain']):.3f},"
            f"equalizer=f=2600:t=q:w=1.2:g={float(style['presence_gain']):.3f},"
            "highpass=f=70,lowpass=f=14500,"
            f"aecho=0.82:0.88:{int(float(style['echo_delay']))}:{float(style['echo_decay']):.3f},"
            "chorus=0.5:0.9:44:0.24:0.26:0.08,"
            f"volume={float(style['volume']):.4f}[aout]"
        )

    def _run_frame_actor_replacement(
        self,
        styled_video: Path,
        actor_video: Path,
        example_remix_video: Path,
        cast_plan: list[dict[str, Any]],
        segment_plan: list[dict[str, Any]],
        processing_steps: list[dict[str, Any]],
        progress_callback: Callable[[dict[str, Any]], None] | None,
        progress_start: float,
        progress_end: float,
    ) -> None:
        frontal_cascade = self._load_face_cascade()
        profile_cascade = self._load_profile_cascade()
        reference_library = self._prepare_reference_portrait_library(
            example_remix_video=example_remix_video,
            cast_plan=cast_plan,
            frontal_cascade=frontal_cascade,
            profile_cascade=profile_cascade,
            processing_steps=processing_steps,
            progress_callback=progress_callback,
            progress=progress_start + 0.005,
        )
        capture = cv2.VideoCapture(str(styled_video))
        if not capture.isOpened():
            raise RuntimeError(f"Unable to open styled video for actor replacement: {styled_video}")

        fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if width <= 0 or height <= 0:
            capture.release()
            raise RuntimeError("Invalid styled video dimensions for actor replacement")

        writer = cv2.VideoWriter(
            str(actor_video),
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if not writer.isOpened():
            capture.release()
            raise RuntimeError(f"Unable to open output writer for actor replacement: {actor_video}")

        worker_threads = self._compute_worker_threads()
        max_inflight = max(worker_threads * 3, 24)
        detection_every = 2
        progress_step = max(1, frame_count // 45) if frame_count > 0 else 60
        last_boxes: list[tuple[int, int, int, int]] = []
        stale_detection_frames = 0
        segment_cursor = 0
        frame_index = 0
        written_frames = 0
        next_write_index = 0
        pending: dict[int, Future[np.ndarray]] = {}
        pending_performer: dict[int, str] = {}

        self._append_processing_step(
            processing_steps,
            "Face Synthesis",
            f"Launching {worker_threads} transformation workers based on detected host CPU capacity.",
            progress_start + 0.01,
            callback=progress_callback,
            extra={"workers": worker_threads},
        )

        def flush_ready_frames(*, force_wait: bool) -> None:
            nonlocal next_write_index, written_frames
            if force_wait and next_write_index in pending and not pending[next_write_index].done():
                pending[next_write_index].result()
            while next_write_index in pending and pending[next_write_index].done():
                transformed = pending.pop(next_write_index).result()
                performer_name = pending_performer.pop(next_write_index, "fictitious cast")
                writer.write(transformed)
                written_frames += 1
                if frame_count > 0 and (
                    written_frames == 1 or written_frames % progress_step == 0 or written_frames >= frame_count
                ):
                    ratio = self._clamp(written_frames / max(frame_count, 1), 0.0, 1.0)
                    mapped = self._clamp(
                        progress_start + (progress_end - progress_start) * ratio,
                        progress_start,
                        progress_end,
                    )
                    self._append_processing_step(
                        processing_steps,
                        "Face Synthesis",
                        (
                            f"Replacing detected actors and upper-body regions with photo-based fictitious cast "
                            f"identities ({int(ratio * 100)}%) [{performer_name}]"
                        ),
                        mapped,
                        callback=progress_callback,
                        extra={"workers": worker_threads},
                    )
                next_write_index += 1

        try:
            with ThreadPoolExecutor(max_workers=worker_threads) as executor:
                while True:
                    ok, frame = capture.read()
                    if not ok:
                        break

                    timestamp_sec = frame_index / max(fps, 1.0)
                    while segment_cursor + 1 < len(segment_plan):
                        if timestamp_sec < self._segment_end_sec(segment_plan[segment_cursor]):
                            break
                        segment_cursor += 1
                    primary_performer = self._segment_performer(segment_plan, segment_cursor, cast_plan)

                    should_detect = frame_index % detection_every == 0 or not last_boxes
                    current_boxes = list(last_boxes)
                    if should_detect:
                        detected_boxes = self._detect_face_boxes(
                            frame=frame,
                            width=width,
                            height=height,
                            frontal_cascade=frontal_cascade,
                            profile_cascade=profile_cascade,
                            max_faces=8,
                        )
                        if detected_boxes:
                            current_boxes = detected_boxes
                            last_boxes = detected_boxes
                            stale_detection_frames = 0
                        else:
                            stale_detection_frames += 1
                            if stale_detection_frames > 15:
                                last_boxes = []
                                current_boxes = []
                    elif last_boxes:
                        stale_detection_frames += 1
                        if stale_detection_frames > 15:
                            last_boxes = []
                            current_boxes = []

                    if not current_boxes:
                        current_boxes = self._fallback_face_boxes(width, height, primary_performer)

                    assigned_performers = self._frame_performer_sequence(
                        primary_performer=primary_performer,
                        cast_plan=cast_plan,
                        target_count=len(current_boxes),
                    )
                    performer_name = str(primary_performer.get("name") or "fictitious cast")
                    frame_copy = frame.copy()
                    pending[frame_index] = executor.submit(
                        self._apply_fictitious_actor_faces,
                        frame_copy,
                        current_boxes,
                        assigned_performers,
                        reference_library,
                        frame_index,
                    )
                    pending_performer[frame_index] = performer_name
                    frame_index += 1

                    flush_ready_frames(force_wait=False)
                    if len(pending) >= max_inflight:
                        flush_ready_frames(force_wait=True)

                while pending:
                    flush_ready_frames(force_wait=True)
        finally:
            capture.release()
            writer.release()

    def _prepare_reference_portrait_library(
        self,
        example_remix_video: Path,
        cast_plan: list[dict[str, Any]],
        frontal_cascade: cv2.CascadeClassifier | None,
        profile_cascade: cv2.CascadeClassifier | None,
        processing_steps: list[dict[str, Any]],
        progress_callback: Callable[[dict[str, Any]], None] | None,
        progress: float,
    ) -> dict[str, list[dict[str, Any]]]:
        local_portraits = self._load_reference_faces_from_disk(frontal_cascade, profile_cascade)
        example_portraits = self._extract_reference_faces_from_video(
            video_path=example_remix_video,
            frontal_cascade=frontal_cascade,
            profile_cascade=profile_cascade,
            max_portraits=56,
        )

        keys = [f"{heritage}:{gender}" for heritage in ("english", "nepali", "hindi") for gender in ("female", "male")]
        library: dict[str, list[dict[str, Any]]] = {}
        for key in keys:
            pool = list(local_portraits.get(key, []))
            if not pool:
                heritage, _ = key.split(":")
                pool = list(local_portraits.get(f"{heritage}:female", [])) + list(local_portraits.get(f"{heritage}:male", []))
            if not pool:
                pool = list(example_portraits)
            library[key] = pool

        all_pool: list[dict[str, Any]] = []
        for key in keys:
            all_pool.extend(library.get(key, []))
        all_pool.extend(example_portraits)

        if not all_pool:
            for key in keys:
                heritage, gender = key.split(":")
                patch, _, _ = self._build_fictitious_face_patch({"heritage": heritage, "gender": gender}, 320, 480, seed=1200)
                fallback_entry = {
                    "image": patch,
                    "face_box": (80, 120, 160, 220),
                    "source": "synthetic-fallback",
                }
                library[key] = [fallback_entry]
                all_pool.append(fallback_entry)

        library["all"] = all_pool
        self._append_processing_step(
            processing_steps,
            "Reference Portraits",
            (
                f"Prepared photo reference library: local={sum(len(items) for items in local_portraits.values())}, "
                f"example={len(example_portraits)}, total={len(all_pool)}."
            ),
            progress,
            callback=progress_callback,
        )
        return library

    def _load_reference_faces_from_disk(
        self,
        frontal_cascade: cv2.CascadeClassifier | None,
        profile_cascade: cv2.CascadeClassifier | None,
    ) -> dict[str, list[dict[str, Any]]]:
        roots = [
            Path(settings.quick_output_root).expanduser() / "reference_faces",
            Path("/app/reference_faces"),
            Path(__file__).resolve().parents[2] / "reference_faces",
        ]
        deduped_roots: list[Path] = []
        for root in roots:
            candidate = root.resolve() if root.exists() else root
            if candidate not in deduped_roots:
                deduped_roots.append(candidate)

        result: dict[str, list[dict[str, Any]]] = {}
        for heritage in ("english", "nepali", "hindi"):
            for gender in ("female", "male"):
                key = f"{heritage}:{gender}"
                result[key] = []
                image_paths: list[Path] = []
                for root in deduped_roots:
                    if not root.exists():
                        continue
                    patterns = [root / heritage / gender, root / heritage]
                    for pattern in patterns:
                        if not pattern.exists():
                            continue
                        for suffix in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                            image_paths.extend(sorted(pattern.glob(suffix)))

                seen_paths: set[Path] = set()
                unique_paths: list[Path] = []
                for image_path in image_paths:
                    if image_path in seen_paths:
                        continue
                    seen_paths.add(image_path)
                    unique_paths.append(image_path)

                for image_path in unique_paths[:32]:
                    image = cv2.imread(str(image_path))
                    if image is None or image.size == 0:
                        continue
                    h, w = image.shape[:2]
                    detected = self._detect_face_boxes(
                        frame=image,
                        width=w,
                        height=h,
                        frontal_cascade=frontal_cascade,
                        profile_cascade=profile_cascade,
                        max_faces=2,
                    )
                    if not detected:
                        detected = [(int(w * 0.30), int(h * 0.15), int(w * 0.40), int(h * 0.45))]
                    for box in detected[:2]:
                        portrait = self._extract_portrait_from_frame(image, box, source=str(image_path))
                        if portrait is not None:
                            result[key].append(portrait)
        return result

    def _extract_reference_faces_from_video(
        self,
        video_path: Path,
        frontal_cascade: cv2.CascadeClassifier | None,
        profile_cascade: cv2.CascadeClassifier | None,
        max_portraits: int,
    ) -> list[dict[str, Any]]:
        portraits: list[dict[str, Any]] = []
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            return portraits

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        sample_every = max(1, frame_count // 90) if frame_count > 0 else 20
        frame_index = 0
        try:
            while len(portraits) < max_portraits:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % sample_every != 0:
                    frame_index += 1
                    continue

                h, w = frame.shape[:2]
                detected = self._detect_face_boxes(
                    frame=frame,
                    width=w,
                    height=h,
                    frontal_cascade=frontal_cascade,
                    profile_cascade=profile_cascade,
                    max_faces=3,
                )
                for box in detected:
                    portrait = self._extract_portrait_from_frame(frame, box, source=f"example-remix:{frame_index}")
                    if portrait is not None:
                        portraits.append(portrait)
                        if len(portraits) >= max_portraits:
                            break
                frame_index += 1
        finally:
            capture.release()
        return portraits

    def _extract_portrait_from_frame(
        self,
        frame: np.ndarray,
        face_box: tuple[int, int, int, int],
        source: str,
    ) -> dict[str, Any] | None:
        x, y, w, h = face_box
        if w <= 2 or h <= 2:
            return None
        frame_h, frame_w = frame.shape[:2]
        left = max(int(x - (w * 0.45)), 0)
        top = max(int(y - (h * 0.40)), 0)
        right = min(int(x + (w * 1.45)), frame_w)
        bottom = min(int(y + (h * 2.25)), frame_h)
        if right - left < 32 or bottom - top < 32:
            return None

        portrait = frame[top:bottom, left:right].copy()
        if portrait.size == 0:
            return None

        target_w, target_h = 320, 480
        resized = cv2.resize(portrait, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
        scale_x = target_w / max(right - left, 1)
        scale_y = target_h / max(bottom - top, 1)
        face_rel_x = int((x - left) * scale_x)
        face_rel_y = int((y - top) * scale_y)
        face_rel_w = int(w * scale_x)
        face_rel_h = int(h * scale_y)
        face_rel_x = int(self._clamp(face_rel_x, 0, target_w - 2))
        face_rel_y = int(self._clamp(face_rel_y, 0, target_h - 2))
        face_rel_w = int(self._clamp(face_rel_w, 8, target_w - face_rel_x))
        face_rel_h = int(self._clamp(face_rel_h, 8, target_h - face_rel_y))
        return {
            "image": resized,
            "face_box": (face_rel_x, face_rel_y, face_rel_w, face_rel_h),
            "source": source,
        }

    def _frame_performer_sequence(
        self,
        primary_performer: dict[str, Any],
        cast_plan: list[dict[str, Any]],
        target_count: int,
    ) -> list[dict[str, Any]]:
        ordered: list[dict[str, Any]] = [primary_performer]
        primary_id = str(primary_performer.get("character_id") or "")
        for performer in cast_plan:
            performer_id = str(performer.get("character_id") or "")
            if performer_id and performer_id == primary_id:
                continue
            ordered.append(performer)
        if not ordered:
            ordered = [{"heritage": "english", "gender": "female", "role": "lead_vocal_performer"}]
        return [ordered[index % len(ordered)] for index in range(max(1, target_count))]

    def _select_reference_portrait_for_performer(
        self,
        performer: dict[str, Any],
        reference_library: dict[str, list[dict[str, Any]]],
        frame_index: int,
        box_index: int,
    ) -> dict[str, Any] | None:
        heritage = str(performer.get("heritage") or "english")
        gender = str(performer.get("gender") or "female")
        key = f"{heritage}:{'female' if gender == 'female' else 'male'}"
        pool = reference_library.get(key) or reference_library.get("all") or []
        if not pool:
            return None
        seed = self._performer_seed(performer) + (frame_index // 6) + (box_index * 31)
        return pool[seed % len(pool)]

    def _detect_face_boxes(
        self,
        frame: np.ndarray,
        width: int,
        height: int,
        frontal_cascade: cv2.CascadeClassifier | None,
        profile_cascade: cv2.CascadeClassifier | None,
        max_faces: int,
    ) -> list[tuple[int, int, int, int]]:
        if frontal_cascade is None and profile_cascade is None:
            return []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        candidates: list[tuple[int, int, int, int]] = []

        if frontal_cascade is not None:
            frontal = frontal_cascade.detectMultiScale(gray, scaleFactor=1.06, minNeighbors=3, minSize=(30, 30))
            for detection in frontal:
                candidates.append((int(detection[0]), int(detection[1]), int(detection[2]), int(detection[3])))

        if profile_cascade is not None:
            profile_left = profile_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(30, 30))
            for detection in profile_left:
                candidates.append((int(detection[0]), int(detection[1]), int(detection[2]), int(detection[3])))
            flipped = cv2.flip(gray, 1)
            profile_right = profile_cascade.detectMultiScale(flipped, scaleFactor=1.08, minNeighbors=4, minSize=(30, 30))
            for detection in profile_right:
                x, y, w, h = int(detection[0]), int(detection[1]), int(detection[2]), int(detection[3])
                candidates.append((width - (x + w), y, w, h))

        normalized = self._normalize_face_boxes(candidates, width, height)
        filtered = self._non_max_suppress_boxes(normalized, iou_threshold=0.34)
        return filtered[:max_faces]

    def _load_face_cascade(self) -> cv2.CascadeClassifier | None:
        if hasattr(self, "_cached_face_cascade"):
            cached = getattr(self, "_cached_face_cascade")
            return cached if isinstance(cached, cv2.CascadeClassifier) else None

        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        if not cascade_path.exists():
            setattr(self, "_cached_face_cascade", None)
            return None

        cascade = cv2.CascadeClassifier(str(cascade_path))
        if cascade.empty():
            setattr(self, "_cached_face_cascade", None)
            return None

        setattr(self, "_cached_face_cascade", cascade)
        return cascade

    def _load_profile_cascade(self) -> cv2.CascadeClassifier | None:
        if hasattr(self, "_cached_profile_cascade"):
            cached = getattr(self, "_cached_profile_cascade")
            return cached if isinstance(cached, cv2.CascadeClassifier) else None

        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_profileface.xml"
        if not cascade_path.exists():
            setattr(self, "_cached_profile_cascade", None)
            return None

        cascade = cv2.CascadeClassifier(str(cascade_path))
        if cascade.empty():
            setattr(self, "_cached_profile_cascade", None)
            return None

        setattr(self, "_cached_profile_cascade", cascade)
        return cascade

    def _normalize_face_boxes(self, detections: Any, width: int, height: int) -> list[tuple[int, int, int, int]]:
        boxes: list[tuple[int, int, int, int]] = []
        for detection in detections:
            x, y, w, h = (int(detection[0]), int(detection[1]), int(detection[2]), int(detection[3]))
            if w * h < 1100:
                continue
            expand_w = int(w * 0.34)
            expand_h = int(h * 0.54)
            nx = max(x - (expand_w // 2), 0)
            ny = max(y - int(h * 0.30), 0)
            nw = min(w + expand_w, width - nx)
            nh = min(h + expand_h, height - ny)
            if nw < 26 or nh < 26:
                continue
            boxes.append((nx, ny, nw, nh))

        boxes.sort(key=lambda item: item[2] * item[3], reverse=True)
        return boxes[:10]

    def _non_max_suppress_boxes(
        self,
        boxes: list[tuple[int, int, int, int]],
        iou_threshold: float,
    ) -> list[tuple[int, int, int, int]]:
        selected: list[tuple[int, int, int, int]] = []
        for candidate in boxes:
            should_keep = True
            for existing in selected:
                if self._box_iou(candidate, existing) > iou_threshold:
                    should_keep = False
                    break
            if should_keep:
                selected.append(candidate)
        return selected

    def _box_iou(self, a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
        ax1, ay1, aw, ah = a
        bx1, by1, bw, bh = b
        ax2, ay2 = ax1 + aw, ay1 + ah
        bx2, by2 = bx1 + bw, by1 + bh
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter_w = max(inter_x2 - inter_x1, 0)
        inter_h = max(inter_y2 - inter_y1, 0)
        inter_area = inter_w * inter_h
        if inter_area <= 0:
            return 0.0
        union = (aw * ah) + (bw * bh) - inter_area
        if union <= 0:
            return 0.0
        return inter_area / union

    def _fallback_face_boxes(self, width: int, height: int, performer: dict[str, Any]) -> list[tuple[int, int, int, int]]:
        role = str(performer.get("role") or "dance_performer")
        if role == "lead_vocal_performer":
            return [
                (int(width * 0.30), int(height * 0.08), int(width * 0.38), int(height * 0.44)),
                (int(width * 0.06), int(height * 0.12), int(width * 0.24), int(height * 0.34)),
                (int(width * 0.70), int(height * 0.12), int(width * 0.24), int(height * 0.34)),
            ]
        return [
            (int(width * 0.08), int(height * 0.10), int(width * 0.26), int(height * 0.34)),
            (int(width * 0.36), int(height * 0.09), int(width * 0.26), int(height * 0.34)),
            (int(width * 0.66), int(height * 0.10), int(width * 0.26), int(height * 0.34)),
        ]

    def _apply_fictitious_actor_faces(
        self,
        frame: np.ndarray,
        face_boxes: list[tuple[int, int, int, int]],
        performers: list[dict[str, Any]],
        reference_library: dict[str, list[dict[str, Any]]],
        frame_index: int,
    ) -> np.ndarray:
        output = frame.copy()
        for box_index, (x, y, w, h) in enumerate(face_boxes):
            if w <= 1 or h <= 1:
                continue
            x2 = min(x + w, output.shape[1])
            y2 = min(y + h, output.shape[0])
            if x2 <= x or y2 <= y:
                continue

            patch_width = x2 - x
            patch_height = y2 - y
            performer = performers[box_index % len(performers)] if performers else {"heritage": "english", "gender": "female"}
            portrait = self._select_reference_portrait_for_performer(
                performer=performer,
                reference_library=reference_library,
                frame_index=frame_index,
                box_index=box_index,
            )
            if portrait is None:
                seed = self._performer_seed(performer) + (box_index * 101) + (frame_index // 7)
                patch, mask, blend_strength = self._build_fictitious_face_patch(performer, patch_width, patch_height, seed)
                roi = output[y:y2, x:x2]
                alpha = (mask.astype(np.float32) / 255.0) * blend_strength
                alpha_3 = np.repeat(alpha[:, :, None], 3, axis=2)
                blended = (roi.astype(np.float32) * (1.0 - alpha_3)) + (patch.astype(np.float32) * alpha_3)
                output[y:y2, x:x2] = np.clip(blended, 0, 255).astype(np.uint8)
                continue

            output = self._overlay_reference_identity(
                frame=output,
                target_face_box=(x, y, w, h),
                portrait=portrait,
            )
        return output

    def _overlay_reference_identity(
        self,
        frame: np.ndarray,
        target_face_box: tuple[int, int, int, int],
        portrait: dict[str, Any],
    ) -> np.ndarray:
        output = frame
        x, y, w, h = target_face_box
        frame_h, frame_w = output.shape[:2]
        x = int(self._clamp(x, 0, frame_w - 2))
        y = int(self._clamp(y, 0, frame_h - 2))
        w = int(self._clamp(w, 8, frame_w - x))
        h = int(self._clamp(h, 8, frame_h - y))

        portrait_image = portrait.get("image")
        portrait_face_box = portrait.get("face_box")
        if not isinstance(portrait_image, np.ndarray) or portrait_image.size == 0:
            return output
        if not isinstance(portrait_face_box, tuple) or len(portrait_face_box) != 4:
            return output

        px, py, pw, ph = portrait_face_box
        portrait_h, portrait_w = portrait_image.shape[:2]
        px = int(self._clamp(px, 0, portrait_w - 2))
        py = int(self._clamp(py, 0, portrait_h - 2))
        pw = int(self._clamp(pw, 8, portrait_w - px))
        ph = int(self._clamp(ph, 8, portrait_h - py))

        head_src_left = max(int(px - (pw * 0.24)), 0)
        head_src_top = max(int(py - (ph * 0.30)), 0)
        head_src_right = min(int(px + (pw * 1.24)), portrait_w)
        head_src_bottom = min(int(py + (ph * 1.10)), portrait_h)
        if head_src_right - head_src_left < 8 or head_src_bottom - head_src_top < 8:
            return output

        head_src = portrait_image[head_src_top:head_src_bottom, head_src_left:head_src_right]
        head_dst_left = x
        head_dst_top = y
        head_dst_right = min(x + w, frame_w)
        head_dst_bottom = min(y + h, frame_h)
        if head_dst_right - head_dst_left < 8 or head_dst_bottom - head_dst_top < 8:
            return output

        head_dst_roi = output[head_dst_top:head_dst_bottom, head_dst_left:head_dst_right]
        head_resized = cv2.resize(head_src, (head_dst_roi.shape[1], head_dst_roi.shape[0]), interpolation=cv2.INTER_CUBIC)
        head_matched = self._fit_color(head_resized, head_dst_roi)
        head_mask = self._soft_ellipse_mask(head_dst_roi.shape[1], head_dst_roi.shape[0], feather_ratio=0.16)
        head_alpha = np.repeat((head_mask[:, :, None] / 255.0) * 0.90, 3, axis=2)
        head_blended = (head_dst_roi.astype(np.float32) * (1.0 - head_alpha)) + (head_matched.astype(np.float32) * head_alpha)
        output[head_dst_top:head_dst_bottom, head_dst_left:head_dst_right] = np.clip(head_blended, 0, 255).astype(np.uint8)

        torso_src_top = min(int(py + (ph * 0.54)), portrait_h - 2)
        torso_src_left = max(int(px - (pw * 0.28)), 0)
        torso_src_right = min(int(px + (pw * 1.28)), portrait_w)
        torso_src_bottom = portrait_h
        if torso_src_right - torso_src_left < 12 or torso_src_bottom - torso_src_top < 12:
            return output
        torso_src = portrait_image[torso_src_top:torso_src_bottom, torso_src_left:torso_src_right]

        torso_dst_left = max(int(x - (w * 0.22)), 0)
        torso_dst_top = min(int(y + (h * 0.52)), frame_h - 2)
        torso_dst_width = int(w * 1.44)
        torso_dst_height = int(h * 1.55)
        torso_dst_right = min(torso_dst_left + torso_dst_width, frame_w)
        torso_dst_bottom = min(torso_dst_top + torso_dst_height, frame_h)
        if torso_dst_right - torso_dst_left < 12 or torso_dst_bottom - torso_dst_top < 12:
            return output

        torso_dst_roi = output[torso_dst_top:torso_dst_bottom, torso_dst_left:torso_dst_right]
        torso_resized = cv2.resize(torso_src, (torso_dst_roi.shape[1], torso_dst_roi.shape[0]), interpolation=cv2.INTER_CUBIC)
        torso_matched = self._fit_color(torso_resized, torso_dst_roi)

        torso_mask = np.zeros((torso_dst_roi.shape[0], torso_dst_roi.shape[1]), dtype=np.float32)
        for row in range(torso_mask.shape[0]):
            vertical = row / max(torso_mask.shape[0] - 1, 1)
            torso_mask[row, :] = self._clamp((vertical * 1.15), 0.0, 1.0)
        torso_mask = cv2.GaussianBlur(torso_mask, (0, 0), max(1.8, min(torso_dst_roi.shape[0], torso_dst_roi.shape[1]) * 0.08))
        torso_alpha = np.repeat((torso_mask[:, :, None]) * 0.46, 3, axis=2)
        torso_blended = (torso_dst_roi.astype(np.float32) * (1.0 - torso_alpha)) + (torso_matched.astype(np.float32) * torso_alpha)
        output[torso_dst_top:torso_dst_bottom, torso_dst_left:torso_dst_right] = np.clip(torso_blended, 0, 255).astype(np.uint8)
        return output

    def _fit_color(self, source: np.ndarray, target: np.ndarray) -> np.ndarray:
        if source.size == 0 or target.size == 0:
            return source
        src = source.astype(np.float32)
        dst = target.astype(np.float32)
        src_mean, src_std = cv2.meanStdDev(src)
        dst_mean, dst_std = cv2.meanStdDev(dst)
        src_std = np.maximum(src_std, 1e-4)
        adjusted = ((src - src_mean.reshape(1, 1, 3)) * (dst_std.reshape(1, 1, 3) / src_std.reshape(1, 1, 3))) + dst_mean.reshape(1, 1, 3)
        adjusted = cv2.GaussianBlur(adjusted, (0, 0), 0.6)
        return np.clip(adjusted, 0, 255).astype(np.uint8)

    def _soft_ellipse_mask(self, width: int, height: int, feather_ratio: float) -> np.ndarray:
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.ellipse(
            mask,
            (width // 2, height // 2),
            (max(4, int(width * 0.45)), max(4, int(height * 0.48))),
            0,
            0,
            360,
            255,
            -1,
        )
        sigma = max(1.2, min(width, height) * feather_ratio)
        return cv2.GaussianBlur(mask, (0, 0), sigma)

    def _build_fictitious_face_patch(
        self,
        performer: dict[str, Any],
        width: int,
        height: int,
        seed: int,
    ) -> tuple[np.ndarray, np.ndarray, float]:
        rng = random.Random(seed)
        style = self._fictitious_face_style(performer, rng)

        patch = np.zeros((height, width, 3), dtype=np.uint8)
        patch[:, :] = style["background"]

        face_center = (width // 2, int(height * 0.58))
        face_axes = (max(8, int(width * 0.34)), max(10, int(height * 0.40)))
        hair_center = (width // 2, int(height * 0.30))
        hair_axes = (max(10, int(width * 0.40)), max(8, int(height * 0.30)))

        cv2.ellipse(patch, hair_center, hair_axes, 0, 0, 360, style["hair"], -1)
        cv2.ellipse(patch, face_center, face_axes, 0, 0, 360, style["skin"], -1)

        eye_y = int(height * 0.52)
        eye_dx = int(width * 0.12)
        eye_radius = max(2, int(min(width, height) * 0.045))
        left_eye = (width // 2 - eye_dx, eye_y)
        right_eye = (width // 2 + eye_dx, eye_y)
        cv2.circle(patch, left_eye, eye_radius, (245, 245, 245), -1)
        cv2.circle(patch, right_eye, eye_radius, (245, 245, 245), -1)
        cv2.circle(patch, left_eye, max(1, int(eye_radius * 0.55)), style["iris"], -1)
        cv2.circle(patch, right_eye, max(1, int(eye_radius * 0.55)), style["iris"], -1)
        cv2.circle(patch, left_eye, max(1, int(eye_radius * 0.25)), (15, 15, 15), -1)
        cv2.circle(patch, right_eye, max(1, int(eye_radius * 0.25)), (15, 15, 15), -1)

        brow_y = max(0, eye_y - int(eye_radius * 1.6))
        cv2.line(
            patch,
            (left_eye[0] - eye_radius, brow_y),
            (left_eye[0] + eye_radius, brow_y - 1),
            style["brow"],
            max(1, eye_radius // 2),
        )
        cv2.line(
            patch,
            (right_eye[0] - eye_radius, brow_y - 1),
            (right_eye[0] + eye_radius, brow_y),
            style["brow"],
            max(1, eye_radius // 2),
        )

        nose_tip = (width // 2, int(height * 0.63))
        cv2.line(patch, (width // 2, eye_y + eye_radius), nose_tip, style["nose"], max(1, eye_radius // 3))
        lip_center = (width // 2, int(height * 0.72))
        lip_axes = (max(4, int(width * 0.09)), max(2, int(height * 0.018)))
        cv2.ellipse(patch, lip_center, lip_axes, 0, 0, 360, style["lip"], -1)

        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.ellipse(
            mask,
            (width // 2, int(height * 0.56)),
            (max(8, int(width * 0.37)), max(10, int(height * 0.44))),
            0,
            0,
            360,
            255,
            -1,
        )
        mask = cv2.GaussianBlur(mask, (0, 0), max(1.5, min(width, height) * 0.03))
        blend_strength = float(style["blend_strength"])
        return patch, mask, self._clamp(blend_strength, 0.74, 0.94)

    def _fictitious_face_style(self, performer: dict[str, Any], rng: random.Random) -> dict[str, Any]:
        heritage = str(performer.get("heritage") or "english")
        gender = str(performer.get("gender") or "female")

        if heritage == "english":
            skin = (188, 205, 233) if gender == "female" else (176, 194, 224)
            hair = (72, 168, 224) if gender == "female" or rng.random() < 0.56 else (58, 90, 142)
            iris = (215, 162, 58)
            lip = (166, 94, 184) if gender == "female" else (126, 94, 158)
            blend_strength = 0.90 if gender == "female" else 0.88
        elif heritage == "hindi":
            skin = (116, 152, 198) if gender == "female" else (104, 140, 186)
            hair = (42, 52, 72)
            iris = (78, 102, 142)
            lip = (124, 76, 162) if gender == "female" else (108, 80, 138)
            blend_strength = 0.87
        else:
            skin = (130, 164, 206) if gender == "female" else (118, 152, 194)
            hair = (48, 62, 86)
            iris = (90, 112, 144)
            lip = (138, 82, 168) if gender == "female" else (112, 86, 142)
            blend_strength = 0.86

        jitter = rng.randint(-8, 8)
        background = (
            int(self._clamp(skin[0] - 26 + jitter, 0, 255)),
            int(self._clamp(skin[1] - 18 + jitter, 0, 255)),
            int(self._clamp(skin[2] - 12 + jitter, 0, 255)),
        )
        brow = tuple(int(self._clamp(channel - 34, 0, 255)) for channel in hair)
        nose = tuple(int(self._clamp(channel - 12, 0, 255)) for channel in skin)
        return {
            "background": background,
            "skin": skin,
            "hair": hair,
            "iris": iris,
            "lip": lip,
            "brow": brow,
            "nose": nose,
            "blend_strength": blend_strength,
        }

    def _performer_seed(self, performer: dict[str, Any]) -> int:
        seed_source = "|".join(
            [
                str(performer.get("character_id") or ""),
                str(performer.get("name") or ""),
                str(performer.get("heritage") or ""),
                str(performer.get("gender") or ""),
            ]
        )
        seed = 0
        for index, char in enumerate(seed_source):
            seed += (index + 1) * ord(char)
        return seed or 1931

    def _safe_unlink(self, file_path: Path) -> None:
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass

    def _run_ffmpeg_with_progress(
        self,
        command: list[str],
        duration_sec: float,
        processing_steps: list[dict[str, Any]],
        progress_callback: Callable[[dict[str, Any]], None] | None,
        progress_start: float,
        progress_end: float,
        stage: str,
        detail_prefix: str,
    ) -> None:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        stderr_lines: list[str] = []
        last_emitted_progress = progress_start

        while True:
            line = process.stderr.readline() if process.stderr is not None else ""
            if not line:
                if process.poll() is not None:
                    break
                continue

            stripped = line.strip()
            if stripped:
                stderr_lines.append(stripped)
                if len(stderr_lines) > 220:
                    stderr_lines = stderr_lines[-220:]

            if stripped.startswith("out_time_ms="):
                try:
                    out_ms = int(stripped.split("=", 1)[1])
                except ValueError:
                    continue
                seconds = max(out_ms / 1_000_000.0, 0.0)
                ratio = self._clamp(seconds / max(duration_sec, 0.1), 0.0, 1.0)
                mapped = self._clamp(
                    progress_start + (progress_end - progress_start) * ratio,
                    progress_start,
                    progress_end,
                )
                if mapped - last_emitted_progress >= 0.012 or ratio >= 0.998:
                    self._append_processing_step(
                        processing_steps,
                        stage,
                        f"{detail_prefix} ({int(ratio * 100)}%)",
                        mapped,
                        callback=progress_callback,
                    )
                    last_emitted_progress = mapped

        return_code = process.wait()
        if return_code != 0:
            detail = "\n".join(stderr_lines[-22:]).strip()
            raise RuntimeError(f"Command failed: {' '.join(command)}\n{detail}")

    def _render_target_segments(
        self,
        target_video: Path,
        clips_dir: Path,
        transformation_profile: dict[str, float | str],
        segment_plan: list[dict[str, Any]],
        processing_steps: list[dict[str, Any]] | None = None,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> list[Path]:
        segment_paths: list[Path] = []
        base_brightness = float(transformation_profile.get("brightness_shift", 0.01))
        base_contrast = float(transformation_profile.get("contrast_gain", 1.05))
        base_saturation = float(transformation_profile.get("saturation_gain", 1.08))
        base_hue = float(transformation_profile.get("hue_shift", 0.0))
        audio_drive = float(transformation_profile.get("audio_drive", 0.15))
        volume_gain = self._clamp(0.9 + ((audio_drive - 0.12) * 2.1), 0.75, 1.35)

        heritage_hue_offset = {"english": 0.0, "nepali": 4.0, "hindi": 8.0}
        progress_step = max(1, len(segment_plan) // 8)
        for index, segment in enumerate(segment_plan, start=1):
            performer = segment.get("performer") or {}
            heritage = str(performer.get("heritage") or "english")
            tempo_multiplier = float(segment.get("tempo_multiplier") or 1.0)
            source_start_sec = float(segment.get("source_start_sec") or segment.get("start_sec") or 0.0)
            source_duration_sec = float(segment.get("source_duration_sec") or segment.get("duration_sec") or 2.0)
            effect_mode = str(segment.get("effect_mode") or "normal")
            performer_profile = self._build_performer_transform_profile(performer, index)
            hue_shift = base_hue + heritage_hue_offset.get(heritage, 0.0) + float(performer_profile["hue_offset"])
            segment_brightness = self._clamp(base_brightness + float(performer_profile["brightness_shift"]), -0.24, 0.24)
            segment_contrast = self._clamp(base_contrast * float(performer_profile["contrast_gain"]), 0.78, 1.7)
            segment_saturation = self._clamp(base_saturation * float(performer_profile["saturation_gain"]), 0.72, 2.1)
            segment_gamma = self._clamp(float(performer_profile["gamma"]), 0.7, 1.4)
            segment_noise = self._clamp(float(performer_profile["noise"]), 0.0, 12.0)
            segment_blur = self._clamp(float(performer_profile["blur_sigma"]), 0.0, 1.2)

            video_filters = [
                "scale=1280:720:force_original_aspect_ratio=decrease",
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                (
                    f"eq=brightness={segment_brightness:.4f}:"
                    f"contrast={segment_contrast:.4f}:"
                    f"saturation={segment_saturation:.4f}:"
                    f"gamma={segment_gamma:.4f}"
                ),
                f"hue=h={hue_shift:.3f}:s={float(performer_profile['hue_saturation']):.4f}",
                f"curves=preset={performer_profile['curve_preset']}",
            ]
            if segment_blur > 0.01:
                video_filters.append(f"gblur=sigma={segment_blur:.3f}")
            if effect_mode == "mirror":
                video_filters.append("hflip")
            elif effect_mode == "stutter":
                video_filters.extend(["fps=18", "fps=30"])
            video_filters.extend(
                [
                    "unsharp=5:5:0.55:3:3:0.00",
                    f"noise=alls={self._clamp(segment_noise * 1.35, 0.0, 14.0):.3f}:allf=t",
                    "format=yuv420p",
                ]
            )
            video_filter = ",".join(video_filters)

            pitch_ratio = 2 ** (float(performer_profile["pitch_semitones"]) / 12.0)
            pitch_inverse = self._clamp(1.0 / pitch_ratio, 0.5, 2.0)
            segment_volume = self._clamp(volume_gain * float(performer_profile["volume_multiplier"]), 0.68, 1.65)
            audio_filter = ",".join(
                [
                    f"asetrate=48000*{pitch_ratio:.6f}",
                    "aresample=48000",
                    f"atempo={pitch_inverse:.6f}",
                    f"atempo={tempo_multiplier:.6f}",
                    f"equalizer=f=180:t=q:w=0.9:g={float(performer_profile['bass_gain']):.3f}",
                    f"equalizer=f=2600:t=q:w=1.2:g={float(performer_profile['presence_gain']):.3f}",
                    "highpass=f=70",
                    "lowpass=f=14500",
                    (
                        f"aecho=0.82:0.88:{int(performer_profile['echo_delay_ms'])}:"
                        f"{float(performer_profile['echo_decay']):.3f}"
                    ),
                    f"volume={segment_volume:.4f}",
                ]
            )
            segment_path = clips_dir / f"{index:03d}_{segment['segment_id']}.mp4"
            self._run_command(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    str(source_start_sec),
                    "-i",
                    str(target_video),
                    "-t",
                    str(source_duration_sec),
                    "-vf",
                    video_filter,
                    "-af",
                    audio_filter,
                    "-r",
                    "30",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "21",
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
            if processing_steps is not None and (index == 1 or index % progress_step == 0 or index == len(segment_plan)):
                ratio = index / max(len(segment_plan), 1)
                progress = self._clamp(0.62 + (ratio * 0.26), 0.62, 0.88)
                role = str(performer.get("role") or "performer")
                self._append_processing_step(
                    processing_steps,
                    "Render Segments",
                    (
                        f"Rendered segment {index}/{len(segment_plan)} "
                        f"with {role} style and voice transform ({effect_mode})."
                    ),
                    progress,
                    callback=progress_callback,
                )
        return segment_paths

    def _build_performer_transform_profile(self, performer: dict[str, Any], segment_index: int) -> dict[str, float | str]:
        gender = str(performer.get("gender") or "female")
        heritage = str(performer.get("heritage") or "english")
        role = str(performer.get("role") or "dance_performer")
        is_lead = role == "lead_vocal_performer"

        pitch_semitones = 2.6 if gender == "female" else -2.2
        if heritage == "hindi":
            pitch_semitones += 0.2 if gender == "female" else -0.1
        elif heritage == "nepali":
            pitch_semitones += 0.1

        curve_preset = "increase_contrast" if is_lead else "medium_contrast"
        hue_offset = {"english": 0.0, "nepali": 2.5, "hindi": 5.5}.get(heritage, 0.0)
        noise = 2.8 if is_lead else 3.8
        blur_sigma = 0.10 if is_lead else 0.18

        if gender == "female":
            saturation_gain = 1.23 if is_lead else 1.13
            contrast_gain = 1.12 if is_lead else 1.05
            brightness_shift = 0.014 if is_lead else 0.006
            gamma = 1.02
            bass_gain = -0.8
            presence_gain = 2.8
            echo_delay_ms = 55
            echo_decay = 0.2
            volume_multiplier = 1.12
        else:
            saturation_gain = 1.09 if is_lead else 1.03
            contrast_gain = 1.16 if is_lead else 1.09
            brightness_shift = -0.006 if is_lead else -0.01
            gamma = 0.98
            bass_gain = 1.8
            presence_gain = 1.5
            echo_delay_ms = 65
            echo_decay = 0.17
            volume_multiplier = 1.06

        if heritage == "hindi":
            saturation_gain += 0.08
            hue_offset += 1.5
            presence_gain += 0.6
            echo_decay += 0.02
        elif heritage == "nepali":
            saturation_gain += 0.04
            hue_offset += 0.8
            bass_gain += 0.4

        hue_saturation = self._clamp(1.0 + (0.03 if is_lead else 0.0), 0.95, 1.2)
        if segment_index % 4 == 0:
            noise += 0.7
            hue_offset += 0.6

        return {
            "pitch_semitones": self._clamp(pitch_semitones, -4.0, 4.0),
            "brightness_shift": self._clamp(brightness_shift, -0.04, 0.04),
            "contrast_gain": self._clamp(contrast_gain, 0.9, 1.25),
            "saturation_gain": self._clamp(saturation_gain, 0.9, 1.35),
            "gamma": self._clamp(gamma, 0.92, 1.08),
            "hue_offset": self._clamp(hue_offset, -8.0, 12.0),
            "hue_saturation": hue_saturation,
            "bass_gain": self._clamp(bass_gain, -3.0, 3.0),
            "presence_gain": self._clamp(presence_gain, -1.0, 4.5),
            "echo_delay_ms": float(self._clamp_int(int(echo_delay_ms), 30, 90)),
            "echo_decay": self._clamp(echo_decay, 0.08, 0.30),
            "volume_multiplier": self._clamp(volume_multiplier, 0.9, 1.2),
            "curve_preset": curve_preset,
            "noise": self._clamp(noise, 1.2, 6.0),
            "blur_sigma": self._clamp(blur_sigma, 0.06, 0.32),
        }

    def _append_processing_step(
        self,
        processing_steps: list[dict[str, Any]],
        stage: str,
        detail: str,
        progress: float,
        callback: Callable[[dict[str, Any]], None] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        step = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "detail": detail,
            "progress": round(self._clamp(progress, 0.0, 1.0), 4),
        }
        if extra:
            step.update(extra)
        processing_steps.append(step)
        if callback is not None:
            callback(step)

    def _extract_values(self, text: str, pattern: str) -> list[float]:
        values: list[float] = []
        for match in re.finditer(pattern, text):
            try:
                values.append(float(match.group(1)))
            except (TypeError, ValueError):
                continue
        return values

    def _average(self, values: list[float], fallback: float) -> float:
        if not values:
            return fallback
        return sum(values) / len(values)

    def _clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _clamp_int(self, value: int, low: int, high: int) -> int:
        return max(low, min(high, value))

    def _run_command(self, command: list[str]) -> None:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            detail = stderr[-1800:] if stderr else stdout[-1800:]
            raise RuntimeError(f"Command failed: {' '.join(command)}\n{detail}")
