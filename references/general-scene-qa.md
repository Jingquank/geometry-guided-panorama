# General-scene inspection and repair

## Plan from evidence, not category

Every scene gets the shared panorama checks. Only activate feature constraints
supported by the source or explicit user intent; estimates remain labeled inferred.
Do not infer a rectangular room from "interior", a flat plane from "ground", or a
regular grid from a need to validate. Source geometry and material identity govern
proxy construction, including intended curves, rough terrain and irregular vegetation.

Add `inspection_plan` to scene-spec.json before preflight. Select salient features,
long edges/silhouettes, vulnerable contact boundaries and any previously reported
failure. One target may cover a coherent region; do not enumerate every leaf.
`source_evidence` must identify the source region or user instruction. For inferred
unseen content, state the assumption rather than claiming visual observation.

```json
{
  "inspection_plan": {
    "version": 1,
    "targets": [{
      "id": "ridge",
      "kind": "organic_form",
      "basis": "observed",
      "source_evidence": "Reference upper third: uneven ridge with two distinct peaks",
      "preserve": "Uneven connected silhouette and the two peaks; no flattening",
      "failure_signal": "Duplicated peak, disconnected ridge or unsupported radial bow",
      "yaw": 0,
      "pitch": 20,
      "fov": 70
    }]
  }
}
```

Kinds: straight_edge, planar_surface, curved_form, organic_form, repetition,
contact_occlusion, lighting_reflection. These select human inspection criteria,
not automatic shape classifiers. Basis: observed, user_requested, inferred.
Yaw is -180..180, pitch -90..90, square perspective FOV 20..110 degrees.
For a truly featureless sky etc., use targets: [] and a concrete no_targets_reason.
An empty list cannot excuse skipping a visible salient object or reported failure.
The validator checks schema, not whether that judgment is justified.

## Inspect the actual image

Pass `--scene-spec scene-spec.json` to check_pano.py. In addition to the 18 baseline
views it exports target-ID-a/b.png: two overlapping rotations, separated by 20% of
that target's FOV. Both come from the same camera center. They expose local warps
but do not constitute independent multiview or translated-camera evidence.

Plan coordinates must be aimed using the actual guide/candidate. Open every target
image; if the feature is clipped, outside view, pole overlap unhelpful or too small,
adjust/add targets and regenerate. A completed view list is not evidence of useful
coverage. Changing the plan invalidates the review. Update the bound scene spec,
re-review the guide and refresh preflight and any dependent finish provenance when
needed. Never relabel a late plan as having existed before the recorded image call.
For substantial new constraints discovered late, restart the affected workflow.

Complete target_checks keyed by target ID with status: pass, specific evidence,
and views containing both target-ID-a and target-ID-b. Compare source-supported
features directly with the original; compare the full object, not only one edge.
A failed/unresolved or unjudgeable salient feature prevents visual approval.
Use higher QA resolution only up to useful source detail. Do not hallucinate evidence
from upscaling. Numeric line-deviation tools may flag observed straight edges, but
no universal pixel threshold or line detector may approve arbitrary natural scenes.

All ten shared checks require evidence. surface_pattern remains relevant when
unpatterned: check no invented grids/bands, and source-matched texture/finish.
The legacy floor-* view names describe downward directions in sky/sea/terrain.
Record why a particular phenomenon is absent rather than inventing it for testing.

## Route repairs by failure

| Evidence/failure | Appropriate action |
| --- | --- |
| Source-supported straight/planar object bows | Revisit affected geometry, silhouette and surface mapping; inspect all its faces/contacts. A 2D edge warp is not a whole-object solution. |
| Intended curved/organic form changes | Preserve observed curvature, branching, connectedness and occlusion; never substitute a Cartesian template. |
| Repeated source pattern drifts | Existing deterministic surface finish, restricted to authorized pattern and real visible surface. |
| Light/shadow bends on a known planar receiver | Check receiver geometry, light/occluder relationship and compositing; do not globally straighten all light edges. |
| Fine appearance defect with stable structure | Local intermediate repair, then refinish protected surfaces and repeat full QA. |
| Source versus proxy conflict | Correct proxy; agreement between proxy and output cannot override the source. |

Deterministic object/material rendering is an escalation for salient structural
failure, not a mandate to build detailed meshes of every forest or cloud. If the
available renderer cannot preserve source quality, report the limit; do not claim
that a coarse proxy or longer prompt solved it. Do not remove lighting as a shortcut.

## Downstream reconstruction is separate

visual-review.json initializes downstream_validation.status to not_tested. A passed
or failed downstream result must record system, workflow/version/settings, evidence
and artifact location. Failure here does not rewrite a valid panorama review, but
prohibits claiming reconstruction success. If reconstruction is the user's goal,
that work remains incomplete until downstream acceptance is established.

After a downstream complaint, compare the exact delivered PNG locally first. Then,
if available, use a labeled synthetic scene with known shapes and lighting under
the same downstream settings. Compare original-center and translated-camera results.
An optional same-geometry softer-light control isolates lighting sensitivity; it is
not replacement artwork. Do not assume a particular platform's undocumented internals.
