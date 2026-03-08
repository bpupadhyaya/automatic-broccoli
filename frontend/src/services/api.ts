import type { ManifestResponse, ProjectCreateInput, ProjectDetail, ProjectPlan, ProjectSummary } from "../types/project";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorPayload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(errorPayload.detail ?? `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export function listProjects(): Promise<ProjectSummary[]> {
  return request<ProjectSummary[]>("/projects");
}

export function createProject(payload: ProjectCreateInput): Promise<ProjectDetail> {
  return request<ProjectDetail>("/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getProject(projectId: number): Promise<ProjectDetail> {
  return request<ProjectDetail>(`/projects/${projectId}`);
}

export function generateProjectPlan(projectId: number): Promise<ProjectPlan> {
  return request<ProjectPlan>(`/projects/${projectId}/generate-plan`, {
    method: "POST",
  });
}

export function getManifest(projectId: number): Promise<ManifestResponse> {
  return request<ManifestResponse>(`/projects/${projectId}/manifest`);
}
