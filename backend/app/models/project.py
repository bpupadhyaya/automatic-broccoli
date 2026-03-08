from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    target_original_video_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    example_original_video_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    example_remix_video_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    character_style: Mapped[str] = mapped_column(String(255), nullable=False)
    region_style_swap: Mapped[str] = mapped_column(String(255), nullable=False)
    gender_mix: Mapped[str] = mapped_column(String(255), nullable=False)
    age_group: Mapped[str] = mapped_column(String(255), nullable=False)
    ethnic_cultural_direction: Mapped[str] = mapped_column(String(255), nullable=False)
    celebrity_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="fictional_only")

    visual_theme: Mapped[str] = mapped_column(String(255), nullable=False)
    costume_style: Mapped[str] = mapped_column(String(255), nullable=False)
    lighting_style: Mapped[str] = mapped_column(String(255), nullable=False)
    cinematic_mood: Mapped[str] = mapped_column(String(255), nullable=False)
    dance_style: Mapped[str] = mapped_column(String(255), nullable=False)
    energy_level: Mapped[str] = mapped_column(String(255), nullable=False)
    camera_style: Mapped[str] = mapped_column(String(255), nullable=False)

    preserve_melody: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    remix_genre: Mapped[str] = mapped_column(String(255), nullable=False)
    beat_intensity: Mapped[str] = mapped_column(String(255), nullable=False)
    vocal_handling: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    config_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    transformation_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    character_bible: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    storyboard_scenes: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    scene_prompts: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    editing_plan: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    consistency_rules: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    manifest: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
