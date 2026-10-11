#!/usr/bin/env python3
import re, struct, json
dec='/home/asdf/Downloads/neverclick-re/ghidra/neverclick-decomp.c'
exe='/home/asdf/Downloads/neverclick-re/extracted/app/neverclick.exe'
lines=open(dec,errors='replace').read().split('\n')
# route registration region
start,end=116400,116960
assign=re.compile(r'(local_[0-9a-f]+|uStack_[0-9a-f]+)\s*=\s*&PTR_FUN_([0-9a-f]+)')
pathre=re.compile(r'FUN_1400204c0\(&local_398,"([^"]+)"')
regcall=re.compile(r'FUN_1400(93f20|93fc0|94060|94180|95aa0)\(([^,]+),')
vt={}   # handler var -> last vtable assigned
routes=[]
pend=None
for i in range(start,end):
    l=lines[i-1] if i-1<len(lines) else ''
    m=assign.search(l)
    if m: vt[m.group(1)]=m.group(2)
    m=pathre.search(l)
    if m: pend=(m.group(1),i)
    m=regcall.search(l)
    if m and pend:
        # handler argument: for 94180(base+off,uVar,handler) or others (path-str, handler)
        args=m.group(2)
        after=lines[i-1][m.end():]
        full=l[m.start():]
        # handler var is 3rd arg; find in full line after path variable
        hm=re.search(r'(?:local_[0-9a-f]+|&local_[0-9a-f]+|uStack_[0-9a-f]+)', full[full.find(',')+1:])
        # simpler: capture all local vars in the registration line
        cands=re.findall(r'&?(local_[0-9a-f]+)', full)
        handler=None
        for c in reversed(cands):
            if c in vt and c!='local_398':
                handler=c; break
        # inline handlers: path registered via FUN_140094180(base+X, uVar, &local_X) uses var built before path
        routes.append({'line':i,'path':pend[0],'wrapper':'FUN_1400'+m.group(1),
                       'handler':handler,'vtable':vt.get(handler)})
        pend=None
# also handle 94180 with constructed string (health/events/app-config): path was inline-encoded; find lines with FUN_140094180(param_1 +
for i in range(start,end):
    l=lines[i-1] if i-1<len(lines) else ''
    if 'FUN_140094180(param_1 + ' in l:
        # find handler var in this line
        cands=re.findall(r'(local_[0-9a-f]+)',l)
        h=None
        for c in reversed(cands):
            if c in vt: h=c;break
        routes.append({'line':i,'path':'<inline:health/events/app-config or hotkeys/:id>','wrapper':'FUN_140094180','handler':h,'vtable':vt.get(h)})
print(json.dumps(routes,indent=1))
# parse vtables from exe .rdata
d=open(exe,'rb').read()
e=struct.unpack_from('<I',d,0x3c)[0]
n=struct.unpack_from('<H',d,e+6)[0]; osz=struct.unpack_from('<H',d,e+20)[0]
base=struct.unpack_from('<Q',d,e+24+24)[0]
secs=[]
for k in range(n):
    o=e+24+osz+k*40
    nm=d[o:o+8].rstrip(b'\x00').decode(errors='replace')
    vsz,va,rsz,ptr=struct.unpack_from('<IIII',d,o+8)
    secs.append((nm,va,vsz,ptr,rsz))
def off(va):
    r=va-base
    for nm,cva,vsz,ptr,rsz in secs:
        if cva<=r<cva+max(vsz,rsz): return ptr+(r-cva)
    return None
vts=sorted({r['vtable'] for r in routes if r['vtable']})
out={}
for v in vts:
    o=off(int(v,16))
    ents=[struct.unpack_from('<Q',d,o+8*j)[0] for j in range(6)]
    out[v]=[hex(x) for x in ents]
print(json.dumps(out,indent=1))
