# Shared prompt (draft v0, shown on screen in the film)

Only `{LANGUAGE}` and `{BUILD_AND_RUN}` change between sessions. Nothing else.

---

Write a ray tracer in {LANGUAGE}.

Follow the algorithm in the attached `spec.md` (based on "Ray Tracing in One Weekend"): spheres with diffuse, metal
and glass materials, a fixed camera, the scene described in `scene.md`, and the random number generator described in
`rng.md` with seed 42.

Requirements:
- Image size 400 x 225, 200 samples per pixel, max bounce depth 10.
- Write the image to `out.ppm` in the PPM (P3) format described in `spec.md`.
- Single file, standard library only, no third-party packages.
- It must build and run with: {BUILD_AND_RUN}

When it runs and writes `out.ppm`, stop and tell me.

---

Notes (not part of the prompt):
- Attach the same four files in every session: `spec.md`, `scene.md`, `rng.md`, `reference.ppm`.
- Do not mention speed, optimization or performance anywhere in the prompt.
- Repair rounds (same wording for every language): "It did not build: <error text>." or "The image does not match the
  reference (first differing pixel at row R, column C)."
- Size and sample count are placeholders; the feasibility test decides the final values.
