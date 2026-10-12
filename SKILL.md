---
name: geometry-guided-panorama
description: Create, edit, and diagnose full 360 x 180 degree, 2:1 equirectangular panoramas from text or images. Use for architecture, interiors, outdoor scenes, and warped floors or repeated objects in a 360 viewer. Preserve the reference structure, materials, and pattern presence or absence. Only clearly observed or explicitly requested regular patterns require world-space rendering or deterministic surface compositing; never invent a grid for validation. Inspect the actual output through perspective reprojection. Use for panorama generation and repair, not ordinary wide-angle images or true multi-view 3D recovery.
---

# Geometry-Guided Panorama

## 0. Establish the execution contract FIRST

Resolve and read the actual selected package, not a remembered earlier version. This is the **execution-and-final-pixel-lock revision, pipeline version 3**. Follow [references/execution-contract.md](references/execution-contract.md) for records and commands.

**Do not call image generation as the first step for a structural scene.** A request to use this skill authorizes the workflow, not replacement of it with a longer panorama prompt. Tool calls and artifacts must exist; describing geometry in a prompt does not create geometry.

Use one task workspace. Inspect the current reference. For a reported failure, reproject the exact failed PNG before generating anything else. If regular tiles form rings/wedges in normal downward views, stop the full-panorama repaint route immediately. Do not reset this failure history merely because the user repeats the original reference.

Check local processing, usable image inputs, access to output bytes, and the ability to continue with finalization/inspection. If a native generator ends the turn or prevents subsequent processing, do not use it as the final operation in verified mode. Mark that route blocked; use only an explicitly authorized unverified preview or a separate material-generation stage. Do not silently downgrade.

A skill file and a CLI checker cannot intercept a direct image-tool call made outside the workflow. Never promise an unbypassable gate. Follow the gate here; production orchestration must call it before serving the asset.

## 1. Select the route and lock the scene

**Reference fidelity comes before convenience of modeling or validation.** For image-to-panorama work, preserve the visible architecture, object forms, materials, colors, gloss, and existing surface pattern or lack of one. The request authorizes projection and necessary out-of-view completion, not redesign. A valid floor plane does not imply tiled flooring; a few color boundaries do not establish a checkerboard. Do not add seams, alternating tiles, decorative bands, or simplify distinctive objects merely to suit the proxy renderer. Explicit user changes override the reference; otherwise correct a conflicting guide to match the source.

Before building the guide, separate observations from assumptions in `scene-spec.json`. A regular pattern needs evidence from an identifiable source region (repeated physical joints or repeated material units), or the user's explicit request. Reflections, shadows, highlights, and irregular stone variation are not sufficient evidence. If pattern presence is unclear, keep that uncertainty in `assessment` and use `pattern: none` to mean **no regular pattern is authorized for synthesis**, not a claim about hidden construction. Preserve visible appearance without inventing a grid. User clarification that a surface has no grid overrides an earlier model inference. Read the evidence rules in [references/surface-lock.md](references/surface-lock.md).

| Scene | Required route |
| --- | --- |
| New interior, architecture, courtyard, street, or important layout | `geometry_guided`: author scene geometry matching this reference. |
| Same-layout material/style edit | `same_layout_edit`: first validate the source panorama. |
| Terrain or foreground-constrained landscape | `geometry_guided`: terrain/silhouette proxies, not four walls. |
| Unconstrained sky or distant landscape | `direct_simple`: allowed only with `structure_sensitive: false`. |
| Clearly observed or explicitly requested regular pattern on a floor, wall, road, or ceiling | Preserve that specific pattern with a deterministic final surface finish; do not introduce one. |

Save `scene-spec.json`: scene type and route, source roles, fixed camera, estimated scale, observed layout anchors, stable object IDs/counts, retain/remove instructions, unknown-region assumptions, and `surface_constraints`. Never reuse the example room as the new scene. Preserve intended curves and circular mosaics; reject accidental rings only when inconsistent with the brief. Scale and unseen content inferred from one image are estimates/completions, not recovered truth.

