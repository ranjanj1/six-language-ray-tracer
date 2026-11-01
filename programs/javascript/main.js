'use strict';
const fs = require('fs');

// xorshift32
let state = 42;
function nextU32() {
  let s = state;
  s = (s ^ ((s << 13) & 0xffffffff)) >>> 0;
  s = (s ^ (s >>> 17)) >>> 0;
  s = (s ^ ((s << 5) & 0xffffffff)) >>> 0;
  state = s;
  return s;
}
function random() { return nextU32() / 4294967296.0; }

const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const mul = (a, t) => [a[0] * t, a[1] * t, a[2] * t];
const vmul = (a, b) => [a[0] * b[0], a[1] * b[1], a[2] * b[2]];
const neg = (a) => [-a[0], -a[1], -a[2]];
const dot = (a, b) => (a[0] * b[0] + a[1] * b[1]) + a[2] * b[2];
const div = (v, t) => mul(v, 1 / t);
const length = (v) => Math.sqrt(dot(v, v));
const unit = (v) => div(v, length(v));
const reflect = (U, N) => sub(U, mul(N, 2 * dot(U, N)));

function randomUnitVector() {
  for (;;) {
    const x = 2 * random() - 1;
    const y = 2 * random() - 1;
    const z = 2 * random() - 1;
    const q = (x * x + y * y) + z * z;
    if (q > 1 || q <= 1e-160) continue;
    return mul([x, y, z], 1 / Math.sqrt(q));
  }
}

const spheres = [
  { c: [0, -100.5, -1], r: 100, type: 'diffuse', albedo: [0.8, 0.8, 0.0] },
  { c: [0, 0, -1.2], r: 0.5, type: 'diffuse', albedo: [0.1, 0.2, 0.5] },
  { c: [-1, 0, -1], r: 0.5, type: 'glass' },
  { c: [1, 0, -1], r: 0.5, type: 'metal', albedo: [0.8, 0.6, 0.2], fuzz: 0.3 },
];

function trace(O, D, depth) {
  if (depth <= 0) return [0, 0, 0];
  let closest = Infinity, hit = null;
  for (const s of spheres) {
    const oc = sub(s.c, O);
    const a = dot(D, D);
    const h = dot(D, oc);
    const c = dot(oc, oc) - s.r * s.r;
    const disc = h * h - a * c;
    if (disc < 0) continue;
    const sq = Math.sqrt(disc);
    let t = (h - sq) / a;
    if (!(t > 0.001 && t < closest)) {
      t = (h + sq) / a;
      if (!(t > 0.001 && t < closest)) continue;
    }
    closest = t; hit = s;
  }
  if (!hit) {
    const U = unit(D);
    const a = 0.5 * (U[1] + 1);
    return add(mul([1, 1, 1], 1 - a), mul([0.5, 0.7, 1], a));
  }
  const P = add(O, mul(D, closest));
  const outward = div(sub(P, hit.c), hit.r);
  const front = dot(D, outward) < 0;
  const N = front ? outward : neg(outward);
  let dir, att;
  if (hit.type === 'diffuse') {
    dir = add(N, randomUnitVector());
    if (Math.abs(dir[0]) < 1e-8 && Math.abs(dir[1]) < 1e-8 && Math.abs(dir[2]) < 1e-8) dir = N;
    att = hit.albedo;
  } else if (hit.type === 'metal') {
    const U = unit(D);
    dir = add(reflect(U, N), mul(randomUnitVector(), hit.fuzz));
    if (dot(dir, N) <= 0) return [0, 0, 0];
    att = hit.albedo;
  } else {
    att = [1, 1, 1];
    const eta = front ? 1 / 1.5 : 1.5;
    const U = unit(D);
    const cosine = Math.min(dot(neg(U), N), 1);
    const sine = Math.sqrt(1 - cosine * cosine);
    if (eta * sine > 1) {
      dir = reflect(U, N);
    } else {
      let r0 = (1 - eta) / (1 + eta);
      r0 = r0 * r0;
      const x = 1 - cosine;
      const x2 = x * x;
      const x5 = (x2 * x2) * x;
      const R = r0 + (1 - r0) * x5;
      const u = random();
      if (R > u) {
        dir = reflect(U, N);
      } else {
        const perp = mul(add(U, mul(N, cosine)), eta);
        const par = mul(N, -Math.sqrt(Math.abs(1 - dot(perp, perp))));
        dir = add(perp, par);
      }
    }
  }
  return vmul(att, trace(P, dir, depth - 1));
}

const W = 400, H = 225, SAMPLES = 200, DEPTH = 10;
const origin = [0, 0, 0];
const vu = [2 * (W / H), 0, 0];
const vv = [0, -2, 0];
const du = div(vu, W), dv = div(vv, H);
const upperLeft = sub(sub([0, 0, -1], mul(vu, 0.5)), mul(vv, 0.5));
const pixel00 = add(upperLeft, mul(add(du, dv), 0.5));

const out = ['P3', `${W} ${H}`, '255'];
const enc = (v) => Math.floor(256 * Math.min(0.999, Math.max(0, Math.sqrt(Math.max(0, v / SAMPLES)))));
for (let j = 0; j < H; j++) {
  for (let i = 0; i < W; i++) {
    const center = add(add(pixel00, mul(du, i)), mul(dv, j));
    let sum = [0, 0, 0];
    for (let s = 0; s < SAMPLES; s++) {
      const ox = random() - 0.5;
      const oy = random() - 0.5;
      const sp = add(add(center, mul(du, ox)), mul(dv, oy));
      sum = add(sum, trace(origin, sub(sp, origin), DEPTH));
    }
    out.push(`${enc(sum[0])} ${enc(sum[1])} ${enc(sum[2])}`);
  }
}
fs.writeFileSync('out.ppm', out.join('\n') + '\n');
