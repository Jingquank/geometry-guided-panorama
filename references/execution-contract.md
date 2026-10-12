# Execution and final-pixel contract (v3)

## Contents
- Preflight state
- Finish request and reviews
- Finalization and release
- Scope and failure cases

## Preflight state

A local record checker is useful only when the caller runs it. It does not intercept
native image tools. Never equate a changed instruction file with successful execution.
Resolve the selected package; preserve a task log with its path/hash and actual commands.

Each artifact uses `{ "path": "relative/or/absolute/path", "sha256": "actual SHA-256" }`.
Paths in a record resolve relative to that JSON file, not the caller's current directory.

Create pipeline-state.json with these fields before image generation:

```json
{
  "pipeline_version": 3,
  "status": "preparing",
  "capabilities": {
    "local_processing": true,
    "output_bytes_accessible": true,
    "post_generation_processing": true
  },
  "planned_final_operation": "masked_surface_finish",
  "scene_spec": {"path": "scene-spec.json", "sha256": "MEASURE"},
  "scene_source": {"path": "scene.py", "sha256": "MEASURE"},
  "structural_base": {"path": "guide/geometry-guide.png", "sha256": "MEASURE"},
  "structural_base_review": {"path": "guide-check/visual-review.json", "sha256": "MEASURE"}
}
```

These are schemas, not ready-to-sign evidence. Never retain MEASURE in real records.
Confirm host capabilities rather than assuming a successful call can be postprocessed.
For an image-only/terminal host, set post_generation_processing to false and stop the
verified route. Separate material generation into a later process/turn only with an
explicitly communicated intermediate status. Do not call an intermediate a final pano.

Run execution_guard.py and hash-bind its output as `preflight_report`. It requires a
passed guide review on structural routes, an explicit structured surface assessment,
and a deterministic last operation for any surface pattern except `none`, `solid`,
`unpatterned`, or `irregular_natural`. Do not mislabel a checkerboard as unpatterned.
Allowed final operations for a protected pattern are `masked_surface_finish` and
`rendered_panorama`. Same-layout edits with regular tiles still require final protection.
For surfaces without an observed/requested regular pattern, the final operation may
be image generation, followed by QA; a floor does not itself require a surface finish.
Before preflight, follow the source-evidence rules in surface-lock.md. Record
`pattern_basis` for regular patterns and an honest assessment for `pattern: none`.
The guards check declared patterns and artifacts, not image semantics or pattern
authorization. A successful preflight cannot validate an invented checkerboard;
source-versus-guide review remains mandatory.

Capabilities are declared observations, not remote-runtime attestation. This checker
cannot prove when a tool was called; retain genuine tool logs where available.

## Finish request and reviews

The surface finisher accepts already rendered pixels; it cannot turn a prompt into a
world-space material render. Do not relabel a generated panorama as rendered evidence.
Use a compatible renderer for production materials and lighting. The bundled flat-color
renderer and planar projector are calibration/proxy tools unless their limited visual
style genuinely meets the user's expressly requested result.

Create finish-request.json with:

```json
{
  "finish_request_version": 1,
  "mode": "masked_surface_finish",
  "scene_spec": {"path": "scene-spec.json", "sha256": "MEASURE"},
  "surface_render": {"path": "surface-render.png", "sha256": "MEASURE"},
  "surface_review": {"path": "surface-review.json", "sha256": "MEASURE"},
  "render_provenance": {"path": "surface-render-record.json", "sha256": "MEASURE"},
  "base": {"path": "intermediate-art.png", "sha256": "MEASURE"},
  "mask": {"path": "visible-surface.png", "sha256": "MEASURE"},
  "mask_review": {"path": "mask-review.json", "sha256": "MEASURE"}
}
```

Use `mode: rendered_panorama` for a complete final scene render, omitting base/mask/mask_review.
The surface_render must be an opaque exact 2:1 PNG at final resolution. In masked mode
all image/mask dimensions must match without implicit resizing. Multiple protected
surfaces may share a combined render/mask; inspect every surface named in the scene spec.

