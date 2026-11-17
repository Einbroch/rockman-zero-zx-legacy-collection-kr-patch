"""main NSO 패치 공통: 가져오기 이름 바꾸기 + 훅 지점 → IPS32, subsdk9 배치.
훅 지점 형식(16바이트): mov x15,x30 ; movz x14,#id ; movk x14,#0x4b4f,lsl#48 ; bl <MakeIpv4Address PLT>"""
import os, struct, sys, shutil
import keystone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, '_work', 'exefs_upd', 'main.img')
NSO = os.path.join(ROOT, '_work', 'exefs_upd', 'main')
BUILD_ID = '48A7577F4E740FEDCB50BA59D7B45AF4'
STRTAB = 0x20fba68
OLD_NAME = b'_ZN2nn3ldn15MakeIpv4AddressEhhhh'
NEW_NAME = b'kohook_dispatch_0000000000000000'
PLT = 0x1c6c620
ks = keystone.Ks(keystone.KS_ARCH_ARM64, keystone.KS_MODE_LITTLE_ENDIAN)

def asm(src, addr):
    enc, _ = ks.asm(src, addr)
    return bytes(enc)

def hook_site(addr, hid):
    return asm(f'mov x15, x30; movz x14, #{hid}; movk x14, #0x4b4f, lsl #48; bl {PLT:#x}', addr)

def ips32(orig, new, base=0x100):
    out = bytearray(b'IPS32'); i = 0; n = len(orig); recs = 0
    while i < n:
        if orig[i] != new[i]:
            j = i
            while j < n and orig[j] != new[j] and j - i < 0xFFFF: j += 1
            o = i + base
            assert o != 0x45454F46
            out += struct.pack('>IH', o, j - i) + new[i:j]; recs += 1; i = j
        else: i += 1
    out += b'EEOF'
    return bytes(out), recs

def branch_targets(img, text_end=0x1c6ea20):
    """.text 의 직접 분기(B/BL/B.cond/CBZ/CBNZ/TBZ/TBNZ) 목적지 집합."""
    import numpy as np
    w = np.frombuffer(img[:text_end], dtype='<u4').astype(np.int64)
    pc = np.arange(len(w), dtype=np.int64) * 4
    out = []
    m = (w >> 26) & 0x1f == 0x05                       # B, BL
    imm = w & 0x3ffffff; imm = np.where(imm & 0x2000000, imm - (1 << 26), imm)
    out.append((pc + imm * 4)[m])
    m = ((w >> 24) == 0x54) | (((w >> 25) & 0x3f) == 0x1a)   # B.cond, CBZ/CBNZ
    imm = (w >> 5) & 0x7ffff; imm = np.where(imm & 0x40000, imm - (1 << 19), imm)
    out.append((pc + imm * 4)[m])
    m = ((w >> 25) & 0x3f) == 0x1b                     # TBZ/TBNZ
    imm = (w >> 5) & 0x3fff; imm = np.where(imm & 0x2000, imm - (1 << 14), imm)
    out.append((pc + imm * 4)[m])
    return set(np.concatenate(out).tolist())

def build(hooks, expect, out_dir, raw=None):
    """hooks: [(주소, 훅번호)], expect: {주소: 원래 바이트(검사용)}, raw: {주소: (원래 바이트, 새 바이트)} 직접 패치"""
    img = open(IMG, 'rb').read(); new = bytearray(img)
    so = img.index(OLD_NAME + b'\0', STRTAB)
    assert so - STRTAB == 0x1e3
    new[so:so + len(OLD_NAME)] = NEW_NAME
    targets = branch_targets(img)
    for addr, hid in hooks:
        inside = [t for t in (addr + 4, addr + 8, addr + 12) if t in targets]
        if inside:
            sys.exit(f'mainpatch: 훅 지점 {addr:#x} 안쪽으로 뛰는 분기 있음 {[hex(t) for t in inside]}')
        if addr in expect:
            assert img[addr:addr + len(expect[addr])] == expect[addr], hex(addr)
        new[addr:addr + 16] = hook_site(addr, hid)
    for addr, (old, nb) in (raw or {}).items():
        assert len(old) == len(nb) and img[addr:addr + len(old)] == old, hex(addr)
        assert all(h + 16 <= addr or addr + len(old) <= h for h, _ in hooks), ('훅 지점과 겹침', hex(addr))
        new[addr:addr + len(nb)] = nb
    patch, recs = ips32(img, bytes(new))
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, BUILD_ID + '.ips'), 'wb').write(patch)
    return recs
