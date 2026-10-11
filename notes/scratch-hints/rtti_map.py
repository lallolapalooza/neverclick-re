#!/usr/bin/env python3
"""Map MSVC RTTI TypeDescriptors -> CompleteObjectLocator -> vtable -> functions."""
import struct, sys

PATH = "extracted/app/neverclick.exe"
data = open(PATH, "rb").read()

# parse PE
e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
assert data[e_lfanew:e_lfanew+4] == b"PE\0\0"
coff = e_lfanew + 4
nsec = struct.unpack_from("<H", data, coff+2)[0]
opt_size = struct.unpack_from("<H", data, coff+16)[0]
opt = coff + 20
magic = struct.unpack_from("<H", data, opt)[0]
assert magic == 0x20B  # PE32+
image_base = struct.unpack_from("<Q", data, opt+24)[0]
sec_table = opt + opt_size
secs = []
for i in range(nsec):
    off = sec_table + i*40
    name = data[off:off+8].rstrip(b"\0").decode()
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, off+8)
    secs.append((name, vaddr, vsize, rawptr, rawsize))

def va2off(va):
    r = va - image_base
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= r < vaddr + max(vsize, rawsize):
            return rawptr + (r - vaddr)
    return None

def u64(off): return struct.unpack_from("<Q", data, off)[0]
def u32(off): return struct.unpack_from("<I", data, off)[0]

def off2va(off):
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if rawptr <= off < rawptr + rawsize:
            return image_base + vaddr + (off - rawptr)
    return None

# find TypeDescriptors by scanning for class name patterns
targets = sys.argv[1:] or ["?AVVisionProvider@nvr@@", "?AVGridProvider@nvr@@",
    "?AVFullScreenGridProvider@nvr@@", "?AVCustomProvider@nvr@@",
    "?AVUiAutomationProvider@nvr@@", "?AVHintCoordinator@nvr@@",
    "?AVHintProvider@nvr@@"]
# build index: va -> type descriptor
td = {}
for name, vaddr, vsize, rawptr, rawsize in secs:
    blob = data[rawptr:rawptr+rawsize]
    start = 0
    while True:
        i = blob.find(b"?AV", start)
        if i < 0: break
        end = blob.find(b"\0", i)
        s = blob[i:end].decode(errors="replace")
        if s.endswith("@@"):
            # TypeDescriptor = addr of pVFTable ptr, name at +8
            name_off = rawptr + i
            tdva = off2va(name_off - 8)
            if tdva is not None:
                td[tdva] = s
        start = i + 1

# scan for pointers to type descriptors (candidate COLs)
col_hits = {}
for name, vaddr, vsize, rawptr, rawsize in secs:
    if ".rdata" not in name and ".data" not in name: continue
    blob = data[rawptr:rawptr+rawsize]
    for i in range(0, len(blob)-8, 4):
        p = struct.unpack_from("<Q", blob, i)[0]
        if p in td:
            colva = off2va(rawptr + i) - 16  # pTypeDescriptor is at COL+16
            # verify: read COL
            coff2 = va2off(colva)
            if coff2 is None: continue
            sig, off_, cd, ptd, pcls, pself = struct.unpack_from("<IIQQQQ", data, coff2)
            if ptd == p and pself == colva and off_ == 0:
                col_hits[colva] = td[p]

# vtable: right after COL (COL is 24 bytes, vtable usually follows immediately)
for colva, tname in sorted(col_hits.items(), key=lambda kv: kv[1]):
    vtoff = va2off(colva + 24)
    if vtoff is None: continue
    entries = []
    for k in range(64):
        fn = u64(vtoff + 8*k)
        if not (image_base <= fn < image_base + 0x400000): break
        entries.append(fn)
    print(f"== {tname}  COL=0x{colva:X} vtable=0x{colva+24:X} slots={len(entries)}")
    for idx, fn in enumerate(entries):
        o = va2off(fn)
        print(f"   [{idx}] FUN_{fn:X}" + (f" (thunk at {o})" if o else ""))
