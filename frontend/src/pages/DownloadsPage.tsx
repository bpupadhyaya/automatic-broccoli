import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import PageCard from "../components/PageCard";
import { formatDate } from "../lib/utils";
import { ROUTES } from "../routes";
import { deleteProject, listDownloadVideos, resolveDownloadUrl } from "../services/api";
import type { DownloadVideoItem } from "../types/project";

export default function DownloadsPage() {
  const [items, setItems] = useState<DownloadVideoItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingProjectId, setDeletingProjectId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    listDownloadVideos()
      .then((rows) => setItems(rows))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (projectId: number) => {
    setActionError(null);
    setDeletingProjectId(projectId);
    try {
      await deleteProject(projectId);
      setItems((current) => current.filter((item) => item.project_id !== projectId));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to delete project entry.");
    } finally {
      setDeletingProjectId(null);
    }
  };

  const latestProjectId = items.length > 0 ? items[0].project_id : null;

  return (
    <div className="space-y-6">
      <PageCard
        title="Downloads"
        subtitle="Access all generated quick-convert remix videos and download them at any time."
      >
        {loading && <p className="text-sm text-slate-500">Loading downloads...</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {actionError && <p className="text-sm text-red-600">{actionError}</p>}

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
                  <th className="px-3 py-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const isLatest = item.project_id === latestProjectId;
                  const isDeleting = deletingProjectId === item.project_id;
                  return (
                  <tr key={item.project_id} className="border-t border-slate-100">
                    <td className="px-3 py-2 text-slate-700">
                      <Link to={ROUTES.projectDetails(item.project_id)} className="font-medium text-brand-700 hover:underline">
                        {item.video_title}
                      </Link>
                      {isLatest && (
                        <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                          Latest
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-slate-700">{item.remix_details}</td>
                    <td className="px-3 py-2 text-slate-700">{formatDate(item.created_at)}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <a
                          href={resolveDownloadUrl(item.download_url)}
                          className="inline-block rounded-md bg-brand-500 px-3 py-1.5 text-xs font-semibold text-white"
                        >
                          Download
                        </a>
                        <button
                          type="button"
                          disabled={isLatest || isDeleting}
                          onClick={() => handleDelete(item.project_id)}
                          className="inline-block rounded-md bg-red-500 px-3 py-1.5 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
                          title={isLatest ? "Latest remix entry cannot be deleted." : "Delete this download entry."}
                        >
                          {isDeleting ? "Deleting..." : "Delete"}
                        </button>
                      </div>
                    </td>
                  </tr>
                )})}
              </tbody>
            </table>
          </div>
        )}
      </PageCard>
    </div>
  );
}