Record actual rendering in surface-render-record.json: `output_sha256`,
`scene_spec_sha256`, `mapping: world_space`, `renderer` (actual identifier), and nonempty
`render_settings` (scene/material inputs and their hashes, camera, projection, samples).
Preserve the renderer's own output log alongside it. These fields are provenance,
not cryptographic proof that an external renderer ran.

Surface-review.json requires:
- `status: passed`, reviewer, specific evidence, surface_render_sha256, scene_spec_sha256.
- `render_role: final_world_space_surface`, protected_surface_ids, reviewed_views.
- `camera_and_projection_matched: true`, `material_and_pattern_checked: true`.

For a floor/ground surface, inspect nadir and all eight floor-* views. For a non-floor
surface record its required_views in the scene-spec entry and inspect all of them
(e.g. zenith and suitable upward views for a ceiling; add explicit views as needed).
Never approve a surface because its manifest exists. Check seams, physical coordinates,
finish quality, and actual renderer camera correspondence.

Mask-review.json requires:
- `status: passed`, reviewer, specific evidence.
- base_sha256, surface_render_sha256, mask_sha256, scene_spec_sha256.
- `camera_and_layout_aligned: true`, `occlusions_and_contacts_checked: true`,
  `full_surface_coverage_checked: true`, `boundary_blend_checked: true`.

Use an opaque L/1 PNG mask: 255 replaces the actual visible surface, 0 preserves the
base. Gray values are allowed only within two pixels of both the core and exterior.
The fully replaced interior is mandatory. This restricts double-grid blending but does
not detect a chair included by mistake or a missed floor patch. Inspect the mask against
the current artwork. Do not use a mask made for a different camera or pre-drift guide.
Subpixel contact/reflection quality remains a visual review responsibility.

## Finalization and release

Run surface_finish.py build on a fresh versioned path. It performs linear-light
boundary blending, preserves zero-mask and full-mask pixels exactly, and writes
`panorama.surface-finish.json`. Do not manually manufacture that manifest.

Run final check_pano.py, inspect all required views, and complete the current review.
Add these hash-bound entries to pipeline-state.json:

- `generation_request`: actual input references, authored prompt, and structural base
  SHA-256. For zero-AI rendering use `mode: render_existing_materials` plus actual_render_inputs;
  never invent a prompt or an AI call for a renderer-only job.
- `candidate` and `candidate_review`: exact final file and actual completed review.
- `surface_finish`: the produced finish manifest, required for every protected pattern.
- `preflight_report`: the successful pre-generation report, still matching current inputs.

Set status to ready_for_review and run release_check.py. In addition to record checks,
it reconstructs the expected final image from the surface/base/mask and compares every
decoded RGB pixel. A changed candidate, rehashed post-finish image, stale mask/review,
missing protected surface, or incompatible spec must fail.

Perform resizing/longitude rolls consistently on all relevant inputs before finalization.
A final artifact transformed afterward must be finished and reviewed again. Do not let
AI repaint a finished surface and then simply refresh its file hash.

## Scope and failure cases

The finisher is not an automatic floor repair model. It relies on a correct world-space
render, matched camera, complete visible mask, and honest visual review. A wrong render
can be copied perfectly; therefore pixel equality does not establish spatial correctness.
The final full-file QA cannot be skipped even if the deterministic comparison passes.

Critical negative cases to test: missing guide; terminal generation; prompt-only finish;
patterned scene with no finish manifest; edited final PNG even with refreshed hashes;
mask not bound to the candidate; missed coverage; broad blending; wrong guide/scene;
old reviews; copied calibration labeled final artwork.

Synthetic fixture reviews used by unit tests are never artwork approvals. Report unit
coverage separately from actual AI output quality and downstream viewer testing.
