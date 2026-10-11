
import struct, sys, os

def chunks(b):
    assert b[:4]==b'DXBC', b[:4]
    n=struct.unpack_from('<I',b,28)[0]
    offs=struct.unpack_from('<%dI'%n,b,32)
    out={}
    for o in offs:
        tag=b[o:o+4].decode('latin1'); size=struct.unpack_from('<I',b,o+4)[0]
        out[tag]=b[o+8:o+8+size]
    return out

OPS={0:'nop',1:'mov',2:'add',3:'sub',4:'mul',5:'div',6:'mad',7:'min',8:'max',9:'lrp',
10:'frc',11:'round_ne',12:'round_ni',13:'round_pi',14:'round_z',15:'sqrt',16:'rsq',17:'round_ni',
18:'round_pi'}  # placeholder, will fix by alignment

def parse(b):
    ch=chunks(b); shex=ch['SHEX']
    ver,ln=struct.unpack_from('<II',shex,0)
    dwords=struct.unpack_from('<%dI'%ln,shex,8)
    return ver,ln,dwords

for name in ['edge_4_14026fd10','edge_5_14026f520']:
    b=open('/home/asdf/Downloads/neverclick-re/notes/scratch-vision/dxbc/%s.dxbc'%name,'rb').read()
    ver,ln,dw=parse(b)
    print('==',name,'version=0x%08x dwords=%d'%(ver,ln))
    i=0; idx=0
    while i<len(dw):
        t=dw[i]
        op=t&0x7ff; l=(t>>11)&0x1fff or ((t>>24)&0x7f)
        print('%3d off %4d tok %08x op %3d len %d  %s'%(idx,i,t,op,l,' '.join('%08x'%x for x in dw[i+1:i+l])))
        i+= max(l,1); idx+=1
