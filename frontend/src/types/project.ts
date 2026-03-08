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
  config_json: Record<string, unknown> | null;
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

export interface CharacterSummary {
  id: number;
  project_id: number;
  name: string;
  role: string;
  identity_summary: string | null;
  age_range: string | null;
  style_archetype: string | null;
  movement_style: string | null;
  is_locked: boolean;
  identity_json: Record<string, unknown>;
  reference_asset_urls: string[];
  consistency_rules_json: string[];
  created_at: string;
}

export interface CharacterListResponse {
  project_id: number;
  characters: CharacterSummary[];
}

export interface CharacterGenerateResponse {
  project_id: number;
  candidates: CharacterSummary[];
}

export interface CharacterLockResponse {
  character: CharacterSummary;
}

export interface ApplyCharacterToShotsResponse {
  project_id: number;
  character_id: number;
  updated_shot_count: number;
}

export type QuickRemixProfile = "english" | "nepali" | "hindi";
export type QuickCastPreset = "female" | "male" | "mixed";
export type QuickHeritageMode = "preserve" | "swap_to_english" | "swap_to_nepali" | "swap_to_hindi" | "mix";
export type YouTubePrivacyStatus = "private" | "unlisted" | "public";

export interface QuickProjectCreateInput {
  target_original_video_url: string;
  example_original_video_url: string;
  example_remix_video_url: string;
  remix_profile: QuickRemixProfile;
  cast_preset: QuickCastPreset;
  heritage_mode: QuickHeritageMode;
  auto_generate_plan: boolean;
  run_end_to_end: boolean;
  local_output_dir?: string;
  allow_youtube_upload: boolean;
  youtube_title?: string;
  youtube_description?: string;
  youtube_privacy_status: YouTubePrivacyStatus;
}

export interface QuickConversionOutput {
  project_id: number;
  output_video_path: string;
  output_dir: string;
  download_url: string;
  youtube_upload?: Record<string, unknown> | null;
}

export interface QuickProcessingStep {
  timestamp: string;
  stage: string;
  detail: string;
  progress: number;
}

export interface QuickConversionProgress {
  project_id: number;
  status: string;
  execution: string;
  progress: number;
  current_stage?: string | null;
  processing_steps: QuickProcessingStep[];
  started_at?: string | null;
  elapsed_seconds?: number | null;
  active_worker_threads?: number;
  output_video_path?: string | null;
  download_url?: string | null;
  execution_error?: string | null;
  youtube_upload?: Record<string, unknown> | null;
}

export interface DownloadVideoItem {
  project_id: number;
  video_title: string;
  remix_details: string;
  download_url: string;
  created_at: string;
}

export interface YouTubeVideoDownloadResult {
  youtube_video_url: string;
  video_title: string;
  output_file_path: string;
  output_dir: string;
  file_size_bytes: number;
  downloaded_at: string;
}
