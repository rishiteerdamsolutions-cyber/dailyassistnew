#!/usr/bin/env python3
"""Generate AHA extension icon PNG files (solid #4f8ef7 blue squares)."""
import struct, zlib, os

def make_png(size, r, g, b):
    def chunk(name, data):
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', crc)

    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0))

    raw = b''.join(b'\x00' + bytes([r, g, b] * size) for _ in range(size))
    idat = chunk(b'IDAT', zlib.compress(raw, 9))
    iend = chunk(b'IEND', b'')

    return b'\x89PNG\r\n\x1a\n' + ihdr + idat + iend

out_dir = os.path.join(os.path.dirname(__file__), 'icons')
os.makedirs(out_dir, exist_ok=True)

# AHA accent colour: #4f8ef7 = (79, 142, 247)
R, G, B = 79, 142, 247

for size, name in [(16, 'icon16'), (48, 'icon48'), (128, 'icon128')]:
    path = os.path.join(out_dir, f'{name}.png')
    with open(path, 'wb') as f:
        f.write(make_png(size, R, G, B))
    print(f'✓ {path}  ({size}x{size})')

print('Icons generated successfully.')
