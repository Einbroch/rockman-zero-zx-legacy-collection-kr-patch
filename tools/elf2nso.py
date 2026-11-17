"""링크된 ELF(PT_LOAD 3개: text/ro/data) → 비압축 NSO. 사용: python elf2nso.py in.elf out.nso"""
import struct, sys, hashlib
src, dst = sys.argv[1], sys.argv[2]
b = open(src, 'rb').read()
phoff, = struct.unpack_from('<Q', b, 0x20); phn, = struct.unpack_from('<H', b, 0x38)
loads = []
for i in range(phn):
    t, fl, off, va, pa, fsz, msz, al = struct.unpack_from('<IIQQQQQQ', b, phoff + i * 56)
    if t == 1: loads.append((va, b[off:off + fsz], msz))
assert len(loads) == 3, loads
(tv, td, _), (rv, rd, _), (dv, dd, dm) = loads
assert tv == 0 and rv % 0x1000 == 0 and dv % 0x1000 == 0
bss = dm - len(dd)
# 섹션 표에서 dynstr/dynsym 위치
shoff, = struct.unpack_from('<Q', b, 0x28); shn, = struct.unpack_from('<H', b, 0x3c); shs, = struct.unpack_from('<H', b, 0x3e)
secs = [struct.unpack_from('<IIQQQQIIQQ', b, shoff + i * 64) for i in range(shn)]
so = secs[shs][4]
def sec(name):
    for s in secs:
        if b[so + s[0]:b.index(b'\0', so + s[0])].decode() == name: return s[3], s[5]
dstr, dsym = sec('.dynstr'), sec('.dynsym')
hdr = bytearray(0x100)
struct.pack_into('<4sIII', hdr, 0, b'NSO0', 0, 0, 0)
off = 0x100
segs = [(td, tv), (rd, rv), (dd, dv)]
fo = []
for i, (d, v) in enumerate(segs):
    fo.append(off)
    struct.pack_into('<III', hdr, 0x10 + i * 0x10, off, v, len(d))
    struct.pack_into('<I', hdr, 0x60 + i * 4, len(d))
    off += len(d)
struct.pack_into('<I', hdr, 0x3C, bss)
hdr[0x40:0x60] = hashlib.sha256(td + rd + dd).digest()[:0x20]
struct.pack_into('<II', hdr, 0x90, dstr[0] - rv, dstr[1])
struct.pack_into('<II', hdr, 0x98, dsym[0] - rv, dsym[1])
for i, (d, v) in enumerate(segs):
    hdr[0xA0 + i * 0x20:0xC0 + i * 0x20] = hashlib.sha256(d).digest()
open(dst, 'wb').write(bytes(hdr) + td + rd + dd)
print('nso', dst, 'text', hex(len(td)), 'ro', hex(len(rd)), 'data', hex(len(dd)), 'bss', hex(bss))
