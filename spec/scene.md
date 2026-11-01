# Fixed scene, version 1

Units are arbitrary. Right-handed coordinates; y points up. All radii positive.
Test spheres in exactly this order; there is no acceleration structure:

| Order | Center | Radius | Material |
|---|---|---|---|
| 0 | (0,-100.5,-1) | 100 | diffuse albedo (0.8,0.8,0.0) |
| 1 | (0,0,-1.2) | 0.5 | diffuse albedo (0.1,0.2,0.5) |
| 2 | (-1,0,-1) | 0.5 | glass index 1.5 |
| 3 | (1,0,-1) | 0.5 | metal albedo (0.8,0.6,0.2), fuzz 0.3 |

Camera origin (0,0,0), looking along -z. No lens blur, motion, exposure,
lights, textures, hollow glass shell, or procedural scene generation.
Image width W=400, height H=225. Viewport height=2, width=2*(W/H).
Compute viewport_u=(2*(W/H),0,0), viewport_v=(0,-2,0),
du=viewport_u/W, dv=viewport_v/H, using vector division as in spec.md.
upper_left=(((0,0,-1)-viewport_u*0.5)-viewport_v*0.5).
pixel00=upper_left+(du+dv)*0.5.
For row j, column i: center=(pixel00+du*i)+dv*j.
Draw ox=random()-0.5, then oy=random()-0.5.
sample_point=(center+du*ox)+dv*oy. Ray origin is camera origin;
direction is sample_point-origin, without normalization.
