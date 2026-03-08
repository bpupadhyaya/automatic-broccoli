from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

CelebrityMode = Literal[
    "fictional_only",
    "celebrity_inspired_only",
    "licensed_real_celebrity_only",
]


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(ORMBaseModel):
    target_original_video_url: HttpUrl
    example_original_video_url: HttpUrl
    example_remix_video_url: HttpUrl

    character_style: str = Field(min_length=1, max_length=255)
    region_style_swap: str = Field(min_length=1, max_length=255)
    gender_mix: str = Field(min_length=1, max_length=255)
    age_group: str = Field(min_length=1, max_length=255)
    ethnic_cultural_direction: str = Field(min_length=1, max_length=255)
    # Real celebrity likeness requires legal rights/licensing. Default stays fictional_only for safety.
    celebrity_mode: CelebrityMode = "fictional_only"

    visual_theme: str = Field(min_length=1, max_length=255)
    costume_style: str = Field(min_length=1, max_length=255)
    lighting_style: str = Field(min_length=1, max_length=255)
    cinematic_mood: str = Field(min_length=1, max_length=255)
    dance_style: str = Field(min_length=1, max_length=255)
    energy_level: str = Field(min_length=1, max_length=255)
    camera_style: str = Field(min_length=1, max_length=255)

    preserve_melody: bool = True
    remix_genre: str = Field(min_length=1, max_length=255)
    beat_intensity: str = Field(min_length=1, max_length=255)
    vocal_handling: str = Field(min_length=1, max_length=255)


class ProjectSummary(ORMBaseModel):
    id: int
    target_original_video_url: str
    remix_genre: str
    celebrity_mode: CelebrityMode
    status: str
    created_at: datetime


class CharacterBible(ORMBaseModel):
    cast_name: str
    aliases: list[str]
    persona_summary: str
    styling_notes: list[str]
    movement_notes: list[str]


class CharacterProfile(ORMBaseModel):
    name: str
    role: str
    identity: dict
    references: list[str]


class Scene(ORMBaseModel):
    scene_number: int
    title: str
    setting: str
    visual_focus: str
    choreography_note: str


class ScenePrompt(ORMBaseModel):
    scene_number: int
    prompt: str


class ProjectPlanResponse(ORMBaseModel):
    transformation_summary: str
    character_bible: CharacterBible
    storyboard_scenes: list[Scene]
    scene_prompts: list[ScenePrompt]
    editing_plan: list[str]
    consistency_rules: list[str]
    manifest: dict


class ProjectListItem(ProjectSummary):
    pass


class ProjectDetail(ProjectSummary):
    example_original_video_url: str
    example_remix_video_url: str
    character_style: str
    region_style_swap: str
    gender_mix: str
    age_group: str
    ethnic_cultural_direction: str
    visual_theme: str
    costume_style: str
    lighting_style: str
    cinematic_mood: str
    dance_style: str
    energy_level: str
    camera_style: str
    preserve_melody: bool
    beat_intensity: str
    vocal_handling: str
    config_json: Optional[dict]
    transformation_summary: Optional[str]
    character_bible: Optional[CharacterBible]
    storyboard_scenes: Optional[list[Scene]]
    scene_prompts: Optional[list[ScenePrompt]]
    editing_plan: Optional[list[str]]
    consistency_rules: Optional[list[str]]
    manifest: Optional[dict]
    updated_at: datetime


class RemixProjectRead(ProjectDetail):
    pass


class ManifestResponse(ORMBaseModel):
    project_id: int
    manifest: dict
