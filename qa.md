# Panorama acceptance and repair

## Separate three claims

1. **File validity:** decoded, opaque PNG with width exactly twice height.
2. **Fixed-center visual quality:** actual perspective reprojections show plausible geometry, correct inventory, and continuous coverage/seam/poles.
3. **3D or downstream validity:** separate validation by a named reconstruction/viewer pipeline. Neither of the first two claims establishes this.

Do not confuse script exit code 0 with visual approval. Do not call a 2:1 photograph an equirectangular panorama merely because the checker can sample it as one.

## Required views

The checker produces square 90-degree perspective views at eight horizontal headings spaced 45 degrees apart, plus zenith and nadir, and eight additional matching headings pitched down 45 degrees. Adjacent horizontal views overlap. `back-seam.png` looks across both horizontal edges with periodic interpolation.

Inspect the montage for overall defects and open all 18 individual views for approval. `floor-checks.jpg` isolates nadir and the eight oblique floor views. For possible geometry drift, inspect paired `compare-*.png` images when a guide/source comparison is available. These are visual comparisons, not automated feature matches. If a defect is too small to judge at the current check resolution, increase `--view-size` up to the source's useful detail; do not infer missing detail from an enlarged preview.

| Check | Acceptance evidence |
| --- | --- |
| Geometry | Intended straight edges stay straight in ordinary perspective. Intended curves remain curved. Floor, walls, terrain, and contact relationships fit the target scene. |
| Surface pattern | In perpendicular nadir, intended regular square tiles have straight joints, constant scale, one rotation/phase, and no rings or wedges. In oblique perspective, allow foreshortening while preserving straight joints. Compare across overlapping views; preserve deliberately curved patterns. |
| Inventory | Each required physical object occurs at the requested location/count. Parts and overlapping views do not count as extra objects. Legitimate reflections and intended repetitions are distinguished from hallucinated duplicates. |
| Coverage | Front, sides, back, corners, sky/ceiling, and ground are complete. No unrelated pasted sectors, mirrored completion, broken silhouettes, or textureless repair blocks. Naturally blank walls or sky are not defects by themselves. |
| Seam | Crossing the back boundary preserves structure, object identity, color, lighting, texture scale, and brushwork. |
| Poles | Zenith/nadir contain plausible content, without holes, black blocks, pinwheels, unexplained stretching, or a solid-color concealment patch. Inspect in perspective, not only in raw polar rows. |
| Reference fidelity | Subject, style, and required layout are preserved. Unseen content is documented as plausible completion. |

These checks establish visible plausibility, not a proof of a unique consistent 3D scene. Do not use line-straightness heuristics to reject intentionally curved architecture or deliberately nonrealistic art styles.

## Source fidelity before geometric approval

Compare the original reference directly with a corresponding perspective view of
the guide and final candidate. Do not use only candidate-versus-guide comparisons:
an invented scene spec can make a wrong guide and a wrong final image agree.

In `reference_fidelity` and `surface_pattern` evidence, record whether the source
actually supports the output's pattern and whether its absence was preserved. For
unpatterned surfaces, still inspect nadir and oblique views for invented joints,
checker colors, bands, or substituted materials; a square grid is not a universal
success criterion. Preserve the original surface finish, including visible gloss.

Treat unsupported surface patterns and unrequested redesign of visible architecture
or distinctive objects as major defects. Straight joints, a successful deterministic
finish, and a palette match cannot excuse them. Do not downgrade such a defect to
an accepted stylistic simplification or relabel visible-area redesign as unseen-area
completion. Correct the source assumptions and guide, then regenerate affected
artifacts and repeat review.

## Numeric diagnostics

`diagnostics.json` includes actual dimensions, format, opacity, SHA-256, and a latitude-weighted seam difference compared with nearby horizontal differences. The cosine latitude weight accounts for spherical area when summarizing a full equirectangular image.

Seam numbers are screening signals, not acceptance thresholds. First and last pixel centers are neighboring directions, not the exact same direction. A real object edge can produce a large boundary difference; matching edge pixels can coexist with a visible seam. No whole-image pixel-similarity threshold establishes structure preservation after a style change.

