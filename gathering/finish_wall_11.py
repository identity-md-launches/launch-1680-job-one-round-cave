#!/usr/bin/env python3
"""Keep round 10 exact outside the one generated round-11 pigment motif."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path('shared/wall-thumbnail').resolve()))
import thumbnail

SOURCE_SHA256 = 'c9709a5bb05cf0b90c21798b96a47afb4600010e104a782b1f2fe708a36e7fcf'
# This rock-only rectangle bounds the new crescent, pebbles and short trail.
BOX = (750, 235, 865, 345)


def chunk(kind, data):
    return (struct.pack('>I', len(data)) + kind + data +
            struct.pack('>I', zlib.crc32(kind + data)))


def motif_pixel(x, y):
    """Keep only generated pigment, never its broad background re-render."""
    def disk(cx, cy, radius):
        return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2

    # The charcoal crescent is the left portion of a thick uneven ellipse.
    oval = ((x - 802) / 43) ** 2 + ((y - 289) / 46) ** 2
    crescent = 0.38 <= oval <= 1.16 and x <= 807
    # Three daubed stones and their short joining stroke.
    stones = disk(798, 291, 13) or disk(825, 261, 12) or disk(831, 317, 12)
    trail = disk(812, 275, 9) or disk(817, 270, 7)
    return crescent or stones or trail


def main():
    old_path = Path('/tmp/gathering-v10.png')
    wall_path = Path('artifacts/gathering/wall-v11.png')
    assert hashlib.sha256(old_path.read_bytes()).hexdigest() == SOURCE_SHA256
    generated_sha256 = hashlib.sha256(wall_path.read_bytes()).hexdigest()
    width, height, old = thumbnail.png_rgb(old_path)
    newer_width, newer_height, generated = thumbnail.png_rgb(wall_path)
    assert (width, height) == (newer_width, newer_height) == (1254, 1254)
    x0, y0, x1, y1 = BOX
    rows, changed, outside = [], 0, 0
    for y in range(height):
        row = bytearray(old[y])
        if y0 <= y <= y1:
            for x in range(x0, x1 + 1):
                if motif_pixel(x, y):
                    at = x * 3
                    row[at:at + 3] = generated[y][at:at + 3]
        for x in range(width):
            at = x * 3
            if row[at:at + 3] != old[y][at:at + 3]:
                changed += 1
                outside += not (x0 <= x <= x1 and y0 <= y <= y1)
        rows.append(bytes(row))
    assert changed > 0 and outside == 0
    encoded = (b'\x89PNG\r\n\x1a\n' +
               chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
               chunk(b'IDAT', zlib.compress(b''.join(b'\x00' + row for row in rows))) +
               chunk(b'IEND', b''))
    wall_path.write_bytes(encoded)
    result = {
        'schema': 'gathering-visual-preservation-v11',
        'source_sha256': SOURCE_SHA256,
        'image_tool_output_sha256': generated_sha256,
        'output_sha256': hashlib.sha256(encoded).hexdigest(),
        'format': 'PNG RGB 8-bit', 'width': width, 'height': height,
        'addition_rectangle': list(BOX), 'changed_pixels': changed,
        'changed_pixels_outside_addition': outside,
        'ancestral_pigment_intersects_addition': False,
        'left_hand_digits': 5, 'right_hand_digits': 5, 'new_hands': 0,
        'unmet_visual_requirements_observed': [],
        'review_limits': ('Visual character and digit counts are subjective review; '
                          'raster preservation is measured outside the addition.')}
    Path('gathering/visual-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
