import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import PageCard from "../components/PageCard";
import { ROUTES } from "../routes";
import { quickConvertProject } from "../services/api";
import type { QuickProjectCreateInput } from "../types/project";

const initialState: QuickProjectCreateInput = {
  target_original_video_url: "",
  example_original_video_url: "",
  example_remix_video_url: "",
  remix_profile: "english",
  cast_preset: "mixed",
  heritage_mode: "preserve",
  auto_generate_plan: true,
};

export default function QuickConvertPage() {
  const [form, setForm] = useState<QuickProjectCreateInput>(initialState);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const ready = useMemo(
    () =>
      Boolean(form.target_original_video_url && form.example_original_video_url && form.example_remix_video_url),
    [form.target_original_video_url, form.example_original_video_url, form.example_remix_video_url]
  );

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const project = await quickConvertProject(form);
      navigate(ROUTES.projectDetails(project.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Quick conversion failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageCard
        title="Quick Conversion Flow"
        subtitle="3 URL inputs + profile-based defaults for fast project creation."
      >
        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="grid grid-cols-1 gap-4">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Target Original Video URL</span>
              <input
                type="url"
                required
                value={form.target_original_video_url}
                onChange={(event) => setForm((prev) => ({ ...prev, target_original_video_url: event.target.value }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Example Original Video URL</span>
              <input
                type="url"
                required
                value={form.example_original_video_url}
                onChange={(event) => setForm((prev) => ({ ...prev, example_original_video_url: event.target.value }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Example Remix Video URL</span>
              <input
                type="url"
                required
                value={form.example_remix_video_url}
                onChange={(event) => setForm((prev) => ({ ...prev, example_remix_video_url: event.target.value }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
              />
            </label>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Remix Profile</span>
              <select
                value={form.remix_profile}
                onChange={(event) => setForm((prev) => ({ ...prev, remix_profile: event.target.value as QuickProjectCreateInput["remix_profile"] }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
              >
                <option value="english">English Remix</option>
                <option value="nepali">Nepali Remix</option>
                <option value="hindi">Hindi Remix</option>
              </select>
            </label>

            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Cast Preset</span>
              <select
                value={form.cast_preset}
                onChange={(event) => setForm((prev) => ({ ...prev, cast_preset: event.target.value as QuickProjectCreateInput["cast_preset"] }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
              >
                <option value="mixed">Mixed</option>
                <option value="female">Girls</option>
                <option value="male">Guys</option>
              </select>
            </label>

            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Heritage Mode</span>
              <select
                value={form.heritage_mode}
                onChange={(event) => setForm((prev) => ({ ...prev, heritage_mode: event.target.value as QuickProjectCreateInput["heritage_mode"] }))}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
              >
                <option value="preserve">Preserve Profile Heritage</option>
                <option value="swap_to_english">Replace With English Actors</option>
                <option value="swap_to_nepali">Replace With Nepali Actors</option>
                <option value="swap_to_hindi">Replace With Hindi Actors</option>
                <option value="mix">Mix English + Nepali + Hindi Actors</option>
              </select>
            </label>
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.auto_generate_plan}
              onChange={(event) => setForm((prev) => ({ ...prev, auto_generate_plan: event.target.checked }))}
            />
            Auto-generate plan immediately
          </label>

          <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-700">
            <p className="font-semibold">Default behavior</p>
            <p>English, Nepali, and Hindi profiles use fictional cast defaults with profile-specific styling.</p>
            <p>Hindi defaults use girls age 18-25 and boys age 18-30.</p>
            <p>Heritage mode lets you preserve, swap, or mix English/Nepali/Hindi performer heritage.</p>
          </div>

          {error && <p className="rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</p>}

          <button
            type="submit"
            disabled={!ready || submitting}
            className="rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {submitting ? "Creating..." : "Quick Convert"}
          </button>
        </form>
      </PageCard>
    </div>
  );
}
