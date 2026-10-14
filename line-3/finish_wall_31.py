"""Keep only this round's image-tool paint; preserve every ancestor pixel elsewhere.

Production helper, not a Code Metadata dependency. FFmpeg composites the editor's
new small head and peeled stone in their original positions. The shared standard
library encoder creates the required thumbnail. No additional images are saved.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('thumbnail', ROOT / 'shared/wall-thumbnail/thumbnail.py')
thumbnail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail)
ancestor_path = ROOT / 'artifacts/line-3/wall.png'
generated_path = ROOT / 'artifacts/line-3/wall-v11.png'
ancestor_bytes = ancestor_path.read_bytes()
generated_bytes = generated_path.read_bytes()
assert hashlib.sha256(ancestor_bytes).hexdigest() == '3b1c683e0032f7da1231ceda663d1f549cb13f7fbddcf080e4fdcd894f135980'
width, height, ancestor = thumbnail.png_rgb(ancestor_path)
gw, gh, _ = thumbnail.png_rgb(generated_path)
assert (width, height) == (gw, gh) == (1254, 1254)
x, y, w, h = 683, 1048, 250, 132
# Feather only the clear-rock edge of the image-generated addition. No motif moves.
filters = (f"[1:v]crop={w}:{h}:{x}:{y},format=rgba,"
           "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
           "a='255*min(1,min(min(X,W-1-X),min(Y,H-1-Y))/8)'[paint];"
           f"[0:v][paint]overlay={x}:{y}:format=rgb,format=rgb24[out]")
command = ['ffmpeg', '-v', 'error', '-filter_complex_threads', '1',
           '-i', str(ancestor_path), '-i', str(generated_path), '-filter_complex', filters,
           '-map', '[out]', '-frames:v', '1', '-threads', '1', '-c:v', 'png',
           '-f', 'image2pipe', 'pipe:1']
png = subprocess.run(command, check=True, capture_output=True).stdout
assert png.startswith(b'\x89PNG\r\n\x1a\n')
generated_path.write_bytes(png)
fw, fh, final = thumbnail.png_rgb(generated_path)
assert (fw, fh) == (width, height)
inside = outside = 0
for py in range(height):
    for px in range(width):
        if final[py][3*px:3*px+3] != ancestor[py][3*px:3*px+3]:
            if x <= px < x+w and y <= py < y+h:
                inside += 1
            else:
                outside += 1
assert inside > 0 and outside == 0
ancestor_path.write_bytes(png)
jpeg = thumbnail.jpeg(thumbnail.resize(width, height, final, 512))
assert len(jpeg) < 100000
with (ROOT / 'dist/line-3/31.jpg').open('xb') as stream:
    stream.write(jpeg)
report = {
    'ancestor_sha256': hashlib.sha256(ancestor_bytes).hexdigest(),
    'generated_before_assembly_sha256': hashlib.sha256(generated_bytes).hexdigest(),
    'wall_sha256': hashlib.sha256(png).hexdigest(), 'format': 'PNG',
    'dimensions': [width, height], 'mode': 'RGB', 'wall_bytes': len(png),
    'addition_boxes_xyxy': [[x, y, x+w, y+h]],
    'changed_pixels_inside_boxes': inside, 'changed_pixels_outside_boxes': outside,
    'thumbnail': {'path': 'dist/line-3/31.jpg', 'format': 'JPEG', 'dimensions': [512, 512],
                  'bytes': len(jpeg), 'sha256': hashlib.sha256(jpeg).hexdigest()},
    'manual_review_pending': True,
}
(ROOT / 'line-3/visual-checks-31.json').write_text(json.dumps(report, indent=2) + '\n')
record = {'name': 'The Stone Skin',
          'image': 'https://api.imd.fun/artifacts/' + report['wall_sha256'],
          'attributes': [
              {'trait_type': 'Cave', 'value': 'Moss'},
              {'trait_type': 'Wall', 'value': 'Line 3'},
              {'trait_type': 'Number', 'value': 31},
              {'trait_type': 'Left behind', 'value': 'Code Metadata'},
              {'trait_type': 'Meaning', 'value': 'Pepe looks beneath the skin of a code stone.'},
              {'trait_type': 'One thing', 'value': 'Ethereum executable code identity'}]}
with (ROOT / 'dist/line-3/31.json').open('x') as stream:
    stream.write(json.dumps(record, indent=2) + '\n')
print(json.dumps(report, indent=2))
