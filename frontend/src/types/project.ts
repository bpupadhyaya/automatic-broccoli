export type CelebrityMode = "fictional_only" | "celebrity_inspired_only" | "licensed_real_celebrity_only";

export interface ProjectCreateInput {
  target_original_video_url: string;
  example_original_video_url: string;
  example_remix_video_url: string;
  character_style: string;
  region_style_swap: string;
  gender_mix: string;
  age_group: string;
  ethnic_cultural_direction: string;
  celebrity_mode: CelebrityMode;
  visual_theme: string;
  costume_style: string;
  lighting_style: string;
  cinematic_mood: string;
  dance_style: string;
  energy_level: string;
  camera_style: string;
  preserve_melody: boolean;
  remix_genre: string;
  beat_intensity: string;
  vocal_handling: string;
}

export interface CharacterBible {
  cast_name: string;
  aliases: string[];
  persona_summary: string;
  styling_notes: string[];
  movement_notes: string[];
}

export interface Scene {
  scene_number: number;
  title: string;
  setting: string;
  visual_focus: string;
  choreography_note: string;
}

export interface ScenePrompt {
  scene_number: number;
  prompt: string;
}

export interface ProjectSummary {
  id: number;
  target_original_video_url: string;
  remix_genre: string;
  celebrity_mode: CelebrityMode;
  status: string;
  created_at: string;
}

export interface ProjectDetail extends ProjectSummary, ProjectCreateInput {
  transformation_summary: string | null;
  character_bible: CharacterBible | null;
  storyboard_scenes: Scene[] | null;
  scene_prompts: ScenePrompt[] | null;
  editing_plan: string[] | null;
  consistency_rules: string[] | null;
  manifest: Record<string, unknown> | null;
  updated_at: string;
}

export interface ProjectPlan {
  transformation_summary: string;
  character_bible: CharacterBible;
  storyboard_scenes: Scene[];
  scene_prompts: ScenePrompt[];
  editing_plan: string[];
  consistency_rules: string[];
  manifest: Record<string, unknown>;
}

export interface ManifestResponse {
  project_id: number;
  manifest: Record<string, unknown>;
}
