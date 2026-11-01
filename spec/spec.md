# Language race renderer contract, version 1

This bench uses the sphere intersections, recursive radiance, Lambertian,
fuzzy metal, dielectric, sky gradient, and square-root output transfer of
Peter Shirley, Trevor David Black, and Steve Hollasch, *Ray Tracing in One
Weekend*, version 4.0.2 (2025-04-25):
https://raytracing.github.io/books/RayTracingInOneWeekend.html
See its sections on antialiasing, diffuse materials, metal, dielectrics, and
positionable camera. This contract, scene.md and rng.md fix the choices left
open by the book; these files take precedence over other book versions.

## Arithmetic

Use IEEE-754 binary64 for geometry and color, round-to-nearest ties-to-even.
No float32, fast-math, fused multiply-add, reassociation, or approximate math.
Evaluate expressions in written order; ordinary +,-,*,/ are left associative.
Vector operations are componentwise except dot(a,b)=(ax*bx+ay*by)+az*bz.
Vector division v/t means v*(1/t), with reciprocal computed first.
length(v)=sqrt(dot(v,v)); unit(v)=v/length(v).
Only sqrt, abs, min, max are needed; fifth powers use multiplication as below.
Use one thread, one stream, and no precomputed images or sample results.

## Intersection

For ray O+t*D and sphere C,r: oc=C-O; a=dot(D,D);
h=dot(D,oc); c=dot(oc,oc)-r*r; disc=h*h-a*c.
If disc<0 miss. Otherwise try (h-sqrt(disc))/a, then
(h+sqrt(disc))/a. A root is accepted only when 0.001<t<closest,
where closest starts at positive infinity for every ray and becomes each
accepted root. Equal roots never replace an earlier hit. Hit point P=O+D*t;
outward=(P-C)/r. front=dot(D,outward)<0; N=outward if front else -outward.

## Radiance

Trace(ray,depth) returns (0,0,0) immediately if depth<=0. Otherwise find
nearest hit. If no hit: U=unit(D), a=0.5*(U.y+1);
return (1,1,1)*(1-a)+(0.5,0.7,1)*a.
Every scattered ray starts exactly at P; use the root minimum above, no offset.

Diffuse: direction=N+random_unit_vector(). If all three absolute components
are <1e-8, use N. Attenuation is the albedo.

Metal: U=unit(D); reflect(U,N)=U-N*(2*dot(U,N));
direction=reflect(U,N)+random_unit_vector()*fuzz. If dot(direction,N)<=0,
return black immediately. Attenuation is the albedo.

Glass: attenuation=(1,1,1); eta=1/1.5 if front else 1.5.
U=unit(D); cosine=min(dot(-U,N),1); sine=sqrt(1-cosine*cosine).
If eta*sine>1, reflect with no random draw. Otherwise compute
r0=(1-eta)/(1+eta); r0=r0*r0; x=1-cosine;
x2=x*x; x5=(x2*x2)*x; R=r0+(1-r0)*x5.
Draw u=random(). Reflect if R>u; otherwise refract:
perp=(U+N*cosine)*eta;
parallel=N*(-sqrt(abs(1-dot(perp,perp)))); direction=perp+parallel.

For every successful scatter return attenuation * Trace(scattered,depth-1),
componentwise. Use this recursive multiplication association (or exactly
reproduce it); do not accumulate throughput with a different association.
No Russian roulette, direct light sampling, or clipping in the trace.

## Samples and file

Use scene.md and rng.md. Seed=42; W=400; H=225; samples=200; depth=10.
Each pixel starts sum=(0,0,0). Add complete sample colors in sample order.
For each component: linear=sum_component/200 (ordinary scalar division);
gamma=sqrt(max(0,linear)); encoded=floor(256*min(0.999,max(0,gamma))).
Write ASCII P3 to out.ppm, header `P3`, `400 225`, `255`, then exactly
W*H RGB integer triplets in row-major order. Whitespace and # comments may
vary; there must be no extra tokens or diagnostic text in the file.

The comparison tolerance is 1 integer code value per channel, inclusive,
for every pixel. It permits a last-bit arithmetic difference crossing a
quantization boundary. It does not excuse changed RNG order, scene or
algorithm: a divergent path may fail even with this tolerance. No aggregate
error or percentage-of-pixels exception. Indices in diagnostics are zero-based.
