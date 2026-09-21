from __future__ import annotations

import argparse
import json
import statistics
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from effekseer_mcp.paths import ensure_workspace_path, resolve_workspace
from effekseer_mcp.sample_library import (
    SAMPLE_LIBRARY_DIR,
    SAMPLE_MANIFEST_NAME,
    SampleLibraryError,
)

SAMPLE_ANALYSIS_DIR = "outputs/sample_analysis"
SAMPLE_ANALYSIS_JSON = "sample_analysis.json"
SAMPLE_ANALYSIS_MARKDOWN = "sample_analysis.md"
PATH_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".tga",
    ".dds",
    ".bmp",
    ".gif",
    ".efkmodel",
    ".wav",
    ".ogg",
    ".mp3",
)
TEXTURE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".tga", ".dds", ".bmp", ".gif")
MODEL_EXTENSIONS = (".efkmodel",)
SOUND_EXTENSIONS = (".wav", ".ogg", ".mp3")


class SampleAnalyzerError(ValueError):
    """Raised when sample analysis input or output paths are invalid."""


def analyze_sample_effects(
    *,
    sample_id: str | None = None,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Analyze imported SampleEffects XML and write JSON/Markdown summaries."""
    workspace_path = resolve_workspace(workspace)
    manifest = _load_sample_manifest(workspace_path)
    templates = _filter_templates(manifest, sample_id)
    samples = []
    errors = []

    for template in templates:
        try:
            samples.append(_analyze_template(template, workspace_path))
        except Exception as exc:  # noqa: BLE001 - keep batch analysis moving.
            errors.append(
                {
                    "sample_id": template.get("sample_id"),
                    "workspace_project_path": template.get("workspace_project_path"),
                    "error": str(exc),
                }
            )

    categories = _aggregate_categories(samples)
    analysis = {
        "generated_at": datetime.now(UTC).isoformat(),
        "sample_count": len(samples),
        "error_count": len(errors),
        "samples": samples,
        "categories": categories,
        "texture_ranking": _counter_ranking(
            texture
            for sample in samples
            for texture in sample["color_texture_paths"]
        ),
        "renderer_type_ranking": _counter_ranking(
            renderer
            for sample in samples
            for renderer in sample["renderer_type_values"]
        ),
        "alpha_blend_ranking": _counter_ranking(
            alpha_blend
            for sample in samples
            for alpha_blend in sample["alpha_blend_values"]
        ),
        "errors": errors,
    }

    output_dir = ensure_workspace_path(SAMPLE_ANALYSIS_DIR, workspace_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / SAMPLE_ANALYSIS_JSON
    markdown_path = output_dir / SAMPLE_ANALYSIS_MARKDOWN
    json_path.write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_build_markdown(analysis), encoding="utf-8")

    return {
        "analysis_path": _relative_to_workspace(json_path, workspace_path),
        "summary_path": _relative_to_workspace(markdown_path, workspace_path),
        "summary": _summary_payload(analysis),
        "analysis": analysis,
    }


def get_sample_analysis_summary(
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Read the latest sample analysis summary from workspace outputs."""
    workspace_path = resolve_workspace(workspace)
    analysis_path = ensure_workspace_path(
        f"{SAMPLE_ANALYSIS_DIR}/{SAMPLE_ANALYSIS_JSON}",
        workspace_path,
    )
    if not analysis_path.is_file():
        raise SampleAnalyzerError("sample analysis has not been generated")
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    if not isinstance(analysis, dict):
        raise SampleAnalyzerError("sample analysis must be a JSON object")
    return _summary_payload(analysis)


def analyze_project_file(
    project_path: str,
    *,
    workspace: str | Path | None = None,
    sample_id: str = "sample",
    display_name: str = "Sample",
    category_hint: str = "misc",
) -> dict[str, Any]:
    """Analyze one workspace-relative SampleEffects .efkproj file."""
    workspace_path = resolve_workspace(workspace)
    safe_project_path = _resolve_sample_project_path(project_path, workspace_path)
    root = ET.parse(safe_project_path).getroot()
    values = _collect_xml_values(root)
    values.update(
        {
            "sample_id": sample_id,
            "display_name": display_name,
            "category_hint": category_hint,
            "workspace_project_path": project_path,
            "node_count": len(root.findall(".//Node")),
            "texture_usage_count": len(values["color_texture_paths"]),
        }
    )
    return values


def _load_sample_manifest(workspace: Path) -> dict[str, Any]:
    manifest_path = ensure_workspace_path(
        f"{SAMPLE_LIBRARY_DIR}/{SAMPLE_MANIFEST_NAME}",
        workspace,
    )
    if not manifest_path.is_file():
        raise SampleAnalyzerError("sample manifest was not found; import samples first")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SampleAnalyzerError("sample manifest must be a JSON object")
    return data


def _filter_templates(
    manifest: dict[str, Any],
    sample_id: str | None,
) -> list[dict[str, Any]]:
    templates = [
        template
        for template in manifest.get("templates", [])
        if isinstance(template, dict)
    ]
    if sample_id is None:
        return templates
    filtered = [template for template in templates if template.get("sample_id") == sample_id]
    if not filtered:
        raise SampleAnalyzerError(f"unknown sample template: {sample_id}")
    return filtered


def _analyze_template(template: dict[str, Any], workspace: Path) -> dict[str, Any]:
    project_path = template.get("workspace_project_path")
    if not isinstance(project_path, str):
        raise SampleLibraryError("template is missing workspace_project_path")
    return analyze_project_file(
        project_path,
        workspace=workspace,
        sample_id=str(template.get("sample_id", "")),
        display_name=str(template.get("display_name", "")),
        category_hint=str(template.get("category_hint", "misc")),
    )


def _resolve_sample_project_path(project_path: str, workspace: Path) -> Path:
    requested = Path(project_path)
    if requested.is_absolute() or ".." in requested.parts:
        raise SampleAnalyzerError("sample project path must be workspace-relative")
    if requested.suffix.lower() != ".efkproj":
        raise SampleAnalyzerError("sample project path must be .efkproj")
    if requested.parts[:2] != ("samples", "sample_effects"):
        raise SampleAnalyzerError("sample project path must be under samples/sample_effects")
    return ensure_workspace_path(requested, workspace)


def _collect_xml_values(root: ET.Element) -> dict[str, Any]:
    values = {
        "max_generation_values": [],
        "life_values": [],
        "generation_time_values": [],
        "generation_time_offset_values": [],
        "location_velocity_values": [],
        "rotation_velocity_values": [],
        "scale_values": [],
        "renderer_type_values": [],
        "alpha_blend_values": [],
        "color_texture_paths": [],
        "model_paths": [],
        "sound_paths": [],
        "fade_in_frames": [],
        "fade_out_frames": [],
    }

    for element, path in _walk(root):
        tag = _tag(element)
        path_tags = tuple(_tag(item) for item in path)
        if tag == "MaxGeneration":
            values["max_generation_values"].extend(_extract_numbers(element))
        elif tag == "Life":
            random_value = _extract_random_value(element)
            if random_value is not None:
                values["life_values"].append(random_value)
        elif tag == "GenerationTime":
            values["generation_time_values"].extend(_extract_numbers(element))
        elif tag == "GenerationTimeOffset":
            values["generation_time_offset_values"].extend(_extract_numbers(element))
        elif tag == "Velocity" and _has_ancestor(path_tags, "LocationValues"):
            values["location_velocity_values"].extend(_extract_numbers(element))
        elif tag == "Velocity" and _has_ancestor(path_tags, "RotationValues"):
            values["rotation_velocity_values"].extend(_extract_numbers(element))
        elif tag == "Scale" and _has_ancestor(path_tags, "ScalingValues"):
            values["scale_values"].extend(_extract_numbers(element))
        elif tag == "Type" and _has_ancestor(path_tags, "DrawingValues"):
            text = _clean_text(element)
            if text:
                values["renderer_type_values"].append(text)
        elif tag == "AlphaBlend":
            text = _clean_text(element)
            if text:
                values["alpha_blend_values"].append(text)
        elif tag == "ColorTexture":
            texture = _clean_path_text(element)
            if texture:
                values["color_texture_paths"].append(texture)
        elif tag == "Frame" and _has_ancestor(path_tags, "FadeIn"):
            values["fade_in_frames"].extend(_extract_numbers(element))
        elif tag == "Frame" and _has_ancestor(path_tags, "FadeOut"):
            values["fade_out_frames"].extend(_extract_numbers(element))

        path_text = _clean_path_text(element)
        if path_text:
            suffix = Path(path_text).suffix.lower()
            if suffix in MODEL_EXTENSIONS:
                values["model_paths"].append(path_text)
            elif suffix in SOUND_EXTENSIONS:
                values["sound_paths"].append(path_text)
            elif suffix in TEXTURE_EXTENSIONS and tag != "ColorTexture":
                values["color_texture_paths"].append(path_text)

    for key, value in values.items():
        if isinstance(value, list):
            values[key] = _dedupe_preserve_order(value)
    return values


def _walk(root: ET.Element) -> list[tuple[ET.Element, tuple[ET.Element, ...]]]:
    items: list[tuple[ET.Element, tuple[ET.Element, ...]]] = []

    def visit(element: ET.Element, parents: tuple[ET.Element, ...]) -> None:
        items.append((element, parents))
        next_parents = (*parents, element)
        for child in list(element):
            visit(child, next_parents)

    visit(root, ())
    return items


def _tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _has_ancestor(path_tags: Sequence[str], tag: str) -> bool:
    return tag in path_tags


def _clean_text(element: ET.Element) -> str:
    return (element.text or "").strip()


def _clean_path_text(element: ET.Element) -> str:
    text = _clean_text(element).replace("\\", "/")
    if not text or Path(text).is_absolute() or ".." in Path(text).parts:
        return ""
    if not text.lower().endswith(PATH_EXTENSIONS):
        return ""
    return text


def _extract_numbers(element: ET.Element) -> list[float]:
    numbers: list[float] = []
    direct_number = _parse_number(_clean_text(element))
    if direct_number is not None:
        numbers.append(direct_number)
    for child in element.iter():
        if child is element:
            continue
        number = _parse_number(_clean_text(child))
        if number is not None:
            numbers.append(number)
    return numbers


def _extract_random_value(element: ET.Element) -> dict[str, float] | None:
    payload = {
        key: _child_number(element, key)
        for key in ("Center", "Min", "Max")
    }
    if all(value is None for value in payload.values()):
        direct = _parse_number(_clean_text(element))
        if direct is None:
            return None
        return {"center": direct, "min": direct, "max": direct}
    center = payload["Center"]
    min_value = payload["Min"]
    max_value = payload["Max"]
    if center is None:
        center = min_value if min_value is not None else max_value
    if min_value is None:
        min_value = center
    if max_value is None:
        max_value = center
    if center is None or min_value is None or max_value is None:
        return None
    return {"center": center, "min": min_value, "max": max_value}


def _child_number(element: ET.Element, tag: str) -> float | None:
    child = element.find(tag)
    if child is None:
        return None
    return _parse_number(_clean_text(child))


def _parse_number(text: str) -> float | None:
    if text.lower() in {"true", "false", ""}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _dedupe_preserve_order(values: list[Any]) -> list[Any]:
    deduped: list[Any] = []
    seen = set()
    for value in values:
        key = json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
        if key not in seen:
            seen.add(key)
            deduped.append(value)
    return deduped


def _aggregate_categories(samples: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        grouped[str(sample.get("category_hint", "misc"))].append(sample)

    categories = {}
    for category, category_samples in grouped.items():
        life_centers = [
            life["center"]
            for sample in category_samples
            for life in sample["life_values"]
            if isinstance(life, dict)
        ]
        generation = [
            value
            for sample in category_samples
            for value in sample["max_generation_values"]
        ]
        velocity = [
            value
            for sample in category_samples
            for value in (
                sample["location_velocity_values"]
                + sample["rotation_velocity_values"]
            )
        ]
        scale = [
            value
            for sample in category_samples
            for value in sample["scale_values"]
        ]
        categories[category] = {
            "sample_count": len(category_samples),
            "life": _range_stats(life_centers),
            "generation": _range_stats(generation),
            "velocity": _range_stats(velocity),
            "scale": _range_stats(scale),
        }
    return categories


def _range_stats(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "max": None, "median": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "median": statistics.median(values),
    }


def _counter_ranking(values: Any) -> list[dict[str, Any]]:
    counter = Counter(str(value) for value in values if str(value))
    return [
        {"value": value, "count": count}
        for value, count in counter.most_common(20)
    ]


def _summary_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_count": analysis.get("sample_count", 0),
        "error_count": analysis.get("error_count", 0),
        "categories": analysis.get("categories", {}),
        "texture_ranking": analysis.get("texture_ranking", []),
        "renderer_type_ranking": analysis.get("renderer_type_ranking", []),
        "alpha_blend_ranking": analysis.get("alpha_blend_ranking", []),
        "errors": analysis.get("errors", []),
    }


def _build_markdown(analysis: dict[str, Any]) -> str:
    lines = [
        "# SampleEffects Analysis",
        "",
        f"- Samples analyzed: {analysis['sample_count']}",
        f"- Errors: {analysis['error_count']}",
        "",
        "## Categories",
        "",
    ]
    for category, stats in sorted(analysis["categories"].items()):
        lines.extend(
            [
                f"### {category}",
                "",
                f"- sample_count: {stats['sample_count']}",
                f"- life: {_format_stats(stats['life'])}",
                f"- generation: {_format_stats(stats['generation'])}",
                f"- velocity: {_format_stats(stats['velocity'])}",
                f"- scale: {_format_stats(stats['scale'])}",
                "",
            ]
        )
    lines.extend(_ranking_section("Texture Ranking", analysis["texture_ranking"]))
    lines.extend(_ranking_section("Renderer Type Ranking", analysis["renderer_type_ranking"]))
    lines.extend(_ranking_section("AlphaBlend Ranking", analysis["alpha_blend_ranking"]))
    if analysis["errors"]:
        lines.extend(["## Errors", ""])
        for error in analysis["errors"]:
            lines.append(f"- `{error.get('sample_id')}`: {error.get('error')}")
        lines.append("")
    return "\n".join(lines)


def _format_stats(stats: dict[str, Any]) -> str:
    if stats.get("count") == 0:
        return "n/a"
    return (
        f"count={stats['count']}, min={stats['min']}, "
        f"max={stats['max']}, median={stats['median']}"
    )


def _ranking_section(title: str, ranking: Sequence[dict[str, Any]]) -> list[str]:
    lines = [f"## {title}", ""]
    if not ranking:
        lines.extend(["- n/a", ""])
        return lines
    for item in ranking[:10]:
        lines.append(f"- `{item['value']}`: {item['count']}")
    lines.append("")
    return lines


def _relative_to_workspace(path: Path, workspace: Path) -> str:
    return path.resolve().relative_to(workspace.resolve()).as_posix()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze imported SampleEffects .efkproj files.")
    parser.add_argument("--sample-id", help="Analyze one imported sample id.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = analyze_sample_effects(sample_id=args.sample_id)
    except Exception as exc:
        print(f"Sample analysis failed: {exc}")
        return 1
    print(f"Wrote {result['analysis_path']}")
    print(f"Wrote {result['summary_path']}")
    return 0
