# Surface topology and projection locks

## Contents
- Evidence before pattern constraints
- Failure model and routing
- Coordinate contract
- Geometry-guide integration
- Deterministic surface finishing
- Masked planar projection utility
- Review and downstream isolation

## Evidence before pattern constraints

A floor's plane, extent, slope, and contacts are geometry. Its seams, tiles, grain,
color divisions, and gloss are separate observations. Modeling the plane never
authorizes adding a lattice. Preserve continuous stone, irregular material variation,
or subtle seams as observed; do not turn any of them into alternating square tiles.

Before selecting a regular pattern, record `pattern_basis` in its surface constraint:

- `kind`: `observed` or `user_requested`.
- `source`: reference file/region, or the actual user request.
- `evidence`: what establishes the specific pattern; identify repeatable physical
  joints/material units and distinguish them from light and reflections.

This is required review evidence, not automatic image recognition: the current
Python guards do not validate these fields or prove a pattern exists. Inspect the
source yourself. Do not cite a generated candidate, calibration grid, proxy, or
your own prior scene spec as independent source evidence.

For no confirmed/requested pattern, record `pattern: none` and an `assessment`
describing visible material and any uncertainty. Preserve its appearance without
synthesizing regular joints. This does not license deleting a clearly observed
pattern. Do not infer checker colors, tile size, phase, or a new material when those
features have no source support. Ask only if unresolved pattern choice is essential
to an explicit user requirement; otherwise continue conservatively without adding it.

For example, a glossy green atrium floor with warm reflected light does not justify
a green-and-beige checkerboard. A visibly tiled floor can have same-color tiles;
visible seams alone do not justify alternating colors. Conversely, preserve a real
checkerboard or an explicitly requested one with its original geometry and appearance.

## Failure model and routing

A flat proxy floor constrains its silhouette, not the topology of painted tiles.
Promote tile seams, boards, brick courses, road markings, and ceiling grids from
"decorative detail" to structural invariants when they establish spatial scale.
Keep genuine circular mosaics, curved architecture, slopes, and irregular natural
surfaces when the brief calls for them; never impose a checkerboard universally.

For a checkerboard floor, preserve a single Cartesian lattice: two orthogonal
world-space axes, constant tile dimensions, one rotation and one phase/origin.
Reject camera-centered rings, wedges, spirals, bent joints, or restarts at sector
boundaries. Tile dimensions and camera height inferred from one image are estimates.
Do not infer a metric scale as ground truth from an uncalibrated photograph.

For regular surface patterns, require route 1 for the FINAL pixels. Routes 2/3 may only create intermediates:

1. **World-space surface finish:** generate/select orthographic material patches,
   apply them to the locked plane/mesh, and deterministically render the complete
   single-center panorama or a correctly occluded surface pass. Use a compatible
   material renderer for shadows/reflections when required. Do not let a subsequent
   unconstrained image edit repaint the protected lattice.
2. **Guide-conditioned image refinement:** supply a guide that actually contains
   the required pattern, not a blank floor. Inspect every final candidate. Treat
   RGB, depth, normal, edge, and textual conditioning as guidance unless the actual
   renderer/compositor enforces the constraint. Use only supported tool controls.
3. **Overlapping perspective repair:** repair a local nadir/oblique view, then
   apply a defined inverse spherical mapping with overlap and visibility checks.
   The checker alone does NOT implement inverse patch compositing. Do not claim
   six independently generated cube faces constitute a consistent scene.

After the first global lattice failure, require route 1 for completion; do not spend the repair budget
repeating "straight lines" or repainting the entire equirectangular lower half.
Do not reuse a badly warped floor as the canonical structural reference.

## Coordinate contract

Use the camera convention in geometry.md. For unit ray d from camera C, intersect
a horizontal plane at z=z_floor:

