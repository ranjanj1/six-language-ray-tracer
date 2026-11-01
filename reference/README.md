# Reference evidence

main.cpp is the bench reference, not a language contestant.
Build: `c++ -std=c++17 -O3 -ffp-contract=off reference/main.cpp -o reference/render`.
Compiler: Apple clang 21.0.0 (clang-2100.0.123.102), arm64-apple-darwin25.5.0.
No installs or third-party libraries. `render` writes out.ppm in its working folder.

Golden reference.ppm SHA-256:
`f1dfef5f4cfece086e1545345fe2d7b43319c37d208f018bdf54c2508a718e05 (v2, 200 spp; v1 20 spp kept in v1-20spp/)`

An independent -O0 build with contraction disabled regenerated an exactly
identical P3 raster (maximum channel difference 0). preview.png was converted
with macOS sips and visually inspected. It is for convenience; the PPM is the
comparison authority. Binary executables can be rebuilt on another machine.
