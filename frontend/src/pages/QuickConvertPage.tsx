import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import PageCard from "../components/PageCard";
import { ROUTES } from "../routes";
import { getQuickConversionProgress, quickConvertProject } from "../services/api";
import type { QuickConversionProgress, QuickProjectCreateInput } from "../types/project";

const initialState: QuickProjectCreateInput = {
  target_original_video_url: "",
  example_original_video_url: "",
  example_remix_video_url: "",
  remix_profile: "english",
  cast_preset: "mixed",
  heritage_mode: "preserve",
  auto_generate_plan: true,
  run_end_to_end: true,
  local_output_dir: "",
  allow_youtube_upload: false,
  youtube_title: "",
  youtube_description: "",
  youtube_privacy_status: "private",
};

const SAMPLE_TARGET_URL = "https://www.youtube.com/watch?v=Ubm7DWRSrg4&list=RDUbm7DWRSrg4&start_radio=1";
const SAMPLE_EXAMPLE_ORIGINAL_URL = "https://www.youtube.com/watch?v=EsTt9jy_mG8&list=RDEsTt9jy_mG8&start_radio=1";
const SAMPLE_EXAMPLE_REMIX_URL = "https://www.youtube.com/watch?v=3JSbeTVVn_E&list=RD3JSbeTVVn_E&start_radio=1";

function mapBackendStageToStepIndex(stage: string | null | undefined, stepCount: number): number {
  const normalized = (stage ?? "").toLowerCase();
  if (!normalized) {
    return 0;
  }
  if (normalized.includes("queued") || normalized.includes("initialize") || normalized.includes("plan generation")) {
    return 0;
  }
  if (normalized.includes("download")) {
    return Math.min(stepCount - 1, 1);
  }
  if (normalized.includes("analyze") || normalized.includes("learn transformation")) {
    return Math.min(stepCount - 1, 2);
  }
  if (normalized.includes("cast synthesis") || normalized.includes("segment planning")) {
    return Math.min(stepCount - 1, 3);
  }
  if (
    normalized.includes("render segments") ||
    normalized.includes("render voice") ||
    normalized.includes("face synthesis") ||
    normalized.includes("reference portraits")
  ) {
    return Math.min(stepCount - 1, 4);
  }
  if (normalized.includes("compose output") || normalized.includes("finalize") || normalized.includes("mux")) {
    return Math.min(stepCount - 1, 5);
  }
  if (normalized.includes("upload")) {
    return Math.min(stepCount - 1, 6);
  }
  if (normalized.includes("completed")) {
    return Math.max(stepCount - 1, 0);
  }
  return 0;
}