```text
t = (z_floor - C.z) / d.z
P = C + t*d                       # only d.z < 0 and t > 0
q = transpose(Rz(grid_rotation)) * (P.xy - grid_origin_xy)
material_u = q.x / period_x
material_v = q.y / period_y
checker = (floor(material_u) + floor(material_v)) mod 2
```

Grid rotation is a world-space positive rotation from +X toward +Y, not image
yaw. The material origin stays fixed in the world; it must not reset at panorama
sectors or follow the viewer. For the procedural checker, period is one tile;
for a repeated image texture, period is the physical size of that whole image.
Do not confuse material UVs with panorama longitude/latitude UVs.

The projection should introduce any necessary curvature in the raw 2:1 image.
Never hand-straighten that image. Under ordinary pinhole reprojection, straight
physical edges should be straight. In a nadir view perpendicular to a horizontal
floor, equal square tiles should form an equal-scale square lattice, rotated as
specified. Oblique views show foreshortening and vanishing points, not equal image
spacing. Do not require equal spacing in oblique perspective views.

No universal "all pole-row pixels must match" test is valid: pixel centers do
not lie exactly at the pole, and a real material discontinuity may pass beneath
the camera. Check an actual nadir perspective instead.

## Geometry-guide integration

Only after establishing pattern evidence, record constraints in scene-spec.json. The following is an explicitly requested checkerboard example, not a default floor:

```json
{
  "scene_type": "interior",
  "route": "geometry_guided",
  "surface_constraints": [{
    "id": "floor",
    "geometry": "horizontal_plane",
    "pattern": "cartesian_checkerboard",
    "pattern_basis": {
      "kind": "user_requested",
      "source": "example user brief",
      "evidence": "The example brief explicitly requests a square checkerboard floor."
    },
    "tile_size": [0.65, 0.65],
    "origin_xy": [0.0, 0.0],
    "rotation_degrees": 23.0,
    "scale_basis": "estimated, not calibrated",
    "preserve": ["seam topology", "tile phase", "world orientation"],
    "finish_route": "world_space_surface"
  }]
}
```

These are example values, not values measured from the hotel reference. Match
the current scene. For a non-patterned surface, record that assessment explicitly.

Use `Scene.checker_floor(...)` only for that evidence-backed checkerboard, to include
actual clipped world-space tiles in a proxy scene. Use a plain quad/mesh for a floor
without a confirmed/requested regular pattern. For a checkerboard, all tile parts
share one object ID. This is a flat-color guide, not a realistic final marble floor.
Do not add an overlapping coplanar floor quad.
For more complex tile designs, use world-space texture mapping in a compatible
renderer rather than building millions of mesh patches.

Render a neutral control room for viewer diagnostics:

```bash
python3 "$SKILL_DIR/scripts/render_guide.py" \
  --scene "$SKILL_DIR/examples/floor-calibration.py" \
  --output-dir "$WORK/calibration" --width 1536 --samples 4
python3 "$SKILL_DIR/scripts/check_pano.py" \
  "$WORK/calibration/geometry-guide.png" --output-dir "$WORK/calibration-check"
```

The control is not a repaired version of the user's scene.

## Deterministic surface finishing

Use the mandatory version-3 finalization in references/execution-contract.md.
The previous optional preference is superseded: guide conditioning alone cannot
produce a verified final patterned surface in this workflow.

Generate material in its own flat frame: an orthographic, repeatable albedo image
with no perspective, fisheye, camera-centered shading, baked window reflections,
or fake 3D room geometry. If a checker lattice is critical, construct its borders
procedurally and restrict generated marble/brushwork to tile interiors. Validate
any generated texture in material space before applying it.

Keep lighting and view-dependent reflections separate from tile topology.
Do not reproject a photographed reflective floor as though it were flat albedo.
The bundled CPU renderer and planar utility do not simulate glossy reflection or
indirect lighting; use a compatible renderer when these are important, or disclose
the albedo-only limitation rather than presenting the guide as final artwork.

