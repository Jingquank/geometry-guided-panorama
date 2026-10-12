# Structure-preserving refinement

## Prepare the call

Run execution_guard.py BEFORE any panorama image call. For a regular surface,
this template creates an INTERMEDIATE, not the final deliverable. Require the
world-space final surface stage even when the prompt includes a grid constraint.
Do not reuse this route after a reported global tile-grid failure as another
unconstrained whole-panorama retry. Read references/execution-contract.md.


Inspect the approved base and appearance references. Attach or identify them through the actual image tool's supported mechanism. A local filename or invented image identifier is not an attachment. If the host chooses references automatically, explicitly describe each visible image's role without inventing unsupported call parameters.

Use the approved geometry guide for new layouts, or the approved existing panorama for a same-layout edit. Use a current candidate for a local repair. Do not return to an unrelated original photograph after a localized edit unless a deliberate structural reset is needed.

Prefer a compact positive description followed by concrete invariants. Do not bury the geometry contract beneath long lists of style adjectives. Use only supported input-fidelity, masking, depth, or structural controls. An RGB guide and a prompt are soft conditioning, not a geometric lock.

For image-to-panorama work, the original reference also governs visible structure,
materials, and pattern presence/absence; it is not merely a palette or mood board.
The guide supplies spherical projection and estimated geometry, not authorization
for new decor. Resolve source/guide conflicts by correcting the guide. Do not cure
projection drift by dropping source fidelity and restyling a coarse proxy.

## Request template

Fill only the fields relevant to this scene. Do not send unresolved placeholders.

```text
Task: Refine the appearance of the supplied structural base into one complete
360 x 180 degree equirectangular panorama, on a 2:1 canvas.

Input roles:
- Structural base: [identify the actual attached guide or approved panorama].
  Preserve its projection, camera, silhouettes, spatial relationships, and layout.
- Original source / appearance references: [identify actual references, or omit].
  Preserve visible forms, materials, gloss, colors, and pattern presence or absence.
  Use the guide for spherical projection; do not copy a source photograph's framing.
  A proxy simplification or placeholder surface is not a requested design change.

Scene and appearance:
[Brief subject, materials, lighting, and visual style.]

Required structure and inventory:
[Object IDs or unambiguous descriptions, physical counts, relative locations,
 required openings, intended curved surfaces, and retain/remove instructions.]

Unseen regions:
[Continue supported materials and forms conservatively; do not introduce new
 patterns, decor, or major objects, or redesign already visible regions.]

Spherical continuity:
Use one fixed camera center. Cover all directions, including the complete
ceiling/sky and floor/ground. The left and right edges meet at the back of the
same scene: continue architecture, objects, texture, and lighting across that
boundary. Preserve plausible pole regions without holes or artificial patches.

Projection constraint:
This is a full equirectangular sphere, not a wide-angle photograph, fisheye,
stitched collage, or cropped panorama. Preserve the base's spherical distortion.
Naturally straight architectural edges should become straight when viewed in
normal perspective; they need not be straight in the raw equirectangular image.

Retain surfaces without confirmed regular patterns without adding seams, grids,
checker colors, or decorative bands. Preserve gloss and natural material variation.
Change appearance only within these constraints. Do not add duplicate doors,
windows, furniture, people, or other physical instances beyond the inventory.
```

## Regular surface-pattern constraint

Include this square-lattice block only for a source-confirmed or explicitly requested square-tile floor. Adapt it to the actual pattern for other surfaces; omit it entirely for unpatterned or uncertain surfaces. Never infer a pattern from this template:

```text
Surface topology is structural, not decorative. Preserve the supplied floor's
single world-space Cartesian lattice, constant tile dimensions, orientation,
and phase. Change only material grain, color variation, and surface treatment
inside that layout. Do not replace it with camera-centered rings, wedges,
spirals, or a new grid per panorama sector. Preserve the mathematical spherical
projection of the guide; do not make joints artificially straight in the raw
2:1 image. In a normal nadir perspective, the flat square-tile floor must read
as a consistent square lattice. In oblique views, joints remain straight with
ordinary perspective foreshortening.
```

Do not call this block a hard geometric lock. For any regular pattern in this workflow, require
world-space material rendering and keep the final protected surface out of
unconstrained image editing. Read references/surface-lock.md. Ask for flat albedo
patches, not a perspective painting of the complete floor, when generating
material for deterministic projection.

## Local repair template

```text
Edit the current panorama, preserving its projection and camera.
Repair only [specific defect] around [angular direction / visible landmark / mask].
Preserve [explicit nearby structure and object identity]. Keep unaffected scene
content and the required inventory unchanged. Continue materials and lighting
across the repaired area. Return the complete panorama without reframing.
```

Use an actual mask only when supported. Neither a textual restriction nor a supplied mask proves exact preservation: some tools treat masks as guidance, not pixel-exact boundaries. Check the live tool semantics and inspect the entire output for unintended changes. For global structural drift, return to the approved guide rather than repeatedly treating it as a local surface defect.

## Provenance and output contract

Save the authored request, actual source references/hashes, tool/model identifier if exposed, requested settings, and result metadata if returned. Do not record guessed seeds, hidden tool prompts, or nonexistent input-fidelity controls.

Preserve the untouched result under a versioned name. Verify dimensions and decoded image bytes. Convert a supported non-PNG result to PNG only without silently altering content or aspect ratio, then inspect that exact PNG. Record a conversion if it occurred. Distinguish native generation from upscaling.

If a tool exposes only a finished image in the conversation and disallows further processing in the same turn, do not claim to have run the checker on it. A native image output may be useful, but it remains unverified by this workflow until its bytes are available and actually checked.
