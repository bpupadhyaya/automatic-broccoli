export const ROUTES = {
  dashboard: "/",
  createProject: "/projects/new",
  quickConvert: "/projects/quick-convert",
  projectDetails: (projectId: number) => `/projects/${projectId}`,
};