For a hybrid composite, require actual camera/layout correspondence and a reviewed
visible-floor mask on the current candidate. Exclude furniture, walls, plants,
contact boundaries and foreground objects. Proxy ID maps are a proposal for a
mask, not segmentation of the AI image. A drifted candidate invalidates blind use
of the proxy mask. Never replace the lower half of the panorama indiscriminately.
Keep protected lattice pixels outside any later unconstrained AI edit.

## Masked planar projection utility

`planar_floor.py` is an albedo projector / calibration tool, not automatic scene
reconstruction, segmentation, a material generator, or a final-quality renderer.
It supports only a level camera in this panorama convention and a horizontal
plane. Use a mesh renderer for slopes, steps, curved floors, or tilted panoramas.

Calibration-only mode:

```bash
python3 "$SKILL_DIR/scripts/planar_floor.py" \
  --spec "$SKILL_DIR/examples/floor-spec.json" \
  --output "$WORK/floor-calibration.png" --width 1536 --samples-side 2
```

Use `--texture "$WORK/albedo.png"` for a repeated flat texture. Without a texture,
the utility renders a procedural checker. Colors are sRGB values in [0,255],
unlike the linear colors accepted by Scene. The constant upper hemisphere is a
deliberate calibration background, never a valid way to conceal defects in art.
Grazing-angle aliasing is not solved by this small supersampler; restrict the
visible-floor mask or use a production texture-filtered renderer as appropriate.

Optional guarded compositing:

```bash
python3 "$SKILL_DIR/scripts/planar_floor.py" \
  --spec "$WORK/floor-spec.json" --texture "$WORK/albedo.png" \
  --base "$WORK/current.png" --mask "$WORK/visible-floor-mask.png" \
  --mask-review "$WORK/mask-review.json" --output "$WORK/composited.png"
```

The mask must be an opaque grayscale PNG at the exact candidate dimensions:
white replaces visible floor; black protects the original pixel; intermediate
values blend in linear light. Avoid broad feathering that creates double joints.
The tool rejects empty masks, size mismatches, masks over non-floor-facing rays,
and stale/missing review records. It cannot detect a chair accidentally included
in an otherwise plausible mask. Inspect the actual mask before signing it.

`mask-review.json` requires `status: passed`, `reviewer`, specific `evidence`,
`candidate_sha256`, `mask_sha256`, `floor_spec_sha256`,
`camera_and_layout_aligned: true`, and `occlusions_and_contacts_checked: true`.
Bind these to current bytes. The output's manifest records provenance, but never
constitutes visual approval. Run full QA on the exact composite afterward.

## Review and downstream isolation

Inspect nadir plus the eight -45-degree floor views and their overlapping
boundaries. Compare phase/orientation/scale with the guide; do not confuse
reflections or shadows with joints. A global ring/wedge artifact in a required Cartesian grid is a major
`surface_pattern` failure, even if the image format and seam checks pass. So is an
unrequested grid on a source surface without one, even when its rendered joints
are perfectly straight. Remove the invention; do not optimize its topology.

When the user reports a wrapped-view or reconstructed-scene defect:

1. Reproject the original candidate locally, at the original projection center.
2. Reproject a mathematically rendered checker control with the same checker.
3. If the candidate alone is bad locally, diagnose the source asset first.
4. If local views are good but a rotation-only viewer is bad, inspect projection
   type, angular coverage, vertical flip, longitude orientation, cropping, camera
   center, FOV and the viewer mapping using the same control panorama.
5. If rotation-only viewing is good but a reconstructed/translated view is bad,
   test the downstream geometry, depth convention, scale and camera assumptions.

Do not claim to have tested the user's downstream service without running it.
A sphere viewer is evaluated from its center, not after camera translation.
A passing panorama is not evidence of translational parallax or reliable 3D
reconstruction. Record downstream status separately as untested, failed, or passed
for the specifically tested configuration.
