from app.models.project import Project
from app.services.project_generator import build_project_plan


def run_remix_planner(project: Project) -> dict:
    return build_project_plan(project)
