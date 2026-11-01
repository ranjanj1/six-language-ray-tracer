#!/usr/bin/env python3
"""Strict P3 parser; per-channel absolute tolerance = 1, inclusive."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 1

def read_ppm(path):
    tokens = re.sub(r'#[^\n]*', '', Path(path).read_text(encoding='ascii')).split()
    if len(tokens) < 4 or tokens[0] != 'P3':
        raise ValueError('expected ASCII P3 header')
    if any(re.fullmatch(r'[0-9]+', t) is None for t in tokens[1:]):
        raise ValueError('expected nonnegative integer tokens')
    w, h, maximum = map(int, tokens[1:4])
    if (w, h, maximum) != (400, 225, 255):
        raise ValueError('expected dimensions 400x225 and maximum 255')
    if len(tokens) != 4 + w*h*3:
        raise ValueError('wrong sample count (truncated or extra data)')
    pixels = list(map(int, tokens[4:]))
    if any(v > 255 for v in pixels):
        raise ValueError('channel outside [0,255]')
    return w, h, pixels

def compare(candidate, reference=ROOT / 'reference.ppm'):
    w, h, expected = read_ppm(reference)
    _, _, actual = read_ppm(candidate)
    maximum = 0
    first = first_failure = None
    for k, (a, b) in enumerate(zip(actual, expected)):
        diff = abs(a-b)
        maximum = max(maximum, diff)
        pixel = {'row': k//3//w, 'column': k//3%w}
        if diff and first is None:
            first = pixel
        if diff > TOLERANCE and first_failure is None:
            first_failure = pixel
    return dict(match=maximum <= TOLERANCE, tolerance=TOLERANCE,
                max_pixel_difference=maximum, first_differing_pixel=first,
                first_outside_tolerance=first_failure)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', nargs='?', default='out.ppm')
    parser.add_argument('--reference', type=Path, default=ROOT/'reference.ppm')
    args = parser.parse_args()
    try:
        result = compare(args.candidate, args.reference)
    except (OSError, ValueError) as error:
        print(f'mismatch: {error}')
        return 2
    print('match' if result['match'] else 'mismatch')
    print(json.dumps(result, indent=2))
    return 0 if result['match'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
