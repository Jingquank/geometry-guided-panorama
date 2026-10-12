#!/usr/bin/env python3
"""Generate fixed-center perspective QA views. Never automatically approve visual quality."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

VIEWS = [
    ("front", 0.0, 0.0), ("front-right", 45.0, 0.0),
    ("right", 90.0, 0.0), ("back-right", 135.0, 0.0),
    ("back-seam", 180.0, 0.0), ("back-left", -135.0, 0.0),
    ("left", -90.0, 0.0), ("front-left", -45.0, 0.0),
    ("zenith", 0.0, 90.0), ("nadir", 0.0, -90.0),
]
# Deliberate extra overlap below the horizon: floor drift can hide in level views.
FLOOR_VIEWS = [("floor-" + name, yaw, -45.0) for name, yaw, _ in VIEWS[:8]]
VIEWS += FLOOR_VIEWS
REVIEW_VERSION = "2-floor-topology"
VISUAL_CHECKS = ("geometry", "surface_pattern", "inventory", "coverage", "seam", "poles", "reference_fidelity")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rays(size: int, yaw_deg: float, pitch_deg: float, fov_deg: float = 90) -> np.ndarray:
    if not 1 <= size <= 4096 or not 0 < fov_deg < 180:
        raise ValueError("Invalid perspective size or field of view")
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    forward = np.array([math.sin(yaw)*math.cos(pitch),
                        math.cos(yaw)*math.cos(pitch), math.sin(pitch)])
    right = np.array([math.cos(yaw), -math.sin(yaw), 0.0])
    up = np.cross(right, forward)
    xy = (2 * (np.arange(size, dtype=np.float64) + 0.5) / size - 1) * math.tan(math.radians(fov_deg)/2)
    result = forward + xy[None, :, None] * right - xy[:, None, None] * up
    return result / np.linalg.norm(result, axis=-1, keepdims=True)


def sample_equirectangular(image: np.ndarray, directions: np.ndarray) -> np.ndarray:
    """Bilinear sampling with periodic longitude; source pixels represent pixel centers."""
    height, width = image.shape[:2]
    yaw = np.arctan2(directions[..., 0], directions[..., 1])
    pitch = np.arcsin(np.clip(directions[..., 2], -1, 1))
    x = (yaw / (2 * np.pi) + 0.5) * width - 0.5
    y = np.clip((0.5 - pitch / np.pi) * height - 0.5, 0, height - 1)
    x0_unwrapped = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx, fy = (x - x0_unwrapped)[..., None], (y - y0)[..., None]
    x0, x1 = x0_unwrapped % width, (x0_unwrapped + 1) % width
    y1 = np.minimum(y0 + 1, height - 1)
    return ((1-fy) * ((1-fx)*image[y0, x0] + fx*image[y0, x1]) +
            fy * ((1-fx)*image[y1, x0] + fx*image[y1, x1]))


def perspective(image: np.ndarray, size: int, yaw: float, pitch: float) -> Image.Image:
    data = sample_equirectangular(image, rays(size, yaw, pitch))
    return Image.fromarray(np.clip(np.rint(data), 0, 255).astype(np.uint8))


def read_rgb(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    with Image.open(path) as im:
        im.load()
        rgba = np.asarray(im.convert("RGBA"))
        info = {"path": str(path.resolve()), "sha256": digest(path),
                "format": im.format, "mode": im.mode, "width": im.width, "height": im.height,
                "transparent_pixel_count": int(np.count_nonzero(rgba[..., 3] != 255)),
                "icc_profile_present": bool(im.info.get("icc_profile"))}
        return np.asarray(im.convert("RGB"), dtype=np.float32), info


def seam_diagnostics(image: np.ndarray) -> dict[str, Any]:
    height, width = image.shape[:2]
    row_weight = np.cos(np.pi * (0.5 - (np.arange(height) + 0.5) / height))
    edge = np.mean(np.abs(image[:, 0] - image[:, -1]), axis=1)
    n = min(16, width // 4)
    nearby = np.concatenate([np.abs(image[:, 1:n+1] - image[:, :n]),
                             np.abs(image[:, -n:] - image[:, -n-1:-1])], axis=1)
    baseline = float(np.average(np.mean(nearby, axis=(1, 2)), weights=row_weight))
    error = float(np.average(edge, weights=row_weight))
    return {"spherical_weighted_boundary_mae_8bit": error,
            "spherical_weighted_nearby_mae_8bit": baseline,
            "boundary_to_nearby_ratio": None if baseline < 1e-8 else error / baseline,
            "boundary_row_mae_p95_8bit": float(np.percentile(edge, 95)),
            "interpretation": "Diagnostic only. Adjacent boundary pixels need not match. No visual pass/fail threshold."}


def initialize_review(output: Path, source: dict[str, Any], automated: dict[str, Any]) -> None:
    path = output / "visual-review.json"
    if path.exists():
        try:
            old = json.loads(path.read_text())
            if (old.get("candidate_sha256") == source["sha256"] and
                    old.get("review_version") == REVIEW_VERSION):
                return
            suffix = str(old.get("candidate_sha256", "unknown"))[:12]
        except (ValueError, OSError):
            suffix = "invalid"
        path.replace(output / f"visual-review.stale-{suffix}.json")
    review = {
        "candidate_path": source["path"], "candidate_sha256": source["sha256"],
        "review_version": REVIEW_VERSION,
        "status": "not_reviewed", "reviewer": None,
        "required_views": [name for name, _, _ in VIEWS], "reviewed_views": [],
        "automated_file_checks": automated,
        "checks": {key: {"status": "not_reviewed", "evidence": "", "views": []}
                   for key in VISUAL_CHECKS},
        "defects": [], "assumptions": [],
        "scope": "Fixed-center visual inspection only; no 3D reconstruction or free-translation validation."
    }
    path.write_text(json.dumps(review, indent=2) + "\n")


def check(path: Path, output: Path, size: int = 512, guide: Path | None = None) -> dict[str, Any]:
    image, source = read_rgb(path)
    output.mkdir(parents=True, exist_ok=True)
    automated = {"decoded": True, "png": source["format"] == "PNG",
                 "exact_2_to_1": source["width"] == 2 * source["height"],
                 "opaque": source["transparent_pixel_count"] == 0}
    result: dict[str, Any] = {"source": source, "automated_file_checks": automated,
                             "assumes_projection": "equirectangular; aspect ratio alone does not prove this",
                             "visual_quality_status": "not_reviewed",
                             "views": []}
    if automated["exact_2_to_1"]:
        result["seam_diagnostics"] = seam_diagnostics(image)
        thumb, header = 256, 25
        sheet = Image.new("RGB", (5*thumb, math.ceil(len(VIEWS)/5)*(thumb+header)), "#202020")
        draw = ImageDraw.Draw(sheet)
        guide_image = None
        if guide is not None:
            guide_image, guide_info = read_rgb(guide)
            if guide_info["width"] != 2 * guide_info["height"]:
                raise ValueError("Comparison guide must have a 2:1 aspect ratio")
            result["comparison_guide"] = guide_info
        for i, (name, yaw, pitch) in enumerate(VIEWS):
            view = perspective(image, size, yaw, pitch)
            view.save(output / f"{name}.png")
            result["views"].append({"name": name, "yaw_degrees": yaw, "pitch_degrees": pitch,
                                    "horizontal_fov_degrees": 90, "vertical_fov_degrees": 90,
                                    "path": str(output / f"{name}.png")})
            x, y = (i % 5)*thumb, (i // 5)*(thumb+header)
            draw.text((x+8, y+5), name, fill="white")
            sheet.paste(view.resize((thumb, thumb), Image.Resampling.LANCZOS), (x, y+header))
            if guide_image is not None:
                paired = Image.new("RGB", (size*2, size+header))
                pd = ImageDraw.Draw(paired)
                pd.text((8, 5), f"Guide: {name}", fill="white")
                pd.text((size+8, 5), f"Candidate: {name}", fill="white")
                paired.paste(perspective(guide_image, size, yaw, pitch), (0, header))
                paired.paste(view, (size, header))
                paired.save(output / f"compare-{name}.png")
        sheet.save(output / "perspective-checks.jpg", quality=92, subsampling=0)
        floor_sheet = Image.new("RGB", (3*thumb, 3*(thumb+header)), "#202020")
        floor_draw = ImageDraw.Draw(floor_sheet)
        for i, (name, _, _) in enumerate([VIEWS[9], *FLOOR_VIEWS]):
            x, y = (i % 3)*thumb, (i // 3)*(thumb+header)
            floor_draw.text((x+8, y+5), name, fill="white")
            with Image.open(output / f"{name}.png") as view:
                floor_sheet.paste(view.resize((thumb, thumb), Image.Resampling.LANCZOS), (x, y+header))
        floor_sheet.save(output / "floor-checks.jpg", quality=92, subsampling=0)
        band = max(1, source["width"]//16)
        strip = np.concatenate([image[:, -band:], image[:, :band]], axis=1)
        Image.fromarray(strip.astype(np.uint8)).save(output / "seam-strip.png")
    else:
        result["error"] = "Wrong aspect ratio. No projection images generated; do not stretch/crop to conceal it."
    (output / "diagnostics.json").write_text(json.dumps(result, indent=2) + "\n")
    initialize_review(output, source, automated)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--view-size", type=int, default=512)
    parser.add_argument("--guide", type=Path)
    args = parser.parse_args()
    if not 32 <= args.view_size <= 2048:
        parser.error("view-size must be between 32 and 2048")
    try:
        result = check(args.image.resolve(), args.output_dir.resolve(), args.view_size, args.guide)
        print(json.dumps({"automated_file_checks": result["automated_file_checks"],
                          "visual_quality_status": "not_reviewed",
                          "output_dir": str(args.output_dir.resolve())}, indent=2))
        return 0 if all(result["automated_file_checks"].values()) else 2
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        print(f"check_pano: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
