#pragma clang fp contract(off)
#pragma STDC FP_CONTRACT OFF
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <vector>

struct V { double x, y, z; };
static inline V operator+(V a, V b) { return {a.x + b.x, a.y + b.y, a.z + b.z}; }
static inline V operator-(V a, V b) { return {a.x - b.x, a.y - b.y, a.z - b.z}; }
static inline V operator-(V a) { return {-a.x, -a.y, -a.z}; }
static inline V operator*(V a, V b) { return {a.x * b.x, a.y * b.y, a.z * b.z}; }
static inline V operator*(V a, double t) { return {a.x * t, a.y * t, a.z * t}; }
static inline V operator/(V a, double t) { double r = 1 / t; return a * r; }
static inline double dot(V a, V b) { return (a.x * b.x + a.y * b.y) + a.z * b.z; }
static inline double length(V a) { return std::sqrt(dot(a, a)); }
static inline V unit(V a) { return a / length(a); }

static uint32_t S = 42;
static uint32_t next_u32() {
    S ^= (S << 13);
    S ^= (S >> 17);
    S ^= (S << 5);
    return S;
}
static double rnd() { return next_u32() / 4294967296.0; }
static V random_unit_vector() {
    for (;;) {
        double x = 2 * rnd() - 1;
        double y = 2 * rnd() - 1;
        double z = 2 * rnd() - 1;
        double q = (x * x + y * y) + z * z;
        if (q > 1 || q <= 1e-160) continue;
        return V{x, y, z} * (1 / std::sqrt(q));
    }
}

enum Kind { DIFFUSE, METAL, GLASS };
struct Sphere { V c; double r; Kind k; V albedo; double fuzz; };
static const Sphere spheres[4] = {
    {{0, -100.5, -1}, 100, DIFFUSE, {0.8, 0.8, 0.0}, 0},
    {{0, 0, -1.2}, 0.5, DIFFUSE, {0.1, 0.2, 0.5}, 0},
    {{-1, 0, -1}, 0.5, GLASS, {1, 1, 1}, 0},
    {{1, 0, -1}, 0.5, METAL, {0.8, 0.6, 0.2}, 0.3},
};

static V reflect(V u, V n) { return u - n * (2 * dot(u, n)); }

static V trace(V O, V D, int depth) {
    if (depth <= 0) return {0, 0, 0};
    double closest = std::numeric_limits<double>::infinity();
    int hit = -1;
    for (int i = 0; i < 4; i++) {
        const Sphere& s = spheres[i];
        V oc = s.c - O;
        double a = dot(D, D);
        double h = dot(D, oc);
        double c = dot(oc, oc) - s.r * s.r;
        double disc = h * h - a * c;
        if (disc < 0) continue;
        double sq = std::sqrt(disc);
        double t = (h - sq) / a;
        if (!(0.001 < t && t < closest)) {
            t = (h + sq) / a;
            if (!(0.001 < t && t < closest)) continue;
        }
        closest = t;
        hit = i;
    }
    if (hit < 0) {
        V U = unit(D);
        double a = 0.5 * (U.y + 1);
        return V{1, 1, 1} * (1 - a) + V{0.5, 0.7, 1} * a;
    }
    const Sphere& s = spheres[hit];
    V P = O + D * closest;
    V outward = (P - s.c) / s.r;
    bool front = dot(D, outward) < 0;
    V N = front ? outward : -outward;
    V dir, att = s.albedo;
    if (s.k == DIFFUSE) {
        dir = N + random_unit_vector();
        if (std::fabs(dir.x) < 1e-8 && std::fabs(dir.y) < 1e-8 && std::fabs(dir.z) < 1e-8) dir = N;
    } else if (s.k == METAL) {
        V U = unit(D);
        dir = reflect(U, N) + random_unit_vector() * s.fuzz;
        if (dot(dir, N) <= 0) return {0, 0, 0};
    } else {
        att = {1, 1, 1};
        double eta = front ? 1 / 1.5 : 1.5;
        V U = unit(D);
        double cosine = std::fmin(dot(-U, N), 1.0);
        double sine = std::sqrt(1 - cosine * cosine);
        if (eta * sine > 1) {
            dir = reflect(U, N);
        } else {
            double r0 = (1 - eta) / (1 + eta);
            r0 = r0 * r0;
            double x = 1 - cosine;
            double x2 = x * x;
            double x5 = (x2 * x2) * x;
            double R = r0 + (1 - r0) * x5;
            double u = rnd();
            if (R > u) {
                dir = reflect(U, N);
            } else {
                V perp = (U + N * cosine) * eta;
                V par = N * (-std::sqrt(std::fabs(1 - dot(perp, perp))));
                dir = perp + par;
            }
        }
    }
    return att * trace(P, dir, depth - 1);
}

int main() {
    const int W = 400, H = 225, SPP = 200, DEPTH = 10;
    V origin{0, 0, 0};
    V vu{2 * ((double)W / (double)H), 0, 0};
    V vv{0, -2, 0};
    V du = vu / (double)W, dv = vv / (double)H;
    V ul = (V{0, 0, -1} - vu * 0.5) - vv * 0.5;
    V p00 = ul + (du + dv) * 0.5;
    FILE* f = std::fopen("out.ppm", "w");
    if (!f) return 1;
    std::fprintf(f, "P3\n%d %d\n255\n", W, H);
    for (int j = 0; j < H; j++) {
        for (int i = 0; i < W; i++) {
            V sum{0, 0, 0};
            V center = (p00 + du * (double)i) + dv * (double)j;
            for (int s = 0; s < SPP; s++) {
                double ox = rnd() - 0.5;
                double oy = rnd() - 0.5;
                V sp = (center + du * ox) + dv * oy;
                sum = sum + trace(origin, sp - origin, DEPTH);
            }
            double c[3] = {sum.x, sum.y, sum.z};
            int e[3];
            for (int k = 0; k < 3; k++) {
                double lin = c[k] / 200;
                double g = std::sqrt(std::fmax(0.0, lin));
                e[k] = (int)std::floor(256 * std::fmin(0.999, std::fmax(0.0, g)));
            }
            std::fprintf(f, "%d %d %d\n", e[0], e[1], e[2]);
        }
    }
    std::fclose(f);
    return 0;
}
