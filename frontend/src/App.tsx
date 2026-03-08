import { Link, Route, Routes, useLocation } from "react-router-dom";

import DashboardPage from "./pages/DashboardPage";
import CreateProjectPage from "./pages/CreateProjectPage";
import ProjectDetailsPage from "./pages/ProjectDetailsPage";
import QuickConvertPage from "./pages/QuickConvertPage";
import DownloadsPage from "./pages/DownloadsPage";
import { ROUTES } from "./routes";

export default function App() {
  const location = useLocation();
  const isDashboardRoute = location.pathname === ROUTES.dashboard;

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-lg font-bold text-brand-700">
            AI YouTube Remix Generator
          </Link>
          <div className="flex items-center gap-3 text-sm font-medium">
            {isDashboardRoute ? (
              <>
                <Link
                  to={ROUTES.quickConvert}
                  className="rounded-md border border-brand-300 px-3 py-2 text-brand-700 hover:bg-brand-50"
                >
                  Quick Convert
                </Link>
                <Link to={ROUTES.downloads} className="rounded-md border border-slate-300 px-3 py-2 text-slate-700 hover:bg-slate-100">
                  Downloads
                </Link>
                <Link to={ROUTES.createProject} className="rounded-md bg-brand-500 px-3 py-2 text-white hover:bg-brand-700">
                  Create Project
                </Link>
              </>
            ) : (
              <Link to={ROUTES.dashboard} className="rounded-md border border-slate-300 px-3 py-2 text-slate-700 hover:bg-slate-100">
                Dashboard
              </Link>
            )}
          </div>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-7xl px-6 py-8">
        <Routes>
          <Route path={ROUTES.dashboard} element={<DashboardPage />} />
          <Route path={ROUTES.quickConvert} element={<QuickConvertPage />} />
          <Route path={ROUTES.downloads} element={<DownloadsPage />} />
          <Route path={ROUTES.createProject} element={<CreateProjectPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailsPage />} />
        </Routes>
      </main>
    </div>
  );
}
