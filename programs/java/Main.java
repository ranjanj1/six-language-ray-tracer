import java.io.*;

public class Main {
    static int s = 42;
    static int nextU32() {
        s ^= s << 13;
        s ^= s >>> 17;
        s ^= s << 5;
        return s;
    }
    static double random() { return (nextU32() & 0xffffffffL) / 4294967296.0; }

    record V(double x, double y, double z) {
        V add(V o) { return new V(x + o.x, y + o.y, z + o.z); }
        V sub(V o) { return new V(x - o.x, y - o.y, z - o.z); }
        V mul(double t) { return new V(x * t, y * t, z * t); }
        V mul(V o) { return new V(x * o.x, y * o.y, z * o.z); }
        V div(double t) { return mul(1 / t); }
        V neg() { return new V(-x, -y, -z); }
        static double dot(V a, V b) { return (a.x * b.x + a.y * b.y) + a.z * b.z; }
        double length() { return Math.sqrt(dot(this, this)); }
        V unit() { return div(length()); }
    }

    static V randomUnit() {
        while (true) {
            double x = 2 * random() - 1;
            double y = 2 * random() - 1;
            double z = 2 * random() - 1;
            double q = (x * x + y * y) + z * z;
            if (q > 1 || q <= 1e-160) continue;
            return new V(x, y, z).mul(1 / Math.sqrt(q));
        }
    }

    static final int DIFFUSE = 0, METAL = 1, GLASS = 2;
    record Sphere(V c, double r, int mat, V albedo, double fuzz) {}

    static final Sphere[] world = {
        new Sphere(new V(0, -100.5, -1), 100, DIFFUSE, new V(0.8, 0.8, 0.0), 0),
        new Sphere(new V(0, 0, -1.2), 0.5, DIFFUSE, new V(0.1, 0.2, 0.5), 0),
        new Sphere(new V(-1, 0, -1), 0.5, GLASS, null, 0),
        new Sphere(new V(1, 0, -1), 0.5, METAL, new V(0.8, 0.6, 0.2), 0.3),
    };

    static V trace(V O, V D, int depth) {
        if (depth <= 0) return new V(0, 0, 0);
        double closest = Double.POSITIVE_INFINITY;
        Sphere hs = null;
        double ht = 0;
        for (Sphere sp : world) {
            V oc = sp.c.sub(O);
            double a = V.dot(D, D);
            double h = V.dot(D, oc);
            double c = V.dot(oc, oc) - sp.r * sp.r;
            double disc = h * h - a * c;
            if (disc < 0) continue;
            double sq = Math.sqrt(disc);
            double t = (h - sq) / a;
            if (t > 0.001 && t < closest) { closest = t; hs = sp; ht = t; }
            t = (h + sq) / a;
            if (t > 0.001 && t < closest) { closest = t; hs = sp; ht = t; }
        }
        if (hs == null) {
            V u = D.unit();
            double a = 0.5 * (u.y() + 1);
            return new V(1, 1, 1).mul(1 - a).add(new V(0.5, 0.7, 1).mul(a));
        }
        V P = O.add(D.mul(ht));
        V outward = P.sub(hs.c).div(hs.r);
        boolean front = V.dot(D, outward) < 0;
        V N = front ? outward : outward.neg();
        V dir, att;
        switch (hs.mat) {
            case DIFFUSE -> {
                dir = N.add(randomUnit());
                if (Math.abs(dir.x()) < 1e-8 && Math.abs(dir.y()) < 1e-8 && Math.abs(dir.z()) < 1e-8) dir = N;
                att = hs.albedo;
            }
            case METAL -> {
                V U = D.unit();
                V refl = U.sub(N.mul(2 * V.dot(U, N)));
                dir = refl.add(randomUnit().mul(hs.fuzz));
                if (V.dot(dir, N) <= 0) return new V(0, 0, 0);
                att = hs.albedo;
            }
            default -> {
                att = new V(1, 1, 1);
                double eta = front ? 1.0 / 1.5 : 1.5;
                V U = D.unit();
                double cosine = Math.min(V.dot(U.neg(), N), 1);
                double sine = Math.sqrt(1 - cosine * cosine);
                if (eta * sine > 1) {
                    dir = U.sub(N.mul(2 * V.dot(U, N)));
                } else {
                    double r0 = (1 - eta) / (1 + eta);
                    r0 = r0 * r0;
                    double x = 1 - cosine;
                    double x2 = x * x;
                    double x5 = (x2 * x2) * x;
                    double R = r0 + (1 - r0) * x5;
                    double u = random();
                    if (R > u) {
                        dir = U.sub(N.mul(2 * V.dot(U, N)));
                    } else {
                        V perp = U.add(N.mul(cosine)).mul(eta);
                        V par = N.mul(-Math.sqrt(Math.abs(1 - V.dot(perp, perp))));
                        dir = perp.add(par);
                    }
                }
            }
        }
        return att.mul(trace(P, dir, depth - 1));
    }

    public static void main(String[] args) throws IOException {
        final int W = 400, H = 225, SAMPLES = 200, DEPTH = 10;
        double ratio = (double) W / H;
        V vu = new V(2 * ratio, 0, 0);
        V vv = new V(0, -2, 0);
        V du = vu.div(W), dv = vv.div(H);
        V upperLeft = new V(0, 0, -1).sub(vu.mul(0.5)).sub(vv.mul(0.5));
        V pixel00 = upperLeft.add(du.add(dv).mul(0.5));
        V origin = new V(0, 0, 0);

        StringBuilder sb = new StringBuilder();
        sb.append("P3\n").append(W).append(' ').append(H).append("\n255\n");
        for (int j = 0; j < H; j++) {
            for (int i = 0; i < W; i++) {
                V center = pixel00.add(du.mul(i)).add(dv.mul(j));
                V sum = new V(0, 0, 0);
                for (int k = 0; k < SAMPLES; k++) {
                    double ox = random() - 0.5;
                    double oy = random() - 0.5;
                    V sp = center.add(du.mul(ox)).add(dv.mul(oy));
                    sum = sum.add(trace(origin, sp.sub(origin), DEPTH));
                }
                double[] c = {sum.x() / SAMPLES, sum.y() / SAMPLES, sum.z() / SAMPLES};
                for (int m = 0; m < 3; m++) {
                    double g = Math.sqrt(Math.max(0, c[m]));
                    int e = (int) Math.floor(256 * Math.min(0.999, Math.max(0, g)));
                    sb.append(e).append(m < 2 ? ' ' : '\n');
                }
            }
        }
        try (Writer w = new BufferedWriter(new FileWriter("out.ppm"))) { w.write(sb.toString()); }
    }
}
