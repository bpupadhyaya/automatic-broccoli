from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    identity_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reference_asset_urls: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    consistency_rules_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    identity_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    age_range: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    style_archetype: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    face_features_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    body_features_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    movement_style: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_locked: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CharacterAsset(Base):
    __tablename__ = "character_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    prompt_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CharacterOutfit(Base):
    __tablename__ = "character_outfits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outfit_name: Mapped[str] = mapped_column(String(128), nullable=False)
    palette_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_asset_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    shot_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(64), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    shot_type: Mapped[str] = mapped_column(String(255), nullable=False)
    camera_framing: Mapped[str] = mapped_column(String(255), nullable=False)
    camera_move: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    cast_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    wardrobe: Mapped[str] = mapped_column(String(255), nullable=False)
    choreography_note: Mapped[str] = mapped_column(Text, nullable=False)
    lighting_note: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    references_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    qc_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    approved_clip_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class RenderJob(Base):
    __tablename__ = "render_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_job_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    raw_output_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    output_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    qc_result_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Manifest(Base):
    __tablename__ = "manifests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Export(Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="processing")
    output_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class QcResultRecord(Base):
    __tablename__ = "qc_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id", ondelete="CASCADE"), nullable=False, index=True)
    render_job_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("render_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scores_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    identity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wardrobe_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    motion_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prompt_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
