#!/usr/bin/env python3
"""Pre-generation checks for the local workflow. Does not intercept external tools."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from check_pano import digest
from verify_review import verify
from inspection_plan import validate_plan

VERSION = 3
NONPATTERNS = {"none", "unpatterned", "irregular_natural", "solid"}


def read_object(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


def resolve_artifact(root: Path, record: dict, key: str) -> Path:
    item = record.get(key)
    if not isinstance(item, dict) or not isinstance(item.get("path"), str):
        raise ValueError(f"Missing hash-bound artifact: {key}")
    path = Path(item["path"])
    path = path if path.is_absolute() else root / path
    path = path.resolve()
    if not path.is_file() or digest(path) != item.get("sha256"):
        raise ValueError(f"Missing or changed artifact: {key}")
    return path


def binding(path: Path) -> dict:
    return {"path": str(path.resolve()), "sha256": digest(path)}


def patterned_ids(spec: dict) -> set[str]:
    items = spec.get("surface_constraints")
    if not isinstance(items, list) or not items:
        raise ValueError("surface_constraints must be a nonempty structured list; record 'none' explicitly")
    seen, protected = set(), set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each surface constraint must be an object")
        key, pattern = item.get("id"), item.get("pattern")
        if not isinstance(key, str) or not key.strip() or key in seen:
            raise ValueError("Surface IDs must be nonempty and unique")
        if not isinstance(pattern, str) or not pattern.strip():
            raise ValueError(f"Missing pattern assessment for {key}")
        seen.add(key)
        if pattern.lower() not in NONPATTERNS:
            protected.add(key)
    return protected


def preflight(pipeline_path: Path) -> list[str]:
    data = read_object(pipeline_path)
    root = pipeline_path.resolve().parent
    errors = []
    if data.get("pipeline_version") != VERSION:
        errors.append("Missing/current pipeline_version must be 3")
    capabilities = data.get("capabilities", {})
    if not isinstance(capabilities, dict):
        capabilities = {}
    for key in ("local_processing", "output_bytes_accessible", "post_generation_processing"):
        if capabilities.get(key) is not True:
            errors.append(f"Cannot verify this route: capability {key} is not confirmed")
    try:
        spec = read_object(resolve_artifact(root, data, "scene_spec"))
        validate_plan(spec)
        route = spec.get("route")
        if route == "direct_simple":
            if (spec.get("scene_type") not in ("sky", "distant_landscape") or
                    spec.get("acceptance", {}).get("structure_sensitive") is not False):
                errors.append("Direct generation is not allowed for a structural scene")
            if spec.get("surface_constraints") and patterned_ids(spec):
                errors.append("Direct generation is not allowed for regular surface patterns")
        elif route in ("geometry_guided", "same_layout_edit"):
            base = resolve_artifact(root, data, "structural_base")
            review = resolve_artifact(root, data, "structural_base_review")
            errors.extend("Structural base: " + e for e in verify(base, review, resolve_artifact(root, data, "scene_spec")))
            if route == "geometry_guided":
                resolve_artifact(root, data, "scene_source")
            protected = patterned_ids(spec)
            for item in spec["surface_constraints"]:
                if item["id"] in protected and item.get("finish_route") not in (
                        "world_space_surface", "deterministic_render"):
                    errors.append(f"{item['id']}: deterministic final surface finish is required, not preferred")
            if protected and data.get("planned_final_operation") not in (
                    "masked_surface_finish", "rendered_panorama"):
                errors.append("Patterned scene must end with deterministic rendering/compositing, not image generation")
        else:
            errors.append("Unknown scene route")
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        errors.append(str(exc))
    return errors


def report_for(path: Path) -> dict:
    data = read_object(path)
    errors = preflight(path)
    return {"preflight_version": VERSION, "status": "blocked" if errors else "ready",
            "errors": errors, "scene_spec": data.get("scene_spec"),
            "structural_base": data.get("structural_base"),
            "capabilities": data.get("capabilities"),
            "planned_final_operation": data.get("planned_final_operation"),
            "scope": "Local artifacts and declared capabilities only; not proof of external tool invocation or visual truth."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pipeline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.pipeline.resolve() == args.output.resolve():
            raise ValueError("Report must not overwrite pipeline state")
        report = report_for(args.pipeline)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return 0 if report["status"] == "ready" else 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(f"execution_guard: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