function formatElapsed(seconds: number | null): string {
  if (seconds == null || !Number.isFinite(seconds)) {
    return "--";
  }
  const rounded = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(rounded / 60);
  const secs = rounded % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export default function QuickConvertPage() {
  const [form, setForm] = useState<QuickProjectCreateInput>(initialState);
  const [submitting, setSubmitting] = useState(false);
  const [activeConversionStep, setActiveConversionStep] = useState(0);
  const [activityFeed, setActivityFeed] = useState<string[]>([]);
  const [conversionProjectId, setConversionProjectId] = useState<number | null>(null);
  const [backendProgressRatio, setBackendProgressRatio] = useState(0);
  const [backendStage, setBackendStage] = useState<string | null>(null);
  const [backendExecution, setBackendExecution] = useState<string | null>(null);
  const [backendElapsedSeconds, setBackendElapsedSeconds] = useState<number | null>(null);
  const [backendActiveWorkers, setBackendActiveWorkers] = useState(0);
  const [conversionStartedAtMs, setConversionStartedAtMs] = useState<number | null>(null);
  const [elapsedTicker, setElapsedTicker] = useState(0);
  const [autoScrollFeed, setAutoScrollFeed] = useState(true);
  const [autoScrollSteps, setAutoScrollSteps] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activityFeedContainerRef = useRef<HTMLDivElement | null>(null);
  const conversionStepsContainerRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();

  const ready = useMemo(
    () =>
      Boolean(form.target_original_video_url && form.example_original_video_url && form.example_remix_video_url),
    [form.target_original_video_url, form.example_original_video_url, form.example_remix_video_url]
  );

  const conversionSteps = useMemo(() => {
    const steps = [
      "Queue conversion job and initialize processing context.",
      "Download source videos from YouTube.",
      "Analyze target and learn transformations from example pair.",
      "Synthesize fictitious cast and build remix segment plan.",
      "Render transformed non-linear segments (visual + voice).",
      "Compose output, finalize status, and prepare download artifact.",
    ];

    if (form.allow_youtube_upload) {
      steps.push("Upload remixed output to YouTube with selected privacy.");
    }

    return steps;
  }, [form.allow_youtube_upload]);

  useEffect(() => {
    if (!submitting || conversionProjectId == null) {
      return;
    }
    let cancelled = false;

    const syncProgress = (progressPayload: QuickConversionProgress) => {
      if (cancelled) {
        return;
      }
      setBackendExecution(progressPayload.execution);
      setBackendProgressRatio(progressPayload.progress ?? 0);
      setBackendStage(progressPayload.current_stage ?? null);
      setBackendElapsedSeconds(typeof progressPayload.elapsed_seconds === "number" ? progressPayload.elapsed_seconds : null);
      setBackendActiveWorkers(progressPayload.active_worker_threads ?? 0);
      if (progressPayload.started_at) {
        const startedMs = Date.parse(progressPayload.started_at);
        if (!Number.isNaN(startedMs)) {
          setConversionStartedAtMs((current) => current ?? startedMs);
        }
      }
      setActiveConversionStep(
        mapBackendStageToStepIndex(progressPayload.current_stage, conversionSteps.length)
      );

      const messages = progressPayload.processing_steps.map((step) => `${step.stage}: ${step.detail}`);
      setActivityFeed(messages);

      if (progressPayload.execution === "completed") {
        setActiveConversionStep(conversionSteps.length - 1);
        setSubmitting(false);
        navigate(ROUTES.projectDetails(progressPayload.project_id));
        return;
      }
      if (progressPayload.execution === "failed") {
        setSubmitting(false);
        setError(progressPayload.execution_error ?? "Quick conversion failed");
      }
    };

    const pollProgress = async () => {
      try {
        const progressPayload = await getQuickConversionProgress(conversionProjectId);
        syncProgress(progressPayload);
      } catch (err) {
        if (cancelled) {
          return;
        }
        setSubmitting(false);
        setError(err instanceof Error ? err.message : "Unable to fetch live conversion progress");
      }
    };

    pollProgress();
    const timer = window.setInterval(pollProgress, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [submitting, conversionProjectId, conversionSteps.length, navigate]);

  useEffect(() => {
    if (!submitting || conversionStartedAtMs == null || backendElapsedSeconds != null) {
      return;
    }
    const timer = window.setInterval(() => {
      setElapsedTicker((current) => current + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [submitting, conversionStartedAtMs, backendElapsedSeconds]);

  const scrollActivityToBottom = () => {
    const container = activityFeedContainerRef.current;
    if (!container) {
      return;
    }
    container.scrollTop = container.scrollHeight;
  };

  useEffect(() => {
    if (!autoScrollFeed) {
      return;
    }
    const handle = window.requestAnimationFrame(() => {
      scrollActivityToBottom();
    });
    return () => window.cancelAnimationFrame(handle);
  }, [activityFeed, autoScrollFeed]);

  const scrollStepsToActive = () => {
    const container = conversionStepsContainerRef.current;
    if (!container) {
      return;
    }
    const active = container.querySelector<HTMLElement>(`[data-step-index="${activeConversionStep}"]`);
    if (!active) {
      container.scrollTop = container.scrollHeight;
      return;
    }
    const centeredTop = active.offsetTop - (container.clientHeight / 2) + (active.clientHeight / 2);
    container.scrollTop = Math.max(0, centeredTop);
  };

  useEffect(() => {
    if (!autoScrollSteps) {
      return;
    }
    const handle = window.requestAnimationFrame(() => {
      scrollStepsToActive();
    });
    return () => window.cancelAnimationFrame(handle);
  }, [activeConversionStep, conversionSteps.length, autoScrollSteps]);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setActiveConversionStep(0);
    setActivityFeed([]);
    setConversionProjectId(null);
    setBackendProgressRatio(0);
    setBackendStage(null);
    setBackendExecution(null);
    setBackendElapsedSeconds(null);
    setBackendActiveWorkers(0);
    setConversionStartedAtMs(Date.now());
    setElapsedTicker(0);
    setAutoScrollFeed(true);
    setAutoScrollSteps(true);
    setSubmitting(true);
    setError(null);
    try {
      const payload: QuickProjectCreateInput = {
        ...form,
        local_output_dir: form.local_output_dir?.trim() || undefined,
        youtube_title: form.youtube_title?.trim() || undefined,
        youtube_description: form.youtube_description?.trim() || undefined,
      };
      const project = await quickConvertProject(payload);
      if (!payload.run_end_to_end) {
        setSubmitting(false);
        navigate(ROUTES.projectDetails(project.id));
        return;
      }
      setConversionProjectId(project.id);
      setBackendExecution("queued");
      setBackendStage("Queued");
      setBackendProgressRatio(0.01);
      setBackendActiveWorkers(0);
      setActivityFeed(["Queued: Quick conversion request accepted. Waiting for backend worker updates."]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Quick conversion failed");
      setSubmitting(false);
    }
  };

  const elapsedSeconds =
    backendElapsedSeconds ??
    (submitting && conversionStartedAtMs != null
      ? Math.max((Date.now() - conversionStartedAtMs + (elapsedTicker * 0)) / 1000, 0)
      : null);

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
              <div className="flex items-center gap-2">
                <input
                  type="url"
                  required
                  value={form.target_original_video_url}
                  onChange={(event) => setForm((prev) => ({ ...prev, target_original_video_url: event.target.value }))}
                  className="w-full rounded-md border border-slate-300 px-3 py-2"
                />
                <button
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, target_original_video_url: SAMPLE_TARGET_URL }))}
                  className="rounded-md border border-slate-300 bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200"
                >
                  Sample
                </button>
              </div>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Example Original Video URL</span>
              <div className="flex items-center gap-2">
                <input
                  type="url"
                  required
                  value={form.example_original_video_url}
                  onChange={(event) => setForm((prev) => ({ ...prev, example_original_video_url: event.target.value }))}
                  className="w-full rounded-md border border-slate-300 px-3 py-2"
                />
                <button
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, example_original_video_url: SAMPLE_EXAMPLE_ORIGINAL_URL }))}
                  className="rounded-md border border-slate-300 bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200"
                >
                  Sample
                </button>
              </div>
            </label>
            <label className="space-y-1 text-sm">
              <span className="font-medium text-slate-700">Example Remix Video URL</span>
              <div className="flex items-center gap-2">
                <input
                  type="url"
                  required
                  value={form.example_remix_video_url}
                  onChange={(event) => setForm((prev) => ({ ...prev, example_remix_video_url: event.target.value }))}
                  className="w-full rounded-md border border-slate-300 px-3 py-2"
                />
                <button
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, example_remix_video_url: SAMPLE_EXAMPLE_REMIX_URL }))}
                  className="rounded-md border border-slate-300 bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200"
                >
                  Sample
                </button>
              </div>
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

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.run_end_to_end}
              onChange={(event) => setForm((prev) => ({ ...prev, run_end_to_end: event.target.checked }))}
            />
            Run end-to-end remix and generate local MP4 output
          </label>

          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-700">Local Output Folder (optional)</span>
            <input
              type="text"
              value={form.local_output_dir ?? ""}
              onChange={(event) => setForm((prev) => ({ ...prev, local_output_dir: event.target.value }))}
              placeholder="Default: ./outputs/project_{id} (host mapped from backend /app/outputs)"
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.allow_youtube_upload}
              onChange={(event) => setForm((prev) => ({ ...prev, allow_youtube_upload: event.target.checked }))}
            />
            Upload remixed video to YouTube (requires server OAuth credentials)
          </label>

          {form.allow_youtube_upload && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <label className="space-y-1 text-sm md:col-span-2">
                <span className="font-medium text-slate-700">YouTube Title (optional)</span>
                <input
                  type="text"
                  value={form.youtube_title ?? ""}
                  onChange={(event) => setForm((prev) => ({ ...prev, youtube_title: event.target.value }))}
                  className="w-full rounded-md border border-slate-300 px-3 py-2"
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="font-medium text-slate-700">Privacy</span>
                <select
                  value={form.youtube_privacy_status}
                  onChange={(event) =>
                    setForm((prev) => ({
                      ...prev,
                      youtube_privacy_status: event.target.value as QuickProjectCreateInput["youtube_privacy_status"],
                    }))
                  }
                  className="w-full rounded-md border border-slate-300 px-3 py-2"
                >
                  <option value="private">Private</option>
                  <option value="unlisted">Unlisted</option>
                  <option value="public">Public</option>
                </select>
              </label>
              <label className="space-y-1 text-sm md:col-span-3">
                <span className="font-medium text-slate-700">YouTube Description (optional)</span>
                <textarea
                  rows={3}
                  value={form.youtube_description ?? ""}
                  onChange={(event) => setForm((prev) => ({ ...prev, youtube_description: event.target.value }))}
                  className="w-full rounded-md border border-slate-300 px-3 py-2"
                />
              </label>
            </div>
          )}

          <div className="rounded-md bg-slate-50 p-3 text-xs text-slate-700">
            <p className="font-semibold">Default behavior</p>
            <p>English, Nepali, and Hindi profiles use fictional cast defaults with profile-specific styling.</p>
            <p>Heritage mode lets you preserve, swap, or mix English/Nepali/Hindi performer heritage.</p>
            <p>If output folder is empty, remixed files are written under the default quick output root.</p>
          </div>

          {error && <p className="rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</p>}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[auto_minmax(0,1fr)]">
            <button
              type="submit"
              disabled={!ready || submitting}
              className="h-fit rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {submitting ? "Converting..." : "Quick Convert"}
            </button>

            {submitting && (
              <div className="rounded-md border border-brand-200 bg-brand-50 p-3">
                <p className="text-sm font-semibold text-brand-800">Conversion Steps</p>
                <p className="mt-1 text-xs text-brand-700">
                  Live backend progress from the conversion worker.
                </p>
                <div className="mt-2 grid grid-cols-1 gap-1 text-xs text-brand-800 md:grid-cols-5">
                  <p>
                    <span className="font-semibold">Project:</span>{" "}
                    {conversionProjectId ? `#${conversionProjectId}` : "starting..."}
                  </p>
                  <p>
                    <span className="font-semibold">Stage:</span> {backendStage ?? "Queued"}
                  </p>
                  <p>
                    <span className="font-semibold">Progress:</span>{" "}
                    {(backendProgressRatio * 100).toFixed(1)}% ({backendExecution ?? "queued"})
                  </p>
                  <p>
                    <span className="font-semibold">Workers:</span> {backendActiveWorkers}
                  </p>
                  <p>
                    <span className="font-semibold">Elapsed:</span> {formatElapsed(elapsedSeconds)}
                  </p>
                </div>
                <div className="mt-2">
                  <div className="h-2 w-full overflow-hidden rounded bg-brand-100">
                    <div
                      className="h-full rounded bg-brand-500 transition-all duration-300"
                      style={{ width: `${Math.max(2, Math.min(100, backendProgressRatio * 100))}%` }}
                    />
                  </div>
                </div>
                <div className="mt-4 rounded-md border border-brand-100 bg-white/80 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold text-brand-800">Conversion Steps</p>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setAutoScrollSteps((current) => {
                            const next = !current;
                            if (next) {
                              window.requestAnimationFrame(() => {
                                scrollStepsToActive();
                              });
                            }
                            return next;
                          });
                        }}
                        className="rounded border border-brand-200 bg-white px-2 py-1 text-[10px] font-semibold text-brand-700 hover:bg-brand-50"
                      >
                        {autoScrollSteps ? "Pause Auto-Scroll" : "Resume Auto-Scroll"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          scrollStepsToActive();
                          setAutoScrollSteps(true);
                        }}
                        className="rounded border border-brand-200 bg-white px-2 py-1 text-[10px] font-semibold text-brand-700 hover:bg-brand-50"
                      >
                        Jump to Latest
                      </button>
                    </div>
                  </div>
                  <div ref={conversionStepsContainerRef} className="mt-2 max-h-48 overflow-y-auto pr-1">
                    <ol className="space-y-2 text-xs">
                      {conversionSteps.map((step, index) => {
                        const isDone = index < activeConversionStep;
                        const isActive = index === activeConversionStep;
                        return (
                          <li key={step} data-step-index={index} className="flex items-start gap-2">
                            <span
                              className={`mt-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full text-[10px] font-semibold ${
                                isDone
                                  ? "bg-emerald-100 text-emerald-700"
                                  : isActive
                                    ? "bg-brand-200 text-brand-800"
                                    : "bg-slate-200 text-slate-600"
                              }`}
                            >
                              {isDone ? "OK" : isActive ? "..." : `${index + 1}`}
                            </span>
                            <span className={isActive ? "font-semibold text-brand-900" : "text-slate-700"}>{step}</span>
                          </li>
                        );
                      })}
                    </ol>
                  </div>
                </div>

                <div className="mt-4 rounded-md border border-brand-100 bg-white/80 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold text-brand-800">Fine-Grained Remix Activity</p>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setAutoScrollFeed((current) => {
                            const next = !current;
                            if (next) {
                              window.requestAnimationFrame(() => {
                                scrollActivityToBottom();
                              });
                            }
                            return next;
                          });
                        }}
                        className="rounded border border-brand-200 bg-white px-2 py-1 text-[10px] font-semibold text-brand-700 hover:bg-brand-50"
                      >
                        {autoScrollFeed ? "Pause Auto-Scroll" : "Resume Auto-Scroll"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          scrollActivityToBottom();
                          setAutoScrollFeed(true);
                        }}
                        className="rounded border border-brand-200 bg-white px-2 py-1 text-[10px] font-semibold text-brand-700 hover:bg-brand-50"
                      >
                        Jump to Latest
                      </button>
                    </div>
                  </div>
                  <div
                    ref={activityFeedContainerRef}
                    className="mt-2 max-h-64 overflow-y-auto pr-1"
                  >
                    <ul className="space-y-1.5 text-xs text-slate-700">
                      {activityFeed.map((message, index) => {
                        const isLatest = index === activityFeed.length - 1;
                        return (
                          <li key={`${index}-${message}`} className="flex items-start gap-2">
                            <span className={`mt-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full text-[9px] font-semibold ${
                              isLatest ? "bg-brand-200 text-brand-800" : "bg-emerald-100 text-emerald-700"
                            }`}>
                              {isLatest ? "..." : "OK"}
                            </span>
                            <span className={isLatest ? "font-semibold text-brand-900" : "text-slate-700"}>{message}</span>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        </form>
      </PageCard>
    </div>
  );
}
