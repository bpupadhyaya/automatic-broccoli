import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import PageCard from "../components/PageCard";
import {
  applyCharacterToShots,
  generateCharacters,
  generateProjectPlan,
  getManifest,
  getProject,
  listCharacters,
  lockCharacter,
  regenerateCharacterAssets,
} from "../services/api";
import type { CharacterSummary, ProjectDetail } from "../types/project";
import { useProjectTabs, type ProjectTab } from "../hooks/useProjectTabs";

function TabButton({
  current,
  label,
  isActive,
  onClick,
}: {
  current: ProjectTab;
  label: string;
  isActive: boolean;
  onClick: (tab: ProjectTab) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onClick(current)}
      className={`rounded-md px-3 py-2 text-sm font-medium ${
        isActive ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-700"
      }`}
    >
      {label}
    </button>
  );
}

export default function ProjectDetailsPage() {
  const { projectId } = useParams();
  const parsedProjectId = Number(projectId);

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manifestError, setManifestError] = useState<string | null>(null);
  const [characters, setCharacters] = useState<CharacterSummary[]>([]);
  const [characterLoading, setCharacterLoading] = useState(false);
  const [characterActionRunning, setCharacterActionRunning] = useState(false);
  const [characterError, setCharacterError] = useState<string | null>(null);
  const [characterNotice, setCharacterNotice] = useState<string | null>(null);
  const [selectedCharacterId, setSelectedCharacterId] = useState<number | null>(null);
  const { activeTab, setActiveTab, tabs } = useProjectTabs();

  const fetchProject = async () => {
    setLoading(true);
    setError(null);

    try {
      const item = await getProject(parsedProjectId);
      setProject(item);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project");
    } finally {
      setLoading(false);
    }
  };

  const fetchCharacters = async () => {
    setCharacterLoading(true);
    setCharacterError(null);
    try {
      const response = await listCharacters(parsedProjectId);
      setCharacters(response.characters);
      const locked = response.characters.find((item) => item.is_locked);
      if (locked) {
        setSelectedCharacterId((prev) => prev ?? locked.id);
      }
    } catch (err) {
      setCharacterError(err instanceof Error ? err.message : "Failed to load characters");
    } finally {
      setCharacterLoading(false);
    }
  };

  useEffect(() => {
    if (!Number.isFinite(parsedProjectId) || parsedProjectId <= 0) {
      setError("Invalid project id");
      setLoading(false);
      return;
    }
    void fetchProject();
    void fetchCharacters();
  }, [parsedProjectId]);

  const runGeneratePlan = async () => {
    setRunning(true);
    setError(null);
    try {
      await generateProjectPlan(parsedProjectId);
      await fetchProject();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate plan");
    } finally {
      setRunning(false);
    }
  };

  const runGenerateCharacters = async () => {
    setCharacterActionRunning(true);
    setCharacterError(null);
    setCharacterNotice(null);
    try {
      await generateCharacters(parsedProjectId, 3);
      await fetchCharacters();
      setCharacterNotice("Generated 3 character candidates.");
    } catch (err) {
      setCharacterError(err instanceof Error ? err.message : "Failed to generate characters");
    } finally {
      setCharacterActionRunning(false);
    }
  };

  const runLockCharacter = async (characterId: number) => {
    setCharacterActionRunning(true);
    setCharacterError(null);
    setCharacterNotice(null);
    try {
      await lockCharacter(characterId);
      setSelectedCharacterId(characterId);
      await fetchCharacters();
      setCharacterNotice(`Character ${characterId} locked.`);
    } catch (err) {
      setCharacterError(err instanceof Error ? err.message : "Failed to lock character");
    } finally {
      setCharacterActionRunning(false);
    }
  };

  const runRegenerateAssets = async (characterId: number) => {
    setCharacterActionRunning(true);
    setCharacterError(null);
    setCharacterNotice(null);
    try {
      await regenerateCharacterAssets(characterId);
      await fetchCharacters();
      setCharacterNotice(`Regenerated assets for character ${characterId}.`);
    } catch (err) {
      setCharacterError(err instanceof Error ? err.message : "Failed to regenerate assets");
    } finally {
      setCharacterActionRunning(false);
    }
  };

  const runApplyCharacter = async () => {
    const targetId = selectedCharacterId ?? characters.find((item) => item.is_locked)?.id;
    if (!targetId) {
      setCharacterError("Select or lock a character first.");
      return;
    }

    setCharacterActionRunning(true);
    setCharacterError(null);
    setCharacterNotice(null);
    try {
      const response = await applyCharacterToShots(parsedProjectId, targetId);
      setCharacterNotice(`Applied character ${targetId} to ${response.updated_shot_count} shots.`);
    } catch (err) {
      setCharacterError(err instanceof Error ? err.message : "Failed to apply character to shots");
    } finally {
      setCharacterActionRunning(false);
    }
  };

  const refreshManifest = async () => {
    setManifestError(null);
    try {
      const response = await getManifest(parsedProjectId);
      setProject((prev) => (prev ? { ...prev, manifest: response.manifest } : prev));
    } catch (err) {
      setManifestError(err instanceof Error ? err.message : "Failed to load manifest");
    }
  };

  const overview = useMemo(
    () =>
      project
        ? [
            ["Status", project.status],
            ["Remix Genre", project.remix_genre],
            ["Celebrity Mode", project.celebrity_mode],
            ["Visual Theme", project.visual_theme],
            ["Dance Style", project.dance_style],
            ["Transformation Summary", project.transformation_summary ?? "Not generated yet"],
          ]
        : [],
    [project]
  );

  if (loading) {
    return <p className="text-sm text-slate-600">Loading project...</p>;
  }

  if (error) {
    return <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>;
  }

  if (!project) {
    return <p className="text-sm text-slate-600">Project not found.</p>;
  }

  return (
    <div className="space-y-6">
      <PageCard title={`Project #${project.id}`} subtitle={project.target_original_video_url}>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={runGeneratePlan}
            disabled={running}
            className="rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-400"
          >
            {running ? "Generating..." : "Generate Plan"}
          </button>
          <button
            type="button"
            onClick={refreshManifest}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700"
          >
            Refresh Manifest
          </button>
          {manifestError && <span className="text-sm text-red-700">{manifestError}</span>}
        </div>
      </PageCard>

      <PageCard>
        <div className="mb-4 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <TabButton
              key={tab.key}
              current={tab.key}
              label={tab.label}
              isActive={activeTab === tab.key}
              onClick={setActiveTab}
            />
          ))}
        </div>

        {activeTab === "overview" && (
          <div className="space-y-2 text-sm text-slate-700">
            {overview.map(([label, value]) => (
              <div key={label} className="rounded-md bg-slate-50 p-2">
                <span className="font-semibold">{label}: </span>
                <span>{value}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === "character-studio" && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={runGenerateCharacters}
                disabled={characterActionRunning}
                className="rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:bg-slate-400"
              >
                {characterActionRunning ? "Working..." : "Generate Characters"}
              </button>
              <button
                type="button"
                onClick={runApplyCharacter}
                disabled={characterActionRunning}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 disabled:text-slate-400"
              >
                Apply To All Shots
              </button>
              {characterNotice && <span className="text-sm text-emerald-700">{characterNotice}</span>}
              {characterError && <span className="text-sm text-red-700">{characterError}</span>}
            </div>

            {characterLoading ? (
              <p className="text-sm text-slate-600">Loading characters...</p>
            ) : (
              <div className="space-y-2">
                {characters.map((character) => (
                  <div key={character.id} className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-semibold text-slate-900">
                          {character.name} ({character.role})
                        </p>
                        <p className="text-slate-700">{character.identity_summary ?? "No identity summary"}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => setSelectedCharacterId(character.id)}
                          className={`rounded-md px-3 py-1.5 text-xs font-semibold ${
                            selectedCharacterId === character.id ? "bg-slate-900 text-white" : "bg-slate-200 text-slate-800"
                          }`}
                        >
                          {selectedCharacterId === character.id ? "Selected" : "Select"}
                        </button>
                        <button
                          type="button"
                          onClick={() => runLockCharacter(character.id)}
                          className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white"
                        >
                          {character.is_locked ? "Locked" : "Lock Character"}
                        </button>
                        <button
                          type="button"
                          onClick={() => runRegenerateAssets(character.id)}
                          className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700"
                        >
                          Regenerate Assets
                        </button>
                      </div>
                    </div>
                    <p className="mt-2 text-xs text-slate-600">
                      refs: {character.reference_asset_urls.length} | locked: {String(character.is_locked)}
                    </p>
                  </div>
                ))}
                {characters.length === 0 && <p className="text-sm text-slate-600">No characters yet. Generate candidates first.</p>}
              </div>
            )}
          </div>
        )}

        {activeTab === "character-bible" && (
          <pre className="overflow-x-auto rounded-md bg-slate-900 p-4 text-xs text-slate-100">
            {JSON.stringify(project.character_bible, null, 2)}
          </pre>
        )}

        {activeTab === "storyboard" && (
          <pre className="overflow-x-auto rounded-md bg-slate-900 p-4 text-xs text-slate-100">
            {JSON.stringify(project.storyboard_scenes, null, 2)}
          </pre>
        )}

        {activeTab === "scene-prompts" && (
          <pre className="overflow-x-auto rounded-md bg-slate-900 p-4 text-xs text-slate-100">
            {JSON.stringify(project.scene_prompts, null, 2)}
          </pre>
        )}

        {activeTab === "manifest-json" && (
          <pre className="overflow-x-auto rounded-md bg-slate-900 p-4 text-xs text-slate-100">
            {JSON.stringify(project.manifest, null, 2)}
          </pre>
        )}
      </PageCard>
    </div>
  );
}
