from __future__ import annotations


class ExporterService:
    """Build synthetic export artifact metadata for requested output formats."""

    def export_project(self, project_id: str, formats: list[str]) -> list[dict]:
        return _build_export_variants(project_id, formats, duration_sec=0)


def _build_export_variants(project_id: str, formats: list[str], duration_sec: int) -> list[dict]:
    variants = []
    for export_format in formats:
        output_url = f"s3://mock/remix/projects/{project_id}/exports/{export_format}.mp4"
        variant_duration = duration_sec
        if export_format == "teaser_15s":
            variant_duration = min(15, duration_sec)
        if export_format == "thumbnails":
            output_url = f"s3://mock/remix/projects/{project_id}/exports/{export_format}.zip"
            variant_duration = 0

        variants.append(
            {
                "format": export_format,
                "status": "processing",
                "output_url": output_url,
                "duration_sec": variant_duration,
            }
        )
    return variants


def build_export_variants(project_id: int, timeline: dict, formats: list[str]) -> list[dict]:
    duration = int(round(timeline.get("duration_sec", 0)))
    return _build_export_variants(str(project_id), formats, duration)
