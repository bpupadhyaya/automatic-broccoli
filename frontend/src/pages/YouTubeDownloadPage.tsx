import { useState } from "react";

import PageCard from "../components/PageCard";
import { formatDate } from "../lib/utils";
import { downloadYouTubeVideo } from "../services/api";
import type { YouTubeVideoDownloadResult } from "../types/project";

const SAMPLE_URL = "https://www.youtube.com/watch?v=Ubm7DWRSrg4";

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(idx === 0 ? 0 : 2)} ${units[idx]}`;
}

export default function YouTubeDownloadPage() {
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<YouTubeVideoDownloadResult | null>(null);

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const payload = await downloadYouTubeVideo(youtubeUrl.trim());
      setResult(payload);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Failed to download YouTube video");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageCard
        title="Download YouTube Video"
        subtitle="Download the highest available quality and save it to the host machine Downloads folder."
      >
        <form className="space-y-4" onSubmit={onSubmit}>
          <label className="space-y-1 text-sm">
            <span className="font-medium text-slate-700">YouTube Video URL</span>
            <div className="flex items-center gap-2">
              <input
                type="url"
                required
                value={youtubeUrl}
                onChange={(event) => setYoutubeUrl(event.target.value)}
                className="w-full rounded-md border border-slate-300 px-3 py-2"
                placeholder="https://www.youtube.com/watch?v=..."
              />
              <button
                type="button"
                onClick={() => setYoutubeUrl(SAMPLE_URL)}
                className="rounded-md border border-slate-300 bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200"
              >
                Sample
              </button>
            </div>
          </label>

          <p className="text-xs text-slate-600">Destination: default Downloads folder on the host machine.</p>

          {error && <p className="rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</p>}

          <button
            type="submit"
            disabled={submitting || youtubeUrl.trim().length === 0}
            className="rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            {submitting ? "Downloading..." : "Download YouTube Video"}
          </button>
        </form>
      </PageCard>

      {result && (
        <PageCard title="Download Complete">
          <dl className="space-y-2 text-sm text-slate-700">
            <div>
              <dt className="font-semibold text-slate-800">Video Title</dt>
              <dd>{result.video_title}</dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-800">Source URL</dt>
              <dd>
                <a href={result.youtube_video_url} target="_blank" rel="noreferrer" className="break-all text-brand-700 hover:underline">
                  {result.youtube_video_url}
                </a>
              </dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-800">Saved File</dt>
              <dd className="break-all font-mono text-xs">{result.output_file_path}</dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-800">Size</dt>
              <dd>{formatBytes(result.file_size_bytes)}</dd>
            </div>
            <div>
              <dt className="font-semibold text-slate-800">Downloaded At</dt>
              <dd>{formatDate(result.downloaded_at)}</dd>
            </div>
          </dl>
        </PageCard>
      )}
    </div>
  );
}
