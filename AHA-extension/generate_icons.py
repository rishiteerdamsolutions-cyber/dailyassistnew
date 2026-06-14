#!/usr/bin/env python3
import struct, zlib, os

def make_png(width, height, r, g, b):
    def chunk(name, data):
        c = struct.pack('>I', len(data)) + name + data
        return c + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
    raw = b''
    for _ in range(height):
        row = b'\x00'
        for _ in range(width):
            row += bytes([r, g, b])
        raw += row
    compressed = zlib.compress(raw)
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')

out_dir = '/Users/nandagiriaditya/GEMINI/ARTIFICIALHUMANAGENT/AHA-extension/extension/icons'
os.makedirs(out_dir, exist_ok=True)
for size in [16, 48, 128]:
    path = f'{out_dir}/icon{size}.png'
    with open(path, 'wb') as f:
        f.write(make_png(size, size, 0x4f, 0x8e, 0xf7))
    print(f'Created {path}')
print('Done.')
