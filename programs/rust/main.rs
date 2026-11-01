use std::fmt::Write as FW;
use std::io::Write;
use std::ops::{Add, Mul, Neg, Sub};

#[derive(Clone, Copy)]
struct V(f64, f64, f64);
impl Add for V { type Output = V; fn add(self, o: V) -> V { V(self.0 + o.0, self.1 + o.1, self.2 + o.2) } }
impl Sub for V { type Output = V; fn sub(self, o: V) -> V { V(self.0 - o.0, self.1 - o.1, self.2 - o.2) } }
impl Mul<f64> for V { type Output = V; fn mul(self, t: f64) -> V { V(self.0 * t, self.1 * t, self.2 * t) } }
impl Mul<V> for V { type Output = V; fn mul(self, o: V) -> V { V(self.0 * o.0, self.1 * o.1, self.2 * o.2) } }
impl Neg for V { type Output = V; fn neg(self) -> V { V(-self.0, -self.1, -self.2) } }

fn dot(a: V, b: V) -> f64 { (a.0 * b.0 + a.1 * b.1) + a.2 * b.2 }
fn div(v: V, t: f64) -> V { v * (1.0 / t) }
fn length(v: V) -> f64 { dot(v, v).sqrt() }
fn unit(v: V) -> V { div(v, length(v)) }
fn reflect(u: V, n: V) -> V { u - n * (2.0 * dot(u, n)) }

struct Rng(u32);
impl Rng {
    fn next_u32(&mut self) -> u32 {
        let mut s = self.0;
        s ^= s << 13;
        s ^= s >> 17;
        s ^= s << 5;
        self.0 = s;
        s
    }
    fn random(&mut self) -> f64 { self.next_u32() as f64 / 4294967296.0 }
    fn unit_vector(&mut self) -> V {
        loop {
            let x = 2.0 * self.random() - 1.0;
            let y = 2.0 * self.random() - 1.0;
            let z = 2.0 * self.random() - 1.0;
            let q = (x * x + y * y) + z * z;
            if q > 1.0 || q <= 1e-160 { continue; }
            return V(x, y, z) * (1.0 / q.sqrt());
        }
    }
}

#[derive(Clone, Copy)]
enum Mat { Diffuse(V), Metal(V, f64), Glass }
struct Sphere { c: V, r: f64, m: Mat }

struct Hit { p: V, n: V, front: bool, m: Mat }

fn hit_world(world: &[Sphere], o: V, d: V) -> Option<Hit> {
    let mut closest = f64::INFINITY;
    let mut res: Option<Hit> = None;
    for s in world {
        let oc = s.c - o;
        let a = dot(d, d);
        let h = dot(d, oc);
        let c = dot(oc, oc) - s.r * s.r;
        let disc = h * h - a * c;
        if disc < 0.0 { continue; }
        let sq = disc.sqrt();
        for t in [(h - sq) / a, (h + sq) / a] {
            if 0.001 < t && t < closest {
                closest = t;
                let p = o + d * t;
                let outward = div(p - s.c, s.r);
                let front = dot(d, outward) < 0.0;
                let n = if front { outward } else { -outward };
                res = Some(Hit { p, n, front, m: s.m });
            }
        }
    }
    res
}

fn trace(world: &[Sphere], rng: &mut Rng, o: V, d: V, depth: i32) -> V {
    if depth <= 0 { return V(0.0, 0.0, 0.0); }
    let h = match hit_world(world, o, d) {
        None => {
            let u = unit(d);
            let a = 0.5 * (u.1 + 1.0);
            return V(1.0, 1.0, 1.0) * (1.0 - a) + V(0.5, 0.7, 1.0) * a;
        }
        Some(h) => h,
    };
    let (att, dir) = match h.m {
        Mat::Diffuse(alb) => {
            let mut dir = h.n + rng.unit_vector();
            if dir.0.abs() < 1e-8 && dir.1.abs() < 1e-8 && dir.2.abs() < 1e-8 { dir = h.n; }
            (alb, dir)
        }
        Mat::Metal(alb, fuzz) => {
            let u = unit(d);
            let dir = reflect(u, h.n) + rng.unit_vector() * fuzz;
            if dot(dir, h.n) <= 0.0 { return V(0.0, 0.0, 0.0); }
            (alb, dir)
        }
        Mat::Glass => {
            let eta = if h.front { 1.0 / 1.5 } else { 1.5 };
            let u = unit(d);
            let cosine = dot(-u, h.n).min(1.0);
            let sine = (1.0 - cosine * cosine).sqrt();
            let dir = if eta * sine > 1.0 {
                reflect(u, h.n)
            } else {
                let mut r0 = (1.0 - eta) / (1.0 + eta);
                r0 = r0 * r0;
                let x = 1.0 - cosine;
                let x2 = x * x;
                let x5 = (x2 * x2) * x;
                let r = r0 + (1.0 - r0) * x5;
                let uu = rng.random();
                if r > uu {
                    reflect(u, h.n)
                } else {
                    let perp = (u + h.n * cosine) * eta;
                    let par = h.n * (-(1.0 - dot(perp, perp)).abs().sqrt());
                    perp + par
                }
            };
            (V(1.0, 1.0, 1.0), dir)
        }
    };
    att * trace(world, rng, h.p, dir, depth - 1)
}

fn main() {
    let world = [
        Sphere { c: V(0.0, -100.5, -1.0), r: 100.0, m: Mat::Diffuse(V(0.8, 0.8, 0.0)) },
        Sphere { c: V(0.0, 0.0, -1.2), r: 0.5, m: Mat::Diffuse(V(0.1, 0.2, 0.5)) },
        Sphere { c: V(-1.0, 0.0, -1.0), r: 0.5, m: Mat::Glass },
        Sphere { c: V(1.0, 0.0, -1.0), r: 0.5, m: Mat::Metal(V(0.8, 0.6, 0.2), 0.3) },
    ];
    let (w, h, spp, depth) = (400usize, 225usize, 200usize, 10);
    let (wf, hf) = (w as f64, h as f64);
    let vu = V(2.0 * (wf / hf), 0.0, 0.0);
    let vv = V(0.0, -2.0, 0.0);
    let du = div(vu, wf);
    let dv = div(vv, hf);
    let upper_left = (V(0.0, 0.0, -1.0) - vu * 0.5) - vv * 0.5;
    let pixel00 = upper_left + (du + dv) * 0.5;
    let origin = V(0.0, 0.0, 0.0);
    let mut rng = Rng(42);
    let mut out = String::new();
    write!(out, "P3\n{} {}\n255\n", w, h).unwrap();
    for j in 0..h {
        for i in 0..w {
            let center = (pixel00 + du * (i as f64)) + dv * (j as f64);
            let mut sum = V(0.0, 0.0, 0.0);
            for _ in 0..spp {
                let ox = rng.random() - 0.5;
                let oy = rng.random() - 0.5;
                let sp = (center + du * ox) + dv * oy;
                let c = trace(&world, &mut rng, origin, sp - origin, depth);
                sum = sum + c;
            }
            let enc = |s: f64| -> i32 {
                let lin = s / 200.0;
                let g = lin.max(0.0).sqrt();
                (256.0 * g.max(0.0).min(0.999)).floor() as i32
            };
            writeln!(out, "{} {} {}", enc(sum.0), enc(sum.1), enc(sum.2)).unwrap();
        }
    }
    std::fs::File::create("out.ppm").unwrap().write_all(out.as_bytes()).unwrap();
}
