# Geometry contract and reference renderer

## Coordinate contract

Use a single projection center C for every ray. In a right-handed world, +X is right, +Y is forward, and +Z is up. Positive image yaw points from forward toward camera-right; do not substitute a renderer's positive world-Z rotation without converting it.

For a W x H panorama, require W = 2H. At pixel-center coordinates:

```text
u = (x + 0.5) / W
v = (y + 0.5) / H
yaw   = 2*pi*(u - 0.5)
pitch = pi*(0.5 - v)
d = (sin(yaw)*cos(pitch), cos(yaw)*cos(pitch), sin(pitch))
ray(t) = C + t*d, t > 0
```

Direction landmarks: u=0.5 is forward; u=0.75 right; u=0.25 left; u=0/1 back. These are angular coordinates; an even-sized image need not have a pixel center exactly at a landmark. Pixel centers do not sample the exact pole. Do not duplicate a boundary column to make pixel values equal.

Use angular coordinates and the same camera center to compare differently sized panoramas. A yaw roll rotates longitude without introducing parallax. Do not generate six unrelated perspective images and stitch them as though they shared a physical camera.

## Supported scene API

Create a task-owned Python file with `build_scene() -> Scene`:

```python
from geometry_core import Scene


def build_scene() -> Scene:
    scene = Scene(camera=(0, 0, 1.6), ambient=0.4)
    scene.quad("ground", [(-8,-8,0),(8,-8,0),(8,8,0),(-8,8,0)], (0.4,0.3,0.2))
    scene.box("bench-01", (-1,2,0), (1,2.5,0.5), (0.3,0.2,0.1))
    return scene
```

Methods:

```text
triangle(id, a, b, c, color)
quad(id, four_perimeter_ordered_vertices, color)
box(id, minimum_xyz, maximum_xyz, color)
cylinder(id, base_xyz, radius, height, color, segments=32, capped=True)
mesh(id, vertices, triangle_or_quad_faces, color)
checker_floor(id, minimum_xy, maximum_xy, z=0, cell=(0.65,0.65),
              origin=(0,0), rotation_degrees=0, colors=(linear_rgb_A,linear_rgb_B))
```

Colors are linear RGB in [0,1]. Distances are scene units, normally estimated meters. Use planar convex quads; triangulate non-planar terrain and other polygons. Reuse an ID for parts of one object; create distinct IDs for different physical objects. Shared IDs do not enforce semantic counts in AI output.

The renderer is two-sided and supports geometry, constant material colors, ambient fill, one directional light, and hard shadows. It does not support physically based global illumination, textures, transparency, reflections, depth of field, or displacement. Do not paint a reflective/transmissive appearance into a guide and claim its light transport is simulated. Use an already compatible renderer for scene-critical effects beyond this implementation.

Use `examples/room.py`, `examples/outdoor.py`, and `examples/curved-gallery.py` only to learn the API. Do not inherit their objects or layouts into an unrelated user request.

## Regular surface patterns

A plain ground quad/mesh is the correct guide for an unpatterned floor. Use
`checker_floor` in its place only for a checkerboard established by source evidence
or an explicit user request (see references/surface-lock.md). The helper and
calibration examples are not default floor designs.
It clips world-space tiles to a rectangular footprint; every tile belongs to the
same surface ID. Keep one global lattice origin, rotation, and dimensions.
Do not overlay an additional coplanar ground quad. Colors remain linear RGB.
Read references/surface-lock.md for deterministic finishing, visibility masks,
material-space coordinates and the limited `planar_floor.py` utility.

## Execution and cache

Dependencies: Python 3.10+, NumPy, Pillow, and a C++17 compiler with thread support (`c++`, `g++`, or `clang++`). No Python package install, Blender install, model download, or network operation occurs automatically. Set `CXX` to a compiler executable if needed; arbitrary shell commands in `CXX` are not supported.

`render_guide.py` imports executable Python from `--scene`. Use a scene authored for the task or inspect it first. Do not run untrusted user-supplied Python merely because it has the right filename.

The wrapper compiles `scripts/renderer.cpp` with `-std=c++17 -O3 -pthread`. The cache key includes source content, compiler path/version, platform, and flags. Reuse `--cache-dir` across guide revisions. A changed scene reuses the binary, not the previous layout or image.

Default: width 1536, height 768, 4 deterministic samples/pixel, up to 8 threads. CLI bounds prevent accidental unbounded image or sampling sizes. `--threads` and `--no-shadows` are optional. The C++ core uses a bounding-volume hierarchy for triangle intersections. These design choices are not an empirical guarantee of optimal performance for every scene.

Outputs:

| File | Meaning |
| --- | --- |
| `geometry-guide.png` | Antialiased guide, linear lighting encoded into sRGB-like values. |
| `object-ids.png` | Center-ray ID: R + 256*G + 65536*B. Zero means environment. Not antialiased. |
| `depth.npy` | Center-ray radial distance in scene units, float32; infinity means environment. |
| `guide-manifest.json` | Camera, dimensions, object IDs, hashes, compiler cache, measured timing. |
| `scene-data.txt` | Serialized geometry passed to the renderer. |

Inspect the actual PNG through reprojection before refinement. A scene can be mathematically rendered yet implausible, inside a wall, or missing important structure. Color/depth/ID outputs do not validate each other semantically.

## Minimal scene-spec example

```json
{
  "scene_type": "interior",
  "route": "geometry_guided",
  "style": "user-specified",
  "camera": {"position": [0, 0, 1.6], "scale_basis": "estimated", "level_horizon": true},
  "source_roles": [{"source": "reference-01", "role": "layout and appearance"}],
  "objects": [
    {"id": "table-01", "category": "table", "count": 1, "position": "front-left", "action": "retain"}
  ],
  "openings": [{"id": "doorway-01", "wall": "front", "count": 1}],
  "surface_constraints": [{"id": "ground", "pattern": "none", "assessment": "No regular pattern required in this example"}],
  "remove": [],
  "unknown_regions": [{"region": "back", "assumption": "continue the room materials; no extra doors"}],
  "acceptance": {"projection": "equirectangular", "coverage_degrees": [360, 180], "aspect_ratio": "2:1"}
}
```

Treat this as a schema example, not a scene preset. Include observations and uncertainties needed for the actual task; omit irrelevant fields.
