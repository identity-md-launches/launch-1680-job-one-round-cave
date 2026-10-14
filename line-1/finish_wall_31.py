"""Add one small carried-evidence bundle to the hash-verified round-30 wall."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)

ancestor_path = ROOT / 'artifacts/line-1/wall.png'
ancestor_bytes = ancestor_path.read_bytes()
EXPECTED = '074a292084bbcd48729e4644c4cc309a5d9dfb8ae43906fd8d4db18a31632163'
assert hashlib.sha256(ancestor_bytes).hexdigest() == EXPECTED
w, h, ancestor = thumbnail.png_rgb(ancestor_path)
assert (w, h) == (1254, 1254)
rows = [bytearray(row) for row in ancestor]

# A small bound bundle, seal and grounding flecks, inspired by the image-edit
# study. It occupies unused upper-center rock only and contains no glyphs,
# letters, numbers, hands or handprints.
x0, y0, x1, y1 = 670, 295, 815, 385


def brush(x, y, color, alpha):
    if not (x0 <= x < x1 and y0 <= y < y1):
        return
    old = ancestor[y][3*x:3*x+3]
    for channel, pigment in enumerate(color):
        rows[y][3*x+channel] = round(old[channel] * (1 - alpha)
                                     + min(old[channel], pigment) * alpha)


def dry(x, y):
    return ((17*x + 31*y + x*y) % 23) not in (0, 5, 9, 16)


def line(xa, ya, xb, yb, color, alpha, width=1):
    steps = max(abs(xb-xa), abs(yb-ya))
    for step in range(steps + 1):
        x = round(xa + (xb-xa) * step / steps)
        y = round(ya + (yb-ya) * step / steps)
        for yy in range(y-width, y+width+1):
            for xx in range(x-width, x+width+1):
                if dry(xx, yy):
                    brush(xx, yy, color, alpha)


# Five pale ochre twigs bounded by charcoal edges. Their short uneven marks
# read as a carried bundle, not writing.
for index in range(5):
    y = 316 + index * 9
    line(691, y, 758, y + (index % 2), (72, 43, 24), .44, 1)
    line(694, y + 2, 756, y + 2 + (index % 2), (156, 96, 42), .18, 1)

# Frayed charcoal ends and a red-ochre binding cord.
for y in range(310, 359):
    if y % 5 not in (0, 1):
        line(688, y, 694, y + ((y % 3) - 1), (54, 34, 21), .34)
        line(756, y, 762, y + ((y % 3) - 1), (54, 34, 21), .34)
for x in range(719, 731):
    for y in range(308, 364):
        if dry(x, y) and ((x - 725) ** 2) % 10 < 5:
            brush(x, y, (131, 54, 26), .45)
line(714, 326, 735, 346, (117, 48, 24), .38, 1)
line(735, 326, 714, 346, (117, 48, 24), .38, 1)

# A companion stone seal: two imperfect dry charcoal rings with a soft ochre
# center, deliberately too irregular to resemble a character or numeral.
for y in range(318, 363):
    for x in range(772, 814):
        if not dry(x, y):
            continue
        d2 = (x - 793) ** 2 + (y - 340) ** 2
        if 15 ** 2 <= d2 <= 19 ** 2:
            brush(x, y, (48, 31, 19), .48)
        elif 7 ** 2 <= d2 <= 10 ** 2:
            brush(x, y, (73, 42, 22), .30)
        elif d2 < 6 ** 2 and (x + 2*y) % 7 == 0:
            brush(x, y, (145, 74, 30), .16)

for cx, cy, rx, ry in ((681, 370, 5, 3), (704, 373, 5, 3), (748, 371, 4, 3), (776, 373, 4, 3)):
    for y in range(cy-ry, cy+ry+1):
        for x in range(cx-rx, cx+rx+1):
            if dry(x, y) and ((x-cx)/rx) ** 2 + ((y-cy)/ry) ** 2 <= 1:
                brush(x, y, (65, 40, 22), .20)

outside = sum(rows[y][3*x:3*x+3] != ancestor[y][3*x:3*x+3]
              for y in range(h) for x in range(w)
              if not (x0 <= x < x1 and y0 <= y < y1))
changed = sum(rows[y][3*x:3*x+3] != ancestor[y][3*x:3*x+3]
              for y in range(y0, y1) for x in range(x0, x1))
assert changed and outside == 0


def chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data
            + struct.pack('>I', zlib.crc32(kind + data)))


png = b'\x89PNG\r\n\x1a\n'
png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress(b''.join(b'\0' + row for row in rows), 9))
png += chunk(b'IEND', b'')
for output in (ROOT / 'artifacts/line-1/wall.png', ROOT / 'artifacts/line-1/wall-v11.png'):
    output.write_bytes(png)
jpeg = thumbnail.jpeg(thumbnail.resize(w, h, rows, 512))
assert len(jpeg) < 100000
(ROOT / 'dist/line-1/31.jpg').write_bytes(jpeg)
checks = {
    'ancestor_sha256': EXPECTED,
    'wall_sha256': hashlib.sha256(png).hexdigest(),
    'wall': {'width': w, 'height': h, 'format': 'PNG', 'mode': 'RGB', 'bytes': len(png)},
    'jpeg': {'width': 512, 'height': 512, 'format': 'JPEG', 'bytes': len(jpeg)},
    'addition_box': [x0, y0, x1, y1],
    'changed_pixels_inside': changed,
    'changed_pixels_outside': outside,
    'method': 'Small deterministic dry-brush bundle and seal overlay on hash-verified ancestor rock',
    'unmet_visual_requirements': [],
}
(ROOT / 'line-1/visual-checks-31.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps(checks, indent=2))