For each surface record `id`, `geometry`, `pattern`, world axes/origin, dimensions/rotation/phase when relevant, and `finish_route`. Use a structured `pattern: none` assessment for unpatterned surfaces. For every regular pattern require `world_space_surface` or `deterministic_render`; do not write merely "prefer". Treat seams and lattice layout as structure; grain/brushwork as appearance. Read [references/surface-lock.md](references/surface-lock.md).

Use +X right, +Y forward, +Z up. Front is image center, back is the horizontal wrap boundary, zenith is top, nadir bottom. Sample pixel centers with periodic longitude and no duplicated final column. Use one fixed projection center. Read [geometry.md](geometry.md) before geometry work.

## 2. Build and inspect the guide before generation

Create a task-specific `scene.py` using the bundled API or a compatible renderer. Model silhouettes, openings, occlusion, and contacts independently of material pattern. For an unpatterned or uncertain floor, use a plain plane/mesh with source-matched base color; do not call `Scene.checker_floor(...)`. Use that helper only for an evidence-backed checkerboard, and a matching mapper for other observed patterns. Calibration grids belong in separate diagnostic artifacts and must never become the artwork guide. Do not create overlapping coplanar floors.

```bash
python3 "$SKILL_DIR/scripts/render_guide.py" --scene "$WORK/scene.py" \
  --output-dir "$WORK/guide" --cache-dir "$WORK/.renderer-cache" --width 1536 --samples 4
python3 "$SKILL_DIR/scripts/check_pano.py" "$WORK/guide/geometry-guide.png" \
  --output-dir "$WORK/guide-check"
```

Inspect the guide in perspective, including nadir and oblique floor views, and compare the corresponding visible region directly with the original reference. Check both structural alignment and whether the guide invented a pattern or changed an object. Record actual evidence. Fix the guide before refinement; consistency with an incorrect scene spec is not approval. The bundled CPU renderer is a proxy renderer, not a production marble/reflection renderer. Proxy IDs/depth are not segmentation/depth measured from later AI artwork. Increase samples only for aliasing, not layout mistakes.

Create the version-3 pipeline state and run the preflight before an image call:

```bash
python3 "$SKILL_DIR/scripts/execution_guard.py" "$WORK/pipeline-state.json" \
  --output "$WORK/preflight.json"
```

Proceed only when the command succeeds and the report says `ready`. Missing capabilities, unreviewed guides, or an AI-last plan for a regular pattern must stop the verified route. Hash-bind the preflight report into the state.

## 3. Refine appearance while preserving the source

Preserve source materials, reflectivity, color variation, and pattern absence as well as structure. Complete unseen areas conservatively by continuing supported surfaces and forms. Do not use unseen-area freedom to redesign visible areas. The deterministic patterned-surface steps below apply only to evidence-backed patterns; unpatterned scenes can proceed from appearance refinement to full QA without a floor-replacement pass.

Read [refinement.md](refinement.md). Supply actual, identifiable references using the live tool contract; do not invent parameters, IDs, seeds, or hidden prompts. Distinguish the structural guide from appearance references. Retain the real request and untouched raw output, labeled **candidate**, never automatically final.

For regular surfaces, generate material in its own flat coordinate frame, then apply it to the fixed world-space surface. Prefer tile-interior grain patches; construct borders and tile placement deterministically. Do not bake perspective window reflections into albedo. Use a compatible material renderer for illumination/reflection quality. A UV projector alone is not a photorealistic final renderer.

Guide-conditioned panorama generation may supply an intermediate background, but cannot be the final operation for a regular pattern. Treat textual constraints, RGB/depth/edge guidance, and generative masks as soft unless an actual deterministic operation enforces the final pixels.

