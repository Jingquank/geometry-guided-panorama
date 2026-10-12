#!/usr/bin/env python3
"""Validate final artifact records and, for patterns, recompute the last surface finish.

Run this through the delivery path. It cannot stop an assistant invoking an
unrelated image tool directly, authenticate reviews, or prove 3D correctness.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from check_pano import digest
from verify_review import verify
from execution_guard import read_object, resolve_artifact, preflight, patterned_ids, report_for
from surface_finish import verify_finish


def verify_pipeline(pipeline_path: Path) -> list[str]:
    data = read_object(pipeline_path)
    root = pipeline_path.resolve().parent
    errors = preflight(pipeline_path)
    def artifact(key):
        try:
            return resolve_artifact(root, data, key)
        except (OSError, ValueError, TypeError) as exc:
            errors.append(str(exc))
            return None
    if data.get("status") != "ready_for_review":
        errors.append("Pipeline must be ready_for_review, not blocked/unverified")
    candidate = artifact("candidate")
    review = artifact("candidate_review")
    spec_path = artifact("scene_spec")
    request_path = artifact("generation_request")
    preflight_path = artifact("preflight_report")
    if candidate and review:
        errors.extend("Final: " + e for e in verify(candidate, review))
    if preflight_path:
        old = read_object(preflight_path)
        current = report_for(pipeline_path)
        if old.get("status") != "ready":
            errors.append("Preflight did not pass")
        for key in ("preflight_version", "scene_spec", "structural_base", "capabilities", "planned_final_operation"):
            if old.get(key) != current.get(key):
                errors.append(f"Preflight is stale for: {key}")
    spec = read_object(spec_path) if spec_path else {}
    if spec.get("route") == "direct_simple":
        if spec.get("scene_type") not in ("sky", "distant_landscape"):
            errors.append("Direct generation is restricted to sky/distant landscape")
    if request_path:
        request = read_object(request_path)
        mode = request.get("mode", "image_generation")
        if mode == "render_existing_materials":
            if not request.get("actual_render_inputs"):
                errors.append("Renderer-only route must retain actual_render_inputs instead of inventing a prompt")
        elif mode == "image_generation":
            if not request.get("authored_prompt"):
                errors.append("Authored generation request must be retained")
            if spec.get("route") in ("geometry_guided", "same_layout_edit"):
                base = artifact("structural_base")
                if base and request.get("structural_base_sha256") != digest(base):
                    errors.append("Generation request does not identify the reviewed structural base")
                if not request.get("actual_input_references"):
                    errors.append("Generation request is missing actual input references")
        else:
            errors.append("Unsupported generation request mode")
    if spec_path and spec.get("route") in ("geometry_guided", "same_layout_edit"):
        try:
            protected = patterned_ids(spec)
            if protected:
                finish = artifact("surface_finish")
                if finish and candidate:
                    if read_object(finish).get("mode") != data.get("planned_final_operation"):
                        errors.append("Surface finish mode does not match the preflight plan")
                    errors.extend("Surface finish: " + e for e in verify_finish(finish, candidate, spec_path))
        except (OSError, ValueError, TypeError) as exc:
            errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pipeline", type=Path)
    args = parser.parse_args()
    try:
        errors = verify_pipeline(args.pipeline)
        print(json.dumps({"release_record_complete": not errors, "errors": errors,
                          "scope": "Local records and exact surface-composite bytes, not visual truth or 3D quality."}, indent=2))
        return 2 if errors else 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(f"release_check: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
