#!/usr/bin/env python3
"""Check review completeness and hash binding; cannot verify the truth of visual judgments."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from check_pano import VIEWS, FLOOR_VIEWS, REVIEW_VERSION, VISUAL_CHECKS, read_rgb


def verify(candidate: Path, review_path: Path) -> list[str]:
    _, info = read_rgb(candidate)
    review = json.loads(review_path.read_text())
    errors = []
    if review.get("review_version") != REVIEW_VERSION:
        errors.append("Review schema is stale; regenerate all checks including floor views.")
    if info["format"] != "PNG" or info["width"] != 2*info["height"] or info["transparent_pixel_count"]:
        errors.append("Candidate must be an opaque, exact 2:1 PNG.")
    if review.get("candidate_sha256") != info["sha256"]:
        errors.append("Review does not match the delivered file's SHA-256.")
    if review.get("status") != "passed":
        errors.append("Visual review has not passed.")
    if not review.get("reviewer"):
        errors.append("Reviewer is missing.")
    required = {name for name, _, _ in VIEWS}
    if not required.issubset(set(review.get("reviewed_views", []))):
        errors.append("Not all required views have been reviewed.")
    for key in VISUAL_CHECKS:
        entry = review.get("checks", {}).get(key, {})
        if entry.get("status") != "pass" or not str(entry.get("evidence", "")).strip():
            errors.append(f"Missing passing evidence for: {key}.")
        views = entry.get("views", [])
        if not views or not set(views).issubset(required):
            errors.append(f"Missing/invalid evidence views for: {key}.")
    surface = review.get("checks", {}).get("surface_pattern", {})
    surface_views = set(surface.get("views", []))
    if "nadir" not in surface_views or not ({v[0] for v in FLOOR_VIEWS} & surface_views):
        errors.append("Surface-pattern evidence must include nadir and at least one oblique floor view.")
    for defect in review.get("defects", []):
        if defect.get("severity") in ("critical", "major") and defect.get("status") != "resolved":
            errors.append("Unresolved critical or major defect remains.")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("review", type=Path)
    args = parser.parse_args()
    try:
        errors = verify(args.candidate, args.review)
        print(json.dumps({"review_record_complete_and_current": not errors,
                          "errors": errors,
                          "limitation": "This checks records, not the truth of visual judgments."}, indent=2))
        return 2 if errors else 0
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"verify_review: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
