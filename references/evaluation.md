# Maintenance and evaluation

## Scope of the supplied implementation

The original request contained the Chinese workflow text but did not include its referenced `geometry.md`, `refinement.md`, `render_guide.py`, or `check_pano.py`. This package provides newly written English guidance and a new reference implementation. It is not an audit of those unseen files. Existing scene scripts may need adaptation to the new `build_scene() -> Scene` API.

The bundled renderer is intentionally a lightweight geometry guide, not a quality-equivalent replacement for an unknown original renderer. The original renderer's performance cannot be inferred from this one.

## Automated regression tests

Run after installation or code changes, not on every scene:

```bash
python3 "$SKILL_DIR/scripts/self_test.py"
python3 "$SKILL_DIR/scripts/floor_self_test.py"
python3 "$SKILL_DIR/scripts/execution_self_test.py"
```

The current run summary is `references/validation-results-v3.json`; current logs use `test-output-v3-*.txt`. Earlier logs and summaries are historical, not this revision's execution evidence.

The current revision reruns the original 11 and floor 14 tests and adds 20 execution/final-pixel tests (45 total). It tests code, not AI quality. The old positive record-only fixture now uses an explicitly unpatterned surface; a patterned candidate without a finish must fail.

Tests cover Cartesian floor mapping, affine nadir coordinates, procedural round trips, rotated tile clipping, periodic textures, protected-pixel compositing, mask provenance, schema invalidation, release gating, coordinate orientation, perspective resampling, wraparound, invalid aspect ratio, opacity rejection, nonautomatic approval, hash invalidation, multipart identity, compiler caching, deterministic rendering, and basic C++/Python interoperability. These do not test AI refinement or prove final visual quality.

## End-to-end quality benchmark

Use paired briefs with the same actual reference inputs, generator/tool version, supported settings, and evaluation rules. Compare the old and revised workflow only when the old implementation is available. Use at least three independent runs per brief as a practical initial sample, not as proof of statistical significance. Keep failed runs in the denominator.

Include these cases:

| Case | Main failure target |
| --- | --- |
| Glossy checkerboard lobby | Square lattice in nadir; straight joints in oblique views; distinguish reflection edges from joints. |
| Deliberately circular floor mosaic | Preserve intended rings; do not apply the Cartesian rule blindly. |
| Old visually plausible 2:1 image with warped floor | Must fail manual surface QA even when format checks pass. |
| Rectangular room with one door, one cabinet, and an object crossing the back seam | Counts, planar geometry, seam identity. |
| Circular gallery or arched courtyard | Accidental straightening of intended curvature. |
| Street with aligned buildings and a road junction | Orientation and perspective drift. |
| Terrain with a sloping horizon and foreground rocks/trees | Imposed room geometry or floating objects. |
| Approved panorama with a material/style-only edit | Unnecessary reconstruction and layout regression. |
| Same-layout local object removal | Unintended global edits. |
| Dense foliage, glass, mirrors, or ornate architecture | Limits of proxy geometry and renderer capability. |
| Missing output-byte access, wrong aspect ratio, or missing compiler | Honest blocked/unverified routing. |

Record first-pass acceptance, acceptance within the allowed repair budget, critical/major defect count by class, object-count agreement, seam/pole review, and reference fidelity. Use a consistent reviewer rubric and preferably blinded comparisons. Do not turn aesthetic scores into factual claims of geometric recovery.

Measure elapsed time by stage, output dimensions, triangle count, sample count, generator calls, compiler cache state, and known cost. Report median and tail behavior with sample size; separate compilation warm-up from cached rendering and AI generation latency. Do not predict universal runtime from a single small example.

## Design references

The camera and inspection math follow ordinary spherical ray mapping, with this package's explicitly chosen axes. Primary references checked while auditing:

- Physically Based Rendering, 4th edition, Spherical Camera: https://pbr-book.org/4ed/Cameras_and_Film/Spherical_Camera
- OpenAI image prompting guide: https://developers.openai.com/api/docs/guides/image-prompting
- OpenAI high-input-fidelity cookbook (capabilities are model-specific; consult the live contract): https://developers.openai.com/cookbook/examples/generate_images_with_high_input_fidelity.md
- OpenAI Images in ChatGPT help: https://help.openai.com/en/articles/11084440-images-in-chatgpt
- Original 3D Gaussian Splatting project: https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/

The supplied text's identifier `JST2` could not be matched confidently to a panorama-reconstruction system. The English workflow therefore uses a generic downstream-reconstruction limitation, rather than inventing product-specific behavior. Preserve a specific identifier only after its intended system is established.


## Surface-lock references checked for this revision

- PBRT planar texture mapping: https://pbr-book.org/4ed/Textures_and_Materials/Texture_Coordinate_Generation
- Paul Bourke, spherical/perspective reprojection: https://paulbourke.net/panorama/sphere2persp/
- Paul Bourke, cube-face pole editing and edge continuity: https://paulbourke.net/panorama/sphericalpano/
- OpenAI image editing mask limitations: https://developers.openai.com/api/docs/guides/image-generation

The revised implementation was tested locally, but no new AI-refined hotel
panorama or downstream reconstruction was executed. Passing unit tests does not
establish an AI success rate or a universal runtime advantage. The visible
checker control tests the projection path, not final-art material quality.
