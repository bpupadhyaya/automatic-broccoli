from __future__ import annotations


def build_export_variants(project_id: int, timeline: dict, formats: list[str]) -> list[dict]:
    duration = int(round(timeline.get("duration_sec", 0)))
    variants = []
    for export_format in formats:
        output_url = f"s3://mock/remix/projects/{project_id}/exports/{export_format}.mp4"
        variant_duration = duration
        if export_format == "teaser_trailer":
            variant_duration = min(30, duration)
        if export_format == "thumbnail_stills":
            output_url = f"s3://mock/remix/projects/{project_id}/exports/{export_format}.zip"
            variant_duration = 0

        variants.append(
            {
                "format": export_format,
                "output_url": output_url,
                "duration_sec": variant_duration,
            }
        )

    return variants