## Review records and release gate

`visual-review.json` begins with `status: not_reviewed`. Fill it only after inspection:

```json
{
  "candidate_sha256": "use the exact hash written by the checker",
  "status": "passed",
  "reviewer": "assistant visual inspection",
  "review_version": "2-floor-topology",
  "reviewed_views": ["front", "front-right", "right", "back-right", "back-seam", "back-left", "left", "front-left", "zenith", "nadir", "floor-front", "floor-front-right", "floor-right", "floor-back-right", "floor-back-seam", "floor-back-left", "floor-left", "floor-front-left"],
  "checks": {
    "geometry": {
      "status": "pass",
      "evidence": "Describe the observed geometry, not a generic claim of compliance.",
      "views": ["front", "right", "back-seam"]
    }
  },
  "defects": [],
  "assumptions": ["Describe any unobserved-region completion."]
}
```

This excerpt shows only one check. Retain and complete all seven entries created by the checker. Never paste this example as evidence of an inspection. For `surface_pattern`, cite nadir and at least one `floor-*` view; explain why a pattern check is not applicable when the scene truly has no regular surface. Mark irrelevant reference comparison as a justified pass against the written brief; do not omit the check.

Use defects with fields such as `id`, `severity`, `status`, `views`, `description`, and `repair_action`. Severity: critical for unusable projection/file or major missing coverage; major for obvious geometry, required-count, or seam failures; minor for limited cosmetic issues that do not violate the brief. Minor issues must be recorded, not hidden. A candidate with unresolved critical/major defects cannot pass.

Re-running checks on changed bytes invalidates old approval; the checker archives a stale review. It preserves a same-hash, same-schema review rather than deleting recorded work; an old schema is archived and reset to force the new surface checks. Use a new candidate directory for each edit to avoid mixing old preview files with new diagnostics. `verify_review.py` checks the file again, hash binding, required view/check evidence, and unresolved defects. It cannot prove that the reviewer actually saw the images or judged them correctly.

## Seam-aware repair

When the image editor supports a reliable local edit:

```bash
python3 "$SKILL_DIR/scripts/roll_pano.py" "$WORK/current.png" \
  "$WORK/rolled.png" --columns HALF_WIDTH
```

Replace `HALF_WIDTH` with the actual integer width divided by two. Positive values roll right. The old back boundary moves to the middle of the image; front moves to the new boundary. Describe the new reference orientation in the edit request and keep the rest of the panorama fixed.

After the edit, verify that dimensions and projection were preserved. Roll back by the exact negative column count, only if the width is unchanged. A changed size requires an explicitly recomputed mapping; do not apply the old pixel offset blindly. Preserve the raw edited result and inspect the complete restored panorama, including its newly joined regions. `roll_pano.py` changes pixel placement without resampling but does not promise to preserve every metadata block or provenance signature.

Do not independently repaint six cube faces and assume they will agree at shared edges. A pole repair through a perspective view requires a defined spherical reprojection/compositing method and overlap checks; the bundled checker exports inspection views, not an inverse paint-and-stitch system.


## Wrapped-floor failure and release

Reproduce the complaint by sampling the original PNG locally before attributing
it to a downstream system. A mathematical checker control distinguishes source
failure from viewer mapping/camera-center errors; reconstructed 3D introduces
another stage that must be tested separately. See references/surface-lock.md.
The controls themselves are diagnostics, never repaired final art.

Run release_check.py using references/release-gate.md before delivering verified
artwork. A format-valid candidate with ring-shaped tiles must fail surface-pattern
QA. No generic auto-pass thresholds are provided for line curvature: material
edges, strong shadows, reflections and intentionally curved motifs can confound
edge detectors. Automated geometry heuristics can flag reviews, not replace them.


## Version-3 final-pixel verification

Run execution_guard.py before generating, then surface_finish.py after any AI
appearance stage for regular patterns. release_check.py now requires that finish
and recomputes the expected final RGB image. A geometry guide hash and a passing
manual review alone no longer satisfy the patterned-surface release route.
This comparison detects post-finish edits, not bad rendering or dishonest reviews.
Use references/execution-contract.md; do not bypass full visual QA.
