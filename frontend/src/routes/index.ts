export const ROUTES = {
  dashboard: "/",
  createProject: "/projects/new",
  quickConvert: "/projects/quick-convert",
  youtubeDownload: "/projects/youtube-download",
  downloads: "/projects/downloads",
  projectDetails: (projectId: number) => `/projects/${projectId}`,
};
