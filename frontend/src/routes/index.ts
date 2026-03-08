export const ROUTES = {
  dashboard: "/",
  createProject: "/projects/new",
  quickConvert: "/projects/quick-convert",
  downloads: "/projects/downloads",
  projectDetails: (projectId: number) => `/projects/${projectId}`,
};
