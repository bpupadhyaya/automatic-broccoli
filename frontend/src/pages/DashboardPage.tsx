import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import PageCard from "../components/PageCard";
import { ROUTES } from "../routes";
import { listProjects } from "../services/api";
import type { ProjectSummary } from "../types/project";
import { formatDate } from "../lib/utils";

export default function DashboardPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then((items) => setProjects(items))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <PageCard
        title="Dashboard"
        subtitle="Manage remix planning projects and inspect generated storyboard assets."
      >
        <p className="text-sm text-slate-600">Projects are generated from three YouTube references.</p>
      </PageCard>

      <PageCard title="All Projects">
        {loading && <p className="text-sm text-slate-500">Loading projects...</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}

        {!loading && !error && projects.length === 0 && (
          <p className="text-sm text-slate-600">No projects yet. Create one to start generating a remix plan.</p>
        )}

        {!loading && !error && projects.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Target Video URL</th>
                  <th className="px-3 py-2">Genre</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((project) => (
                  <tr key={project.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 font-medium text-slate-700">
                      <Link to={ROUTES.projectDetails(project.id)} className="text-brand-700 hover:underline">
                        #{project.id}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-slate-700">
                      <a
                        href={project.target_original_video_url}
                        target="_blank"
                        rel="noreferrer"
                        className="break-all text-brand-700 hover:underline"
                      >
                        {project.target_original_video_url}
                      </a>
                    </td>
                    <td className="px-3 py-2 text-slate-700">{project.remix_genre}</td>
                    <td className="px-3 py-2 text-slate-700">{project.status}</td>
                    <td className="px-3 py-2 text-slate-700">{formatDate(project.created_at)}</td>
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
