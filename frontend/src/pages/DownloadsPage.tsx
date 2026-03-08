import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import PageCard from "../components/PageCard";
import { formatDate } from "../lib/utils";
import { ROUTES } from "../routes";
import { listDownloadVideos, resolveDownloadUrl } from "../services/api";
import type { DownloadVideoItem } from "../types/project";

export default function DownloadsPage() {
  const [items, setItems] = useState<DownloadVideoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDownloadVideos()
      .then((rows) => setItems(rows))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <PageCard
        title="Downloads"
        subtitle="Access all generated quick-convert remix videos and download them at any time."
      >
        {loading && <p className="text-sm text-slate-500">Loading downloads...</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {!loading && !error && items.length === 0 && (
          <p className="text-sm text-slate-600">No remixed videos available yet. Run Quick Convert to generate one.</p>
        )}

        {!loading && !error && items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2">Video Title</th>
                  <th className="px-3 py-2">Remix Details</th>
                  <th className="px-3 py-2">Created</th>
                  <th className="px-3 py-2">Download</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.project_id} className="border-t border-slate-100">
                    <td className="px-3 py-2 text-slate-700">
                      <Link to={ROUTES.projectDetails(item.project_id)} className="font-medium text-brand-700 hover:underline">
                        {item.video_title}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-slate-700">{item.remix_details}</td>
                    <td className="px-3 py-2 text-slate-700">{formatDate(item.created_at)}</td>
                    <td className="px-3 py-2">
                      <a
                        href={resolveDownloadUrl(item.download_url)}
                        className="inline-block rounded-md bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white"
                      >
                        Download
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </PageCard>
    </div>
  );
}
