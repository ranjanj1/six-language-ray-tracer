from math import sqrt, floor, inf

W, H, SAMPLES, DEPTH = 400, 225, 200, 10

state = 42


def rnd():
    global state
    s = state
    s ^= (s << 13) & 0xFFFFFFFF
    s ^= s >> 17
    s ^= (s << 5) & 0xFFFFFFFF
    state = s
    return s / 4294967296.0


def rand_unit():
    while True:
        x = 2 * rnd() - 1
        y = 2 * rnd() - 1
        z = 2 * rnd() - 1
        q = (x * x + y * y) + z * z
        if q > 1 or q <= 1e-160:
            continue
        k = 1 / sqrt(q)
        return x * k, y * k, z * k


# (cx, cy, cz, r, kind, albedo, param)  kind 0 diffuse, 1 metal, 2 glass
SPHERES = [
    (0.0, -100.5, -1.0, 100.0, 0, (0.8, 0.8, 0.0), 0.0),
    (0.0, 0.0, -1.2, 0.5, 0, (0.1, 0.2, 0.5), 0.0),
    (-1.0, 0.0, -1.0, 0.5, 2, (1.0, 1.0, 1.0), 1.5),
    (1.0, 0.0, -1.0, 0.5, 1, (0.8, 0.6, 0.2), 0.3),
]


def trace(ox, oy, oz, dx, dy, dz, depth):
    atts = []
    base = (0.0, 0.0, 0.0)
    while True:
        if depth <= 0:
            break
        closest = inf
        hit = None
        a = (dx * dx + dy * dy) + dz * dz
        for sp in SPHERES:
            cx, cy, cz, r = sp[0], sp[1], sp[2], sp[3]
            ocx, ocy, ocz = cx - ox, cy - oy, cz - oz
            h = (dx * ocx + dy * ocy) + dz * ocz
            c = ((ocx * ocx + ocy * ocy) + ocz * ocz) - r * r
            disc = h * h - a * c
            if disc < 0:
                continue
            sq = sqrt(disc)
            t = (h - sq) / a
            if not (0.001 < t < closest):
                t = (h + sq) / a
                if not (0.001 < t < closest):
                    continue
            closest = t
            hit = sp
        if hit is None:
            l = sqrt((dx * dx + dy * dy) + dz * dz)
            k = 1 / l
            uy = dy * k
            t = 0.5 * (uy + 1)
            s = 1 - t
            base = (1 * s + 0.5 * t, 1 * s + 0.7 * t, 1 * s + 1.0 * t)
            break
        cx, cy, cz, r, kind, alb, prm = hit
        t = closest
        px, py, pz = ox + dx * t, oy + dy * t, oz + dz * t
        ir = 1 / r
        nx, ny, nz = (px - cx) * ir, (py - cy) * ir, (pz - cz) * ir
        front = ((dx * nx + dy * ny) + dz * nz) < 0
        if not front:
            nx, ny, nz = -nx, -ny, -nz
        if kind == 0:
            rx, ry, rz = rand_unit()
            ndx, ndy, ndz = nx + rx, ny + ry, nz + rz
            if abs(ndx) < 1e-8 and abs(ndy) < 1e-8 and abs(ndz) < 1e-8:
                ndx, ndy, ndz = nx, ny, nz
        elif kind == 1:
            k = 1 / sqrt((dx * dx + dy * dy) + dz * dz)
            ux, uy, uz = dx * k, dy * k, dz * k
            d2 = 2 * ((ux * nx + uy * ny) + uz * nz)
            rx, ry, rz = ux - nx * d2, uy - ny * d2, uz - nz * d2
            fx, fy, fz = rand_unit()
            ndx, ndy, ndz = rx + fx * prm, ry + fy * prm, rz + fz * prm
            if ((ndx * nx + ndy * ny) + ndz * nz) <= 0:
                base = (0.0, 0.0, 0.0)
                break
        else:
            eta = 1 / 1.5 if front else 1.5
            k = 1 / sqrt((dx * dx + dy * dy) + dz * dz)
            ux, uy, uz = dx * k, dy * k, dz * k
            cosine = min(((-ux) * nx + (-uy) * ny) + (-uz) * nz, 1)
            sine = sqrt(1 - cosine * cosine)
            reflect = False
            if eta * sine > 1:
                reflect = True
            else:
                r0 = (1 - eta) / (1 + eta)
                r0 = r0 * r0
                x = 1 - cosine
                x2 = x * x
                x5 = (x2 * x2) * x
                R = r0 + (1 - r0) * x5
                u = rnd()
                if R > u:
                    reflect = True
            if reflect:
                d2 = 2 * ((ux * nx + uy * ny) + uz * nz)
                ndx, ndy, ndz = ux - nx * d2, uy - ny * d2, uz - nz * d2
            else:
                px_ = (ux + nx * cosine) * eta
                py_ = (uy + ny * cosine) * eta
                pz_ = (uz + nz * cosine) * eta
                s = -sqrt(abs(1 - ((px_ * px_ + py_ * py_) + pz_ * pz_)))
                ndx, ndy, ndz = px_ + nx * s, py_ + ny * s, pz_ + nz * s
        atts.append(alb)
        ox, oy, oz = px, py, pz
        dx, dy, dz = ndx, ndy, ndz
        depth -= 1
    # fold attenuation * Trace(...) from the innermost outward
    r, g, b = base
    for al in reversed(atts):
        r, g, b = al[0] * r, al[1] * g, al[2] * b
    return r, g, b


def main():
    vw = 2 * (W / H)
    vux, vvy = vw, -2.0
    k = 1 / W
    dux = vux * k
    k = 1 / H
    dvy = vvy * k
    ulx = 0.0 - vux * 0.5
    uly = 0.0 - vvy * 0.5
    ulz = -1.0
    p0x = ulx + (dux + 0.0) * 0.5
    p0y = uly + (0.0 + dvy) * 0.5
    p0z = ulz + (0.0 + 0.0) * 0.5

    out = ["P3", "%d %d" % (W, H), "255"]
    for j in range(H):
        for i in range(W):
            cx = (p0x + dux * i) + 0.0 * j
            cy = (p0y + 0.0 * i) + dvy * j
            cz = (p0z + 0.0 * i) + 0.0 * j
            sr = sg = sb = 0.0
            for _ in range(SAMPLES):
                ox = rnd() - 0.5
                oy = rnd() - 0.5
                sx = (cx + dux * ox) + 0.0 * oy
                sy = (cy + 0.0 * ox) + dvy * oy
                sz = (cz + 0.0 * ox) + 0.0 * oy
                r, g, b = trace(0.0, 0.0, 0.0, sx, sy, sz, DEPTH)
                sr += r
                sg += g
                sb += b
            px = []
            for s in (sr, sg, sb):
                lin = s / 200
                gm = sqrt(max(0, lin))
                px.append(str(floor(256 * min(0.999, max(0, gm)))))
            out.append(" ".join(px))
    with open("out.ppm", "w") as f:
        f.write("\n".join(out) + "\n")


main()
