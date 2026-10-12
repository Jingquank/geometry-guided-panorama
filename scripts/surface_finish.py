#!/usr/bin/env python3
"""Compose a reviewed world-space surface last, then verify exact decoded pixels.

This is a compositor, NOT a renderer, segmentation model, topology classifier,
or proof that external render provenance/reviewer statements are truthful.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from check_pano import FLOOR_VIEWS, VIEWS, read_rgb, digest
from execution_guard import read_object, resolve_artifact, binding, patterned_ids


def image_pixels(path: Path) -> np.ndarray:
    rgb, info = read_rgb(path)
    if info["format"] != "PNG" or info["width"] != 2 * info["height"] or info["transparent_pixel_count"]:
        raise ValueError(f"Expected an opaque 2:1 PNG: {path}")
    return rgb.astype(np.uint8)


def review_common(review: dict) -> None:
    if (review.get("status") != "passed" or not str(review.get("reviewer", "")).strip()
            or not str(review.get("evidence", "")).strip()):
        raise ValueError("Require an actual passed review with reviewer and specific evidence")


def binary_dilate(a: np.ndarray) -> np.ndarray:
    # Longitude wraps; latitude does not.
    p = np.pad(a, ((1, 1), (0, 0)), mode="edge")
    out = np.zeros_like(a)
    for dy in range(3):
        for dx in (-1, 0, 1):
            out |= np.roll(p[dy:dy+a.shape[0]], dx, axis=1)
    return out


def validate_mask(mask: np.ndarray) -> None:
    if not np.any(mask == 255):
        raise ValueError("Mask needs a fully protected surface interior; empty/soft-only masks are invalid")
    middle = (mask > 0) & (mask < 255)
    if np.any(middle):
        near_out, near_in = mask == 0, mask == 255
        for _ in range(2):
            near_out, near_in = binary_dilate(near_out), binary_dilate(near_in)
        if np.any(middle & ~(near_out & near_in)):
            raise ValueError("Feathering must be within two pixels of both mask interior and exterior; do not blend two grids")


def compose(base: np.ndarray, surface: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if base.shape != surface.shape or mask.shape != base.shape[:2]:
        raise ValueError("Base, surface, and mask dimensions must match without resizing")
    validate_mask(mask)
    alpha = mask.astype(np.float64)[..., None] / 255
    def linear(rgb):
        x = rgb.astype(np.float64) / 255
        return np.where(x <= .04045, x / 12.92, ((x+.055)/1.055)**2.4)
    x = linear(base) * (1-alpha) + linear(surface) * alpha
    s = np.where(x <= .0031308, 12.92*x, 1.055*np.maximum(x, 0)**(1/2.4)-.055)
    out = np.clip(np.rint(s*255), 0, 255).astype(np.uint8)
    out[mask == 0] = base[mask == 0]
    out[mask == 255] = surface[mask == 255]
    return out


def expected(request_path: Path) -> tuple[np.ndarray, dict, list[Path]]:
    req = read_object(request_path)
    if req.get("finish_request_version") != 1:
        raise ValueError("finish_request_version must be 1")
    root = request_path.resolve().parent
    paths = []
    def get(key):
        path = resolve_artifact(root, req, key)
        paths.append(path)
        return path
    spec_path, surface_path, srp = get("scene_spec"), get("surface_render"), get("surface_review")
    spec, sr = read_object(spec_path), read_object(srp)
    protected = patterned_ids(spec)
    if not protected:
        raise ValueError("Surface finalizer is for explicitly patterned surfaces")
    review_common(sr)
    for field, value in (("scene_spec_sha256", digest(spec_path)),
                         ("surface_render_sha256", digest(surface_path))):
        if sr.get(field) != value:
            raise ValueError(f"Surface review has missing or stale {field}")
    if not protected.issubset(set(sr.get("protected_surface_ids", []))):
        raise ValueError("Surface review does not cover every patterned surface")
    for flag in ("camera_and_projection_matched", "material_and_pattern_checked"):
        if sr.get(flag) is not True:
            raise ValueError(f"Surface review missing {flag}")
    if sr.get("render_role") != "final_world_space_surface":
        raise ValueError("Guide/calibration/unconstrained AI output is not a final rendered surface")
    rp = get("render_provenance")
    provenance = read_object(rp)
    if (provenance.get("output_sha256") != digest(surface_path)
            or provenance.get("scene_spec_sha256") != digest(spec_path)
            or provenance.get("mapping") != "world_space"
            or not provenance.get("renderer") or not provenance.get("render_settings")):
        raise ValueError("World-space render provenance is missing or not bound to the current surface/spec")
    needed = set()
    for item in spec["surface_constraints"]:
        if item["id"] not in protected:
            continue
        if (item.get("role") in ("floor", "ground") or item["id"] in ("floor", "ground")
                or item.get("geometry") in ("floor_plane", "ground_mesh")):
            needed |= {"nadir", *[v[0] for v in FLOOR_VIEWS]}
        else:
            views = item.get("required_views", [])
            if not isinstance(views, list) or not views:
                raise ValueError("Non-floor protected surfaces need explicit required_views")
            needed.update(views)
    if not needed.issubset(set(sr.get("reviewed_views", []))):
        raise ValueError("Surface review is missing required views (floor: nadir plus all eight oblique views)")
    surface = image_pixels(surface_path)
    mode = req.get("mode")
    if mode == "rendered_panorama":
        return surface, {"mode": mode, "protected_surface_ids": sorted(protected)}, paths
    if mode != "masked_surface_finish":
        raise ValueError("Use rendered_panorama or masked_surface_finish")
    base_path, mask_path, mrp = get("base"), get("mask"), get("mask_review")
    mr = read_object(mrp)
    review_common(mr)
    for key, path in (("base_sha256", base_path), ("surface_render_sha256", surface_path),
                      ("mask_sha256", mask_path), ("scene_spec_sha256", spec_path)):
        if mr.get(key) != digest(path):
            raise ValueError(f"Mask review has missing or stale {key}")
    for key in ("camera_and_layout_aligned", "occlusions_and_contacts_checked",
                "full_surface_coverage_checked", "boundary_blend_checked"):
        if mr.get(key) is not True:
            raise ValueError(f"Mask review missing {key}")
    with Image.open(mask_path) as im:
        if im.format != "PNG" or im.mode not in ("L", "1"):
            raise ValueError("Mask must be an opaque grayscale PNG")
        mask = np.asarray(im.convert("L"))
    base = image_pixels(base_path)
    pixels = compose(base, surface, mask)
    return pixels, {"mode": mode, "protected_surface_ids": sorted(protected),
                    "core_pixel_count": int(np.count_nonzero(mask == 255)),
                    "blend_pixel_count": int(np.count_nonzero((mask > 0) & (mask < 255)))}, paths


def build(request_path: Path, output: Path) -> Path:
    pixels, info, inputs = expected(request_path)
    manifest_path = output.with_suffix(".surface-finish.json")
    if output.suffix.lower() != ".png":
        raise ValueError("Output must be PNG")
    for dest in (output, manifest_path):
        if dest.resolve() in {p.resolve() for p in [request_path, *inputs]}:
            raise ValueError("Do not overwrite inputs")
        if dest.exists():
            raise ValueError("Use a fresh versioned output path")
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(pixels).save(output)
    manifest = {"surface_finish_version": 1, "request": binding(request_path),
                "output": binding(output), **info,
                "scope": "Exact reconstruction of final pixels; not rendering/visual/reconstruction proof."}
    manifest_path.write_text(json.dumps(manifest, indent=2)+"\n")
    return manifest_path


def verify_finish(manifest_path: Path, candidate: Path, scene_spec: Path) -> list[str]:
    try:
        manifest = read_object(manifest_path)
        if manifest.get("surface_finish_version") != 1:
            return ["Surface finish schema is missing or stale"]
        root = manifest_path.resolve().parent
        request_path = resolve_artifact(root, manifest, "request")
        output = resolve_artifact(root, manifest, "output")
        if digest(output) != digest(candidate):
            return ["Candidate was changed after deterministic surface finish"]
        req = read_object(request_path)
        bound_spec = resolve_artifact(request_path.parent, req, "scene_spec")
        if digest(bound_spec) != digest(scene_spec):
            return ["Surface finish belongs to a different scene spec"]
        predicted, _, _ = expected(request_path)
        actual = image_pixels(candidate)
        if predicted.shape != actual.shape or not np.array_equal(predicted, actual):
            return ["Candidate pixels differ from the recomputed deterministic final finish"]
        return []
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        return [str(exc)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    create = subs.add_parser("build")
    create.add_argument("request", type=Path)
    create.add_argument("output", type=Path)
    verify = subs.add_parser("verify")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("candidate", type=Path)
    verify.add_argument("scene_spec", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "build":
            print(build(args.request, args.output))
            return 0
        errors = verify_finish(args.manifest, args.candidate, args.scene_spec)
        print(json.dumps({"surface_pixels_match": not errors, "errors": errors}, indent=2))
        return 2 if errors else 0
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print(f"surface_finish: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
