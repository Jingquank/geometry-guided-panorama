#!/usr/bin/env python3
"""Compile/cache the bundled C++17 guide renderer and render a trusted scene.py."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import uuid

import numpy as np
from PIL import Image

from geometry_core import Scene

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compiler_path() -> str:
    candidates = [os.environ.get("CXX", ""), "c++", "g++", "clang++"]
    for candidate in candidates:
        if candidate and (resolved := shutil.which(candidate)):
            return resolved
    raise RuntimeError("A C++17 compiler is required. No installation was attempted.")


def compile_renderer(cache: Path) -> tuple[Path, bool, str, float]:
    start = time.perf_counter()
    compiler = compiler_path()
    version = subprocess.run([compiler, "--version"], capture_output=True,
                             text=True, check=True, timeout=15).stdout
    source = ROOT / "renderer.cpp"
    flags = ["-std=c++17", "-O3", "-pthread"]
    fingerprint = hashlib.sha256((sha256(source) + compiler + version +
                                 platform.platform() + " ".join(flags)).encode()).hexdigest()[:20]
    binary = cache / fingerprint / "renderer"
    binary.parent.mkdir(parents=True, exist_ok=True)
    compiled = not binary.is_file()
    if compiled:
        temp = binary.with_name(f"renderer-{uuid.uuid4().hex}.tmp")
        try:
            subprocess.run([compiler, *flags, str(source), "-o", str(temp)],
                           capture_output=True, text=True, check=True, timeout=120)
            os.replace(temp, binary)
        finally:
            temp.unlink(missing_ok=True)
    return binary, compiled, fingerprint, time.perf_counter() - start


def load_scene(path: Path) -> Scene:
    if not path.is_file():
        raise ValueError(f"Scene file does not exist: {path}")
    module_spec = importlib.util.spec_from_file_location("ggp_task_scene", path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError("Cannot import the scene file")
    module = importlib.util.module_from_spec(module_spec)
    # A scene is executable Python. Execute only a scene authored or inspected for this task.
    module_spec.loader.exec_module(module)
    factory = getattr(module, "build_scene", None)
    if not callable(factory):
        raise ValueError("scene.py must define build_scene() -> geometry_core.Scene")
    scene = factory()
    if not isinstance(scene, Scene):
        raise TypeError("build_scene() must return geometry_core.Scene")
    if len(scene.triangles) > 2_000_000:
        raise ValueError("Guide triangle limit exceeded; simplify the scene")
    return scene


def serialize(scene: Scene, path: Path) -> None:
    with path.open("w", encoding="ascii") as stream:
        stream.write("GGP1\n")
        for value in [scene.camera, scene.sky_top, scene.sky_horizon,
                      scene.sky_bottom, scene.sun_direction]:
            stream.write(" ".join(format(x, ".17g") for x in value) + "\n")
        stream.write(f"{scene.ambient:.17g} {len(scene.triangles)}\n")
        for a, b, c, color, object_id in scene.triangles:
            stream.write(" ".join(format(x, ".17g") for x in (*a, *b, *c, *color)))
            stream.write(f" {object_id}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--width", type=int, default=1536)
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--threads", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--no-shadows", action="store_true")
    args = parser.parse_args()
    if not 16 <= args.width <= 8192 or args.width % 2:
        parser.error("width must be even and between 16 and 8192")
    if not 1 <= args.samples <= 64 or not 1 <= args.threads <= 64:
        parser.error("samples and threads must be between 1 and 64")
    start = time.perf_counter()
    try:
        scene_path, output = args.scene.resolve(), args.output_dir.resolve()
        scene = load_scene(scene_path)
        output.mkdir(parents=True, exist_ok=True)
        source_path = output / "scene-data.txt"
        serialize(scene, source_path)
        cache = args.cache_dir.resolve() if args.cache_dir else output / ".renderer-cache"
        binary, compiled, cache_key, compile_seconds = compile_renderer(cache)
        render_start = time.perf_counter()
        prefix = output / "raw"
        subprocess.run([str(binary), str(source_path), str(prefix), str(args.width),
                        str(args.samples), str(args.threads), str(int(not args.no_shadows))],
                       capture_output=True, text=True, check=True, timeout=300)
        render_seconds = time.perf_counter() - render_start
        for source, name in [(output / "raw-color.ppm", "geometry-guide.png"),
                             (output / "raw-ids.ppm", "object-ids.png")]:
            with Image.open(source) as image:
                image.save(output / name, format="PNG")
            source.unlink()
        raw_depth = output / "raw-depth.bin"
        depth = np.fromfile(raw_depth, dtype=np.float32).reshape(args.width // 2, args.width)
        np.save(output / "depth.npy", depth)
        raw_depth.unlink()
        manifest = {
            "implementation": "new-reference-implementation-not-original-renderer",
            "projection": "equirectangular", "angular_coverage_degrees": [360, 180],
            "axes": {"right": "+X", "forward": "+Y", "up": "+Z"},
            "front_u": 0.5, "seam_u": [0.0, 1.0], "pixel_centers": True,
            "camera": list(scene.camera), "width": args.width, "height": args.width // 2,
            "samples": args.samples, "threads": args.threads, "shadows": not args.no_shadows,
            "triangle_count": len(scene.triangles), "objects": scene.objects,
            "object_id_encoding": "R + 256*G + 65536*B; 0 is environment; center-ray sample",
            "depth_encoding": "radial scene-unit distance; +infinity is environment; center-ray sample",
            "scene_path": str(scene_path), "scene_sha256": sha256(scene_path),
            "serialized_scene_sha256": sha256(source_path),
            "guide_sha256": sha256(output / "geometry-guide.png"),
            "compiled_this_run": compiled, "compiler_cache_key": cache_key,
            "observed_seconds": {"compiler_check_and_build": round(compile_seconds, 4),
                                 "render": round(render_seconds, 4),
                                 "total": round(time.perf_counter() - start, 4)},
            "limitations": ["Geometry guide only; not physically based final art.",
                            "Object IDs and depth describe the proxy scene, not AI output.",
                            "Camera position and scene plausibility require visual review."]
        }
        (output / "guide-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(json.dumps({"guide": str(output / "geometry-guide.png"),
                          "compiled_this_run": compiled,
                          "observed_seconds": manifest["observed_seconds"]}, indent=2))
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"render_guide: external command failed: {exc.stderr or exc}", file=sys.stderr)
    except (OSError, ValueError, TypeError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"render_guide: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
