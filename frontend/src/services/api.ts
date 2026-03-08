import type {
  ApplyCharacterToShotsResponse,
  CharacterGenerateResponse,
  CharacterListResponse,
  CharacterLockResponse,
  ManifestResponse,
  ProjectCreateInput,
  ProjectDetail,
  ProjectPlan,
  ProjectSummary,
  QuickConversionOutput,
  QuickProjectCreateInput,
} from "../types/project";

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

export function quickConvertProject(payload: QuickProjectCreateInput): Promise<ProjectDetail> {
  return request<ProjectDetail>("/projects/quick-convert", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getQuickConversionOutput(projectId: number): Promise<QuickConversionOutput> {
  return request<QuickConversionOutput>(`/projects/${projectId}/quick-convert/output`);
}

export function getQuickConversionDownloadUrl(projectId: number): string {
  return `${API_BASE_URL}/projects/${projectId}/quick-convert/download`;
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

export function generateCharacters(projectId: number, candidateCount = 3): Promise<CharacterGenerateResponse> {
  return request<CharacterGenerateResponse>(`/projects/${projectId}/characters/generate`, {
    method: "POST",
    body: JSON.stringify({ candidate_count: candidateCount }),
  });
}

export function listCharacters(projectId: number): Promise<CharacterListResponse> {
  return request<CharacterListResponse>(`/projects/${projectId}/characters`);
}

export function lockCharacter(characterId: number): Promise<CharacterLockResponse> {
  return request<CharacterLockResponse>(`/characters/${characterId}/lock`, {
    method: "POST",
  });
}

export function regenerateCharacterAssets(characterId: number): Promise<unknown> {
  return request<unknown>(`/characters/${characterId}/regenerate-assets`, {
    method: "POST",
  });
}

export function applyCharacterToShots(projectId: number, characterId: number): Promise<ApplyCharacterToShotsResponse> {
  return request<ApplyCharacterToShotsResponse>(`/projects/${projectId}/characters/apply-to-shots`, {
    method: "POST",
    body: JSON.stringify({ character_id: characterId }),
  });
}
