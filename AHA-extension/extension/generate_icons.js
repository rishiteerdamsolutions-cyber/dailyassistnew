// Node.js script to generate AHA PNG icons — run once after cloning.
// Usage: node generate_icons.js
// Requires: Node.js (no extra packages)

const fs   = require('fs');
const path = require('path');
const zlib = require('zlib');

function makePng(size, r, g, b) {
  function chunk(nameStr, data) {
    const name = Buffer.from(nameStr, 'ascii');
    const lenBuf = Buffer.alloc(4);
    lenBuf.writeUInt32BE(data.length, 0);
    const crcInput = Buffer.concat([name, data]);
    const crc = crc32(crcInput);
    const crcBuf = Buffer.alloc(4);
    crcBuf.writeUInt32BE(crc >>> 0, 0);
    return Buffer.concat([lenBuf, name, data, crcBuf]);
  }

  // CRC-32 table
  const crcTable = (() => {
    const table = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) {
        c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      }
      table[n] = c;
    }
    return table;
  })();

  function crc32(buf) {
    let c = 0xFFFFFFFF;
    for (let i = 0; i < buf.length; i++) {
      c = crcTable[(c ^ buf[i]) & 0xFF] ^ (c >>> 8);
    }
    return (c ^ 0xFFFFFFFF) >>> 0;
  }

  // IHDR
  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(size, 0);
  ihdrData.writeUInt32BE(size, 4);
  ihdrData[8]  = 8;  // bit depth
  ihdrData[9]  = 2;  // color type: RGB
  ihdrData[10] = 0;
  ihdrData[11] = 0;
  ihdrData[12] = 0;
  const ihdr = chunk('IHDR', ihdrData);

  // Raw pixel data: filter byte (0) + RGB per row
  const row = Buffer.alloc(1 + size * 3);
  row[0] = 0; // filter: None
  for (let i = 0; i < size; i++) {
    row[1 + i * 3]     = r;
    row[1 + i * 3 + 1] = g;
    row[1 + i * 3 + 2] = b;
  }
  const rawRows = Buffer.concat(Array(size).fill(row));
  const compressed = zlib.deflateSync(rawRows, { level: 9 });
  const idat = chunk('IDAT', compressed);

  const iend = chunk('IEND', Buffer.alloc(0));

  const sig = Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
  return Buffer.concat([sig, ihdr, idat, iend]);
}

const outDir = path.join(__dirname, 'icons');
fs.mkdirSync(outDir, { recursive: true });

// AHA accent: #4f8ef7 = (79, 142, 247)
const [R, G, B] = [79, 142, 247];

for (const [size, name] of [[16, 'icon16'], [48, 'icon48'], [128, 'icon128']]) {
  const filePath = path.join(outDir, `${name}.png`);
  fs.writeFileSync(filePath, makePng(size, R, G, B));
  console.log(`✓ ${filePath}  (${size}×${size})`);
}

console.log('Icons generated successfully.');
