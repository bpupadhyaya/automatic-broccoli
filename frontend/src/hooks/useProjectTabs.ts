import { useMemo, useState } from "react";

export type ProjectTab =
  | "overview"
  | "character-studio"
  | "character-bible"
  | "storyboard"
  | "scene-prompts"
  | "manifest-json";

export function useProjectTabs(defaultTab: ProjectTab = "overview") {
  const [activeTab, setActiveTab] = useState<ProjectTab>(defaultTab);

  const tabs = useMemo(
    () => [
      { key: "overview", label: "Overview" },
      { key: "character-studio", label: "Character Studio" },
      { key: "character-bible", label: "Character Bible" },
      { key: "storyboard", label: "Storyboard" },
      { key: "scene-prompts", label: "Scene Prompts" },
      { key: "manifest-json", label: "Manifest JSON" },
    ] as const,
    []
  );

  return { activeTab, setActiveTab, tabs };
}
