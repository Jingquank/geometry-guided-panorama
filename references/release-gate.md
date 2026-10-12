# Release gate (pipeline version 3)

Use references/execution-contract.md for the current complete schema and commands.
The older presence-and-hash gate is superseded.

Run execution_guard.py BEFORE image generation. It validates declared capabilities,
scene route, surface assessments, the reviewed structural base, and the planned last
operation. A checkerboard lobby cannot use direct_simple or an AI-last verified route.
A passed report does not intercept an external image call; actual orchestration must
respect this check. A written skill is not an enforcement mechanism on its own.

For every regular pattern, end with surface_finish.py. Use a real world-space final
render or an aligned masked surface composite. Keep its generated finish manifest.
The tool does not render or segment the scene, and will not repair wrong input pixels.

Run check_pano.py on the exact final output, visually inspect all required views, and
complete the actual review. The checker's exit code 0 means format validity only.
Its output starts not_reviewed; running a checker does not make an image pass.

Before final delivery run release_check.py on the version-3 state. It validates:

- Matching current preflight, scene/guide, generation or render input records.
- An actual completed, hash-bound final review with no unresolved major defects.
- A deterministic surface finish for all protected patterns.
- The exact final pixels recomputed from its bound render/base/mask inputs.

The gate rejects later AI edits even when the candidate hash is refreshed, because
it recomputes the finished pixels rather than trusting only a recorded output hash.
It rejects missing/changed surface sources and reviews. It cannot prove an external
renderer ran, a mask covers every true floor pixel, or a visual judgment is honest.
A bad surface render remains bad after perfect copying; full visual QA is essential.

Do not deliver guides or controls as final art. Do not call the output verified when
the gate has not run. Do not claim unit tests demonstrate image-model quality or
that a fixed-center panorama validates a reconstruction or translated camera.
