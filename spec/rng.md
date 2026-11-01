# Deterministic random stream, version 1

Use xorshift32, with unsigned 32-bit state. Seed once at process/render start
with decimal 42. Do not reseed at pixels or bounces. Each next_u32 performs,
in this order (all left shifts and XOR results reduced modulo 2^32):

```
s = s XOR ((s << 13) AND 0xffffffff)
s = s XOR (s >>> 17)
s = s XOR ((s << 5) AND 0xffffffff)
return s
```

`>>>` means zero-fill right shift. In languages with signed bitwise operations,
convert the final result to unsigned. `random()` is next_u32 / 4294967296.0
in binary64, giving [0,1). No standard-library RNG is permitted.
First five outputs from seed 42: 11355432, 2836018348, 476557059,
3648046016, 3759983556.

Random unit vector: repeatedly draw x, then y, then z, each as 2*random()-1.
Let q=(x*x+y*y)+z*z. Reject when q>1 or q<=1e-160. Otherwise return
(x,y,z)*(1/sqrt(q)). Rejections consume all three draws.

Render rows top to bottom, columns left to right, samples 0 through 19.
For each sample draw horizontal jitter then vertical jitter before tracing.
At each hit: diffuse consumes a random unit vector; metal consumes a random
unit vector even when fuzz is zero; glass draws one random value only when
there is no total internal reflection. Misses and exhausted depth draw nothing.
Complete the entire recursive sample before beginning the next sample.