Save a reviewed `surface_render.png` from world-space rendering plus its provenance. For a hybrid, author and inspect an aligned visible-surface mask against the current candidate, excluding furniture/walls/plants and preserving contacts. Cover the whole visible patterned surface, not just the nadir. Broad blending of incompatible grids is prohibited. The projector's ID mask cannot be blindly reused after AI layout drift.

## 4. Finish protected pixels deterministically LAST, when required

Skip the patterned-surface finisher when no regular surface pattern is authorized. Never add a checkerboard to make this stage or its tests applicable.

Use a reviewed world-space final render, or compose its visible surfaces over the intermediate artwork. Follow the finish-request schema in [references/execution-contract.md](references/execution-contract.md).

```bash
python3 "$SKILL_DIR/scripts/surface_finish.py" build \
  "$WORK/finish-request.json" "$WORK/candidate-01/panorama.png"
```

This copies a rendered panorama or composites a reviewed surface and mask; it does NOT create a renderer, a mask, or a valid scene. Its manifest binds the inputs and recomputable output pixels. It rejects guides/calibration records as final surfaces, subject to honest provenance/review.

Do not pass the finished result through another unconstrained AI edit. To repair it, return to the intermediate artwork/materials, rerender/recompose, and repeat QA. A later resize/roll/color edit also invalidates this exact finish; perform necessary transformations consistently before finalization. Do not crop/pad/stretch a non-panorama into 2:1.

## 5. Inspect the exact final file, then release

```bash
python3 "$SKILL_DIR/scripts/check_pano.py" "$WORK/candidate-01/panorama.png" \
  --output-dir "$WORK/candidate-01/check" --guide "$WORK/guide/geometry-guide.png"
```

Omit `--guide` only for `direct_simple`; use the validated source for same-layout edits. Read [qa.md](qa.md). Inspect the 18 named views and the floor montage. Require straight physical joints in pinhole perspective, a regular square lattice in perpendicular nadir when intended, proper foreshortening in oblique views, seam continuity, complete poles, correct object counts, and preserved reference style. Raw equirectangular curves are not inherently defects.

`check_pano.py` exit code 0 means file checks only. It initializes visual status to `not_reviewed`; it does not measure semantic floor correctness. Record `failed` immediately on any major defect. Only mark `passed` after actual inspection of all required views and all checks. Hashes prove file identity, not that a judgment is true. Never turn synthetic test fixtures into artwork reviews.

Bind the final review and surface-finish manifest to the pipeline state. Set `ready_for_review` only when the evidence exists. Run:

```bash
python3 "$SKILL_DIR/scripts/release_check.py" "$WORK/pipeline-state.json"
```

For a regular pattern this now requires and recomputes the last deterministic surface finish, in addition to reviews/provenance. Missing finish, stale inputs, or changed final pixels must fail. Read [references/release-gate.md](references/release-gate.md). Do not call a failed or unreviewed candidate verified.

## 6. Failure and delivery

Fix geometry errors in geometry. If a guide or candidate introduced a pattern absent from the reference, remove that invented pattern and correct the scene spec, guide, and dependent evidence. Do not make the invention more geometrically precise. For drift in an actually observed/requested pattern, use deterministic surface rendering, not another whole-panorama "straight tiles" prompt. Repair isolated defects only in the intermediate artwork and repeat finalization. Default budget: one initial candidate and at most two targeted repairs; after the first repeated global-pattern failure, change methods rather than spend another identical attempt. Never claim universal latency/quality or unseen test results.

Deliver one verified PNG through a confirmed file link/attachment when available. Keep engineering files private unless requested. Report actual dimensions and validation only when permitted by the host's output rules. An explicitly authorized preview must be labeled unverified before a terminal image call, not silently substituted for a requested verified asset.

Separate local rotation-only inspection from the user's downstream viewer/reconstruction. Do not claim their model is fixed without testing it. Use a mathematical control to isolate source/viewer issues, but label it calibration, never a repaired hotel. Record actual stage durations, model calls, defects, and downstream status. For maintenance/testing read [references/evaluation.md](references/evaluation.md).
