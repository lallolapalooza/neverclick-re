#!/usr/bin/env python3
"""Static vtable/RTTI resolver for neverclick.exe (read-only, never executes the binary).

Usage:
  vt.py vt 0x14026a5b8 [n]          dump a vtable (given PTR_FUN_xxx address)
  vt.py cls <mangled-or-plain-name> find RTTI typeinfo -> COL -> vtable -> functions
  vt.py str 0x140288990 [len]       read a .rdata string at VA
  vt.py scan <substring>            list RTTI/other strings containing substring

All output maps function VAs back to Ghidra decomp headers (line numbers) via
notes/scratch-interaction/func-index.txt when the VA is a known function.
"""
import struct
import sys
import re
import pefile

EXE = "/home/asdf/Downloads/neverclick-re/extracted/app/neverclick.exe"
IDX = "/home/asdf/Downloads/neverclick-re/notes/scratch-interaction/func-index.txt"

pe = pefile.PE(EXE)
image_base = pe.OPTIONAL_HEADER.ImageBase


def va_to_off(va):
    rva = va - image_base
    return pe.get_offset_from_rva(rva)


def off_to_va(off):
    try:
        return image_base + pe.get_rva_from_offset(off)
    except Exception:
        return None


def qword(va):
    return struct.unpack_from("<Q", pe.__data__, va_to_off(va))[0]


def dword(va):
    return struct.unpack_from("<I", pe.__data__, va_to_off(va))[0]


# function VA -> decomp header line
func_map = {}


def load_index():
    with open(IDX) as f:
        for line in f:
            m = re.match(r"(\d+):.*?----- ([0-9a-f]+) : ", line)
            if m:
                func_map[int(m.group(2), 16)] = int(m.group(1))


def fname(va):
    ln = func_map.get(va)
    tag = f"FUN_{va:x}" if va else "0"
    return f"{tag}@line{ln}" if ln else tag


def in_exec(va):
    if not va:
        return False
    try:
        off = va_to_off(va)
    except Exception:
        return False
    for s in pe.sections:
        if s.contains_offset(off) and s.Characteristics & 0x20000000:
            return True
    return False


def dump_vtable(va, n=12):
    out = []
    for i in range(n):
        try:
            e = qword(va + 8 * i)
        except Exception:
            break
        if not in_exec(e):
            break
        out.append(f"  [{i:2d}] 0x{e:x}  {fname(e)}")
    return "\n".join(out) or "  (no executable entries)"


def rdata():
    for s in pe.sections:
        if b".rdata" in s.Name.rstrip(b"\x00"):
            return s.get_data(), s.VirtualAddress
    return None, None


def scan_bytes(needle):
    data = pe.__data__
    res = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        res.append(i)
        start = i + 1
    return res


def find_class(name):
    """Find MSVC RTTI typeinfo for plain name like nvr::ToolActivationHookCallback."""
    parts = name.split("::")
    mangled = ("?AV" + "@".join(reversed(parts)) + "@@").encode()
    hits = scan_bytes(mangled + b"\x00")
    results = []
    for off in hits:
        name_va = off_to_va(off)
        if name_va is None:
            continue
        # MSVC typeinfo = {pVFtable(8), spare(8), name[]} where name begins with '.'
        # our needle starts at the '?' (name_va = name_addr + 1)
        ti_va = name_va - 17
        ti_rva = ti_va - image_base
        # x64 COL = {sig(4), offset(4), cdOffset(4), pTypeDescriptor RVA(4), pSelf(8)}
        for hit_off in scan_bytes(struct.pack("<I", ti_rva)):
            if hit_off < 0xC:
                continue
            col_off = hit_off - 0xC
            col_va = off_to_va(col_off)
            if col_va is None:
                continue
            pself = struct.unpack_from("<Q", pe.__data__, col_off + 0x10)[0]
            if pself != col_va:
                continue
            vt_va = col_va + 0x18  # COL (0x18) immediately precedes vtable
            results.append((ti_va, col_va, vt_va))
    return results


def main():
    load_index()
    cmd = sys.argv[1]
    if cmd == "vt":
        va = int(sys.argv[2], 16)
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 12
        print(dump_vtable(va, n))
    elif cmd == "cls":
        name = sys.argv[2]
        res = find_class(name)
        if not res:
            print("no RTTI found")
        for ti, col, vt in res:
            print(f"typeinfo=0x{ti:x} COL=0x{col:x} vtable?=0x{vt:x}")
            print(dump_vtable(vt, 16))
    elif cmd == "str":
        va = int(sys.argv[2], 16)
        ln = int(sys.argv[3]) if len(sys.argv) > 3 else 64
        off = va_to_off(va)
        raw = pe.__data__[off:off + ln]
        print(repr(raw))
    elif cmd == "scan":
        pat = sys.argv[2].encode()
        for off in scan_bytes(pat):
            va = off_to_va(off)
            ctx = pe.__data__[off:off + 80]
            print(f"0x{va:x}: {ctx!r}")


if __name__ == "__main__":
    main()
