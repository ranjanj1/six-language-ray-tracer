package main

import (
	"bufio"
	"fmt"
	"math"
	"os"
)

// xorshift32 RNG
var rs uint32 = 42

func nextU32() uint32 {
	rs ^= rs << 13
	rs ^= rs >> 17
	rs ^= rs << 5
	return rs
}

func random() float64 { return float64(nextU32()) / 4294967296.0 }

// float64() conversions prevent fused multiply-add on arm64.
type V struct{ x, y, z float64 }

func add(a, b V) V       { return V{a.x + b.x, a.y + b.y, a.z + b.z} }
func sub(a, b V) V       { return V{a.x - b.x, a.y - b.y, a.z - b.z} }
func mul(a V, t float64) V {
	return V{float64(a.x * t), float64(a.y * t), float64(a.z * t)}
}
func hadamard(a, b V) V {
	return V{float64(a.x * b.x), float64(a.y * b.y), float64(a.z * b.z)}
}
func neg(a V) V { return V{-a.x, -a.y, -a.z} }
func dot(a, b V) float64 {
	return float64(float64(a.x*b.x)+float64(a.y*b.y)) + float64(a.z*b.z)
}
func div(a V, t float64) V { return mul(a, 1/t) }
func length(a V) float64   { return math.Sqrt(dot(a, a)) }
func unit(a V) V           { return div(a, length(a)) }

func randomUnit() V {
	for {
		x := 2*random() - 1
		y := 2*random() - 1
		z := 2*random() - 1
		q := float64(float64(x*x)+float64(y*y)) + float64(z*z)
		if q > 1 || q <= 1e-160 {
			continue
		}
		return mul(V{x, y, z}, 1/math.Sqrt(q))
	}
}

const (
	Diffuse = iota
	Metal
	Glass
)

type Sphere struct {
	c      V
	r      float64
	mat    int
	albedo V
	fuzz   float64
}

var scene = []Sphere{
	{V{0, -100.5, -1}, 100, Diffuse, V{0.8, 0.8, 0.0}, 0},
	{V{0, 0, -1.2}, 0.5, Diffuse, V{0.1, 0.2, 0.5}, 0},
	{V{-1, 0, -1}, 0.5, Glass, V{1, 1, 1}, 0},
	{V{1, 0, -1}, 0.5, Metal, V{0.8, 0.6, 0.2}, 0.3},
}

func trace(o, d V, depth int) V {
	if depth <= 0 {
		return V{}
	}
	closest := math.Inf(1)
	hit := -1
	var P, N V
	var front bool
	for idx := range scene {
		s := &scene[idx]
		oc := sub(s.c, o)
		a := dot(d, d)
		h := dot(d, oc)
		c := dot(oc, oc) - float64(s.r*s.r)
		disc := float64(h*h) - float64(a*c)
		if disc < 0 {
			continue
		}
		sq := math.Sqrt(disc)
		for k := 0; k < 2; k++ {
			var t float64
			if k == 0 {
				t = (h - sq) / a
			} else {
				t = (h + sq) / a
			}
			if 0.001 < t && t < closest {
				closest = t
				hit = idx
				P = add(o, mul(d, t))
				out := div(sub(P, s.c), s.r)
				front = dot(d, out) < 0
				if front {
					N = out
				} else {
					N = neg(out)
				}
			}
		}
	}
	if hit < 0 {
		u := unit(d)
		a := 0.5 * (u.y + 1)
		return add(mul(V{1, 1, 1}, 1-a), mul(V{0.5, 0.7, 1}, a))
	}
	s := &scene[hit]
	var dir V
	switch s.mat {
	case Diffuse:
		dir = add(N, randomUnit())
		if math.Abs(dir.x) < 1e-8 && math.Abs(dir.y) < 1e-8 && math.Abs(dir.z) < 1e-8 {
			dir = N
		}
	case Metal:
		u := unit(d)
		refl := sub(u, mul(N, 2*dot(u, N)))
		dir = add(refl, mul(randomUnit(), s.fuzz))
		if dot(dir, N) <= 0 {
			return V{}
		}
	case Glass:
		eta := 1.5
		if front {
			eta = 1 / 1.5
		}
		u := unit(d)
		cosine := math.Min(dot(neg(u), N), 1)
		sine := math.Sqrt(1 - float64(cosine*cosine))
		reflectDir := sub(u, mul(N, 2*dot(u, N)))
		if float64(eta*sine) > 1 {
			dir = reflectDir
		} else {
			r0 := (1 - eta) / (1 + eta)
			r0 = r0 * r0
			x := 1 - cosine
			x2 := x * x
			x5 := float64(x2*x2) * x
			R := r0 + float64((1-r0)*x5)
			uu := random()
			if R > uu {
				dir = reflectDir
			} else {
				perp := mul(add(u, mul(N, cosine)), eta)
				par := mul(N, -math.Sqrt(math.Abs(1-dot(perp, perp))))
				dir = add(perp, par)
			}
		}
	}
	return hadamard(s.albedo, trace(P, dir, depth-1))
}

func main() {
	const W, H, samples, depth = 400, 225, 200, 10
	vu := V{2 * (float64(W) / float64(H)), 0, 0}
	vv := V{0, -2, 0}
	du := div(vu, W)
	dv := div(vv, H)
	ul := sub(sub(V{0, 0, -1}, mul(vu, 0.5)), mul(vv, 0.5))
	p00 := add(ul, mul(add(du, dv), 0.5))
	origin := V{}

	f, err := os.Create("out.ppm")
	if err != nil {
		panic(err)
	}
	w := bufio.NewWriter(f)
	fmt.Fprintf(w, "P3\n%d %d\n255\n", W, H)
	enc := func(s float64) int {
		l := s / samples
		g := math.Sqrt(math.Max(0, l))
		return int(math.Floor(256 * math.Min(0.999, math.Max(0, g))))
	}
	for j := 0; j < H; j++ {
		for i := 0; i < W; i++ {
			center := add(add(p00, mul(du, float64(i))), mul(dv, float64(j)))
			var sum V
			for s := 0; s < samples; s++ {
				ox := random() - 0.5
				oy := random() - 0.5
				sp := add(add(center, mul(du, ox)), mul(dv, oy))
				sum = add(sum, trace(origin, sub(sp, origin), depth))
			}
			fmt.Fprintf(w, "%d %d %d\n", enc(sum.x), enc(sum.y), enc(sum.z))
		}
	}
	w.Flush()
	f.Close()
}
