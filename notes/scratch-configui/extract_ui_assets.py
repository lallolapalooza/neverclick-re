#!/usr/bin/env python3
"""Extract brotli-embedded Tauri v2 web assets from neverclick-ui.exe.

Struct (32B) in .rdata: path_ptr, path_len, bytes_ptr, bytes_len.
Anchor: css struct at file offset 0xdaacb0 (located via pointer xref).
Walks backward/forward validating path shape; decompresses via node brotli.
"""
import struct, subprocess, os, sys, json

EXE = '/home/asdf/Downloads/neverclick-re/extracted/app/neverclick-ui.exe'
OUT = '/home/asdf/Downloads/neverclick-re/extracted/ui-assets'
ANCHOR = 0xdaacb0          # struct for /assets/index-BknSijrv.css
IMG = 0x140000000
BASE_RVA, BASE_PTR = 11829248, 11824640

d = open(EXE, 'rb').read()

def va2off(va):
    return BASE_PTR + (va - IMG - BASE_RVA)

def read_struct(off):
    pp, pl, bp, bl = struct.unpack_from('<QQQQ', d, off)
    return pp, pl, bp, bl

def valid(off):
    try:
        pp, pl, bp, bl = read_struct(off)
        if not (1 <= pl <= 200 and 1 <= bl <= 20_000_000):
            return None
        po, bo = va2off(pp), va2off(bp)
        if not (0 <= po < len(d)) or not (0 <= bo and bo + bl <= len(d)):
            return None
        path = d[po:po + pl]
        if not all(0x20 <= c < 0x7f for c in path):
            return None
        if b'.' not in path or b'/' not in path:
            return None
        return path.decode(), d[bo:bo + bl]
    except Exception:
        return None

# walk backwards/forward from anchor in 32-byte steps
entries = {}
starts = [ANCHOR]
off = ANCHOR
while True:
    off -= 32
    e = valid(off)
    if not e:
        break
    entries[off] = e
    last_back = off
off = ANCHOR + 32
while True:
    e = valid(off)
    if not e:
        break
    entries[off] = e
    off += 32
entries[ANCHOR] = valid(ANCHOR)

print(f'parsed {len(entries)} asset structs')

# dump brotli blobs for node
os.makedirs(OUT, exist_ok=True)
blobs = []
manifest = []
for o in sorted(entries):
    path, blob = entries[o]
    manifest.append({'struct_off': hex(o), 'path': path, 'blob_len': len(blob)})
    blobs.append(blob)

# decompress via node in one go
tmp = '/home/asdf/Downloads/neverclick-re/notes/scratch-configui/probe/blobs.bin'
with open(tmp, 'wb') as f:
    # write as framed file: len(4B) + blob, repeated
    for b in blobs:
        f.write(struct.pack('<I', len(b)))
        f.write(b)

node = r'''
const z=require("zlib"),fs=require("fs");
const b=fs.readFileSync(process.argv[2]);
let p=0,i=0,res=[];
while(p<b.length){
  const n=b.readUInt32LE(p); p+=4;
  const chunk=b.subarray(p,p+n); p+=n;
  try{ const o=z.brotliDecompressSync(chunk); res.push({i,ok:true,len:o.length, data:o}); }
  catch(e){ res.push({i,ok:false,err:String(e.message).slice(0,80)}); }
  i++;
}
const man=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
fs.mkdirSync(process.argv[4],{recursive:true});
for(const r of res){
  const m=man[r.i];
  if(r.ok){ const dst=process.argv[4]+"/"+m.path.replace(/^\//,"").replace(/\.\.\//g,""); fs.mkdirSync(require("path").dirname(dst),{recursive:true}); fs.writeFileSync(dst, r.data); }
}
console.log(res.filter(r=>r.ok).length+" ok, "+res.filter(r=>!r.ok).length+" failed");
for(const r of res.filter(r=>!r.ok)){console.log("FAIL",man[r.i].path,r.err);}
'''
np = '/home/asdf/Downloads/neverclick-re/notes/scratch-configui/probe/extract.js'
open(np, 'w').write(node)
mp = '/home/asdf/Downloads/neverclick-re/notes/scratch-configui/probe/manifest.json'
json.dump(manifest, open(mp, 'w'), indent=1)
r = subprocess.run(['node', np, tmp, mp, OUT], capture_output=True, text=True)
print(r.stdout)
print(r.stderr[:500])
