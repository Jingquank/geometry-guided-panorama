# Repeated wrapped-floor failure: audit and correction

## Conclusion

The last image-generation turn again produced only an image candidate from a prompt and the original photograph. It did not execute the geometry/surface-render/final-review pipeline. Therefore the repeated defect is not evidence that the implemented planar mapping produced rings; that mapping was not applied to the delivered pixels.

The latest 1774 x 887 PNG was reprojected in this audit without the downstream service. Its nadir visibly has curved/radial tile bands and wedge junctions. The same checker correctly reprojects a deterministic planar control. The source asset alone is sufficient to exhibit the reported problem. Downstream behavior remains untested.

## Source identity

- File: sunlit_360_neoclassical_hotel_lobby.png
- SHA-256: 2da8b9e480de69e8f767f122860c27e99405aa172e3943d580de3c9d2dc48aa9
- Local review: FAILED, global surface-pattern defect.
- AI generation in this audit: none.
- Repaired hotel artwork in this audit: none.

## Findings in the previous package

1. The instructions already required geometry and final reprojection. They were not executed in the previous image turn. Changing the instruction file cannot by itself enforce a tool sequence.
2. The high-risk surface route still said to prefer world-space finishing while retaining a whole-panorama refinement template. This left a soft-constraint route too easy to use as final output.
3. The release checker required nonempty surface constraints and checked review/provenance records, but did not require a final surface-render artifact or compare final pixels with that artifact.
4. check_pano.py returned exit code 0 for valid PNG/aspect/opacity while intentionally leaving visual quality not_reviewed. Treating this return code as visual approval is incorrect.
5. The package contains proxy/albedo tools, not an automatic photorealistic hotel reconstruction, segmentation, or glossy material renderer. Correct calibration mathematics is not a finished hotel.

## Changes actually implemented

- Rewrite SKILL.md as an execution-first entrypoint (pipeline version 3), with failure recovery before generation.
- Add execution_guard.py: inspect the actual guide and declared host capabilities before a generation call. Reject prompt-only final operations for protected patterns.
- Make deterministic world-space finishing mandatory for regular patterns; guide-conditioned full panorama output can only be an intermediate.
- Add surface_finish.py: copy an actual reviewed full render or compose a reviewed surface/mask last. Require hash-bound current inputs, all floor review directions, and full-mask-coverage evidence. Preserve the replaced interior and unmasked base exactly, with only narrow linear-light boundary blending.
- Update release_check.py: require the finish and recompute all expected final pixels; do not just accept a refreshed output hash.
- Reject AI/image transformations after finalization unless the surface is finished and visually reviewed again.
- Explicitly distinguish blocked verified routes from authorized unverified previews when the host cannot continue after image generation.

## Tests run

45 local tests passed: 11 original, 14 floor, 20 new execution/final-pixel tests. A temporary assertion failure caused by an error-message case change was corrected before the final rerun; the final logs are included. The updated positive record-only fixture now uses an unpatterned surface. Patterned release without finalization has its own negative test.

New cases include missing guide, a terminal generation route, image-generation-last, missing deterministic finish, stale mask/review, changed final pixels even with refreshed hashes, broad feathering, and a surface explicitly labeled calibration instead of final rendering.

Synthetic fixture approvals in these tests are explicitly labeled as synthetic. They test the validator, not the visual quality of those fixture images.

## Remaining boundaries

A Markdown skill and local CLI cannot stop a direct image tool call outside the workflow. A production caller must actually enforce the preflight/finalization/release path. This package is not an authenticated remote orchestration system.

Exact pixel reconstruction proves that the final image matches its recorded inputs, not that those inputs are geometrically or aesthetically correct. A mislabeled bad render or incorrectly reviewed mask can still be wrong. Actual nadir/oblique/full-scene visual review is required, and material rendering quality must meet the brief.

No new AI-refined hotel, reference-fidelity benchmark, downstream viewer run, or 3D reconstruction test was completed here. The control image is not a repaired hotel.

## Technical references consulted

- PBRT spherical camera: https://pbr-book.org/4ed/Cameras_and_Film/Spherical_Camera
- PBRT planar texture coordinates: https://pbr-book.org/4ed/Textures_and_Materials/Texture_Coordinate_Generation

These support the projection/texture-coordinate distinction; the findings about this package come from its actual code and local tests.
