import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import PageCard from "../components/PageCard";
import { ROUTES } from "../routes";
import { createProject } from "../services/api";
import type { CelebrityMode, ProjectCreateInput } from "../types/project";

const initialFormState: ProjectCreateInput = {
  target_original_video_url: "",
  example_original_video_url: "",
  example_remix_video_url: "",
  character_style: "Stylized cinematic performer",
  region_style_swap: "US pop x Afro-fusion",
  gender_mix: "Androgynous",
  age_group: "Young adult",
  ethnic_cultural_direction: "Global diaspora inspired",
  celebrity_mode: "fictional_only",
  visual_theme: "Neon city noir",
  costume_style: "Futuristic street couture",
  lighting_style: "High contrast teal-orange",
  cinematic_mood: "Ambitious and euphoric",
  dance_style: "Hip hop freestyle",
  energy_level: "High",
  camera_style: "Dynamic handheld and dolly",
  preserve_melody: true,
  remix_genre: "Electronic dance pop",
  beat_intensity: "Punchy",
  vocal_handling: "Layered harmonics",
};

const fields: Array<{ key: keyof ProjectCreateInput; label: string; type?: "text" | "url" | "select" | "boolean" }> = [
  { key: "target_original_video_url", label: "Target Original Video URL", type: "url" },
  { key: "example_original_video_url", label: "Example Original Video URL", type: "url" },
  { key: "example_remix_video_url", label: "Example Remix Video URL", type: "url" },
  { key: "character_style", label: "Character Style", type: "text" },
  { key: "region_style_swap", label: "Region/Style Swap", type: "text" },
  { key: "gender_mix", label: "Gender Mix", type: "text" },
  { key: "age_group", label: "Age Group", type: "text" },
  { key: "ethnic_cultural_direction", label: "Ethnic/Cultural Direction", type: "text" },
  { key: "celebrity_mode", label: "Celebrity Mode", type: "select" },
  { key: "visual_theme", label: "Visual Theme", type: "text" },
  { key: "costume_style", label: "Costume Style", type: "text" },
  { key: "lighting_style", label: "Lighting Style", type: "text" },
  { key: "cinematic_mood", label: "Cinematic Mood", type: "text" },
  { key: "dance_style", label: "Dance Style", type: "text" },
  { key: "energy_level", label: "Energy Level", type: "text" },
  { key: "camera_style", label: "Camera Style", type: "text" },
  { key: "preserve_melody", label: "Preserve Melody", type: "boolean" },
  { key: "remix_genre", label: "Remix Genre", type: "text" },
  { key: "beat_intensity", label: "Beat Intensity", type: "text" },
  { key: "vocal_handling", label: "Vocal Handling", type: "text" },
];

const celebrityModes: CelebrityMode[] = [
  "fictional_only",
  // Inspired mode still uses fictional identities; no direct likeness cloning.
  "celebrity_inspired_only",
  // Real-celebrity output is only valid when legal rights and licensing are secured.
  "licensed_real_celebrity_only",
];

export default function CreateProjectPage() {
  const [form, setForm] = useState<ProjectCreateInput>(initialFormState);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const isReady = useMemo(
    () =>
      Boolean(
        form.target_original_video_url && form.example_original_video_url && form.example_remix_video_url
      ),
    [form.target_original_video_url, form.example_original_video_url, form.example_remix_video_url]
  );

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const project = await createProject(form);
      navigate(ROUTES.projectDetails(project.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageCard
        title="Create Remix Project"
        subtitle="Safety note: cloning real celebrity likeness requires legal rights and licensing."
      >
        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {fields.map((field) => {
              if (field.type === "boolean") {
                return (
                  <label key={field.key} className="flex items-center gap-3 rounded-md border border-slate-200 bg-slate-50 p-3">
                    <input
                      type="checkbox"
                      checked={form.preserve_melody}
                      onChange={(event) => setForm((prev) => ({ ...prev, preserve_melody: event.target.checked }))}
                    />
                    <span className="text-sm font-medium text-slate-800">{field.label}</span>
                  </label>
                );
              }

              if (field.type === "select") {
                return (
                  <label key={field.key} className="space-y-1 text-sm">
                    <span className="font-medium text-slate-700">{field.label}</span>
                    <select
                      value={form.celebrity_mode}
                      onChange={(event) =>
                        setForm((prev) => ({ ...prev, celebrity_mode: event.target.value as CelebrityMode }))
                      }
                      className="w-full rounded-md border border-slate-300 px-3 py-2"
                    >
                      {celebrityModes.map((mode) => (
                        <option key={mode} value={mode}>
                          {mode}
                        </option>
                      ))}
                    </select>
                  </label>
                );
              }

              return (
                <label key={field.key} className="space-y-1 text-sm">
                  <span className="font-medium text-slate-700">{field.label}</span>
                  <input
                    type={field.type === "url" ? "url" : "text"}
                    value={String(form[field.key])}
                    onChange={(event) =>
                      setForm((prev) => ({ ...prev, [field.key]: event.target.value }))
                    }
                    required={field.type === "url"}
                    className="w-full rounded-md border border-slate-300 px-3 py-2"
                  />
                </label>
              );
            })}
          </div>

          {error && <p className="rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</p>}

          <button
            type="submit"
            disabled={!isReady || submitting}
            className="rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {submitting ? "Creating..." : "Create Project"}
          </button>
        </form>
      </PageCard>
    </div>
  );
}
