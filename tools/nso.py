"""main.img(압축 해제된 NSO 이미지) 분석 도우미: 재배치·ADRP 교차참조·디스어셈블."""
import struct, capstone, os
IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_work', 'exefs_upd', 'main.img')
TEXT_END = 0x1c6ea20

class Img:
    def __init__(self, path=IMG):
        self.b = open(path, 'rb').read()
        self.md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
        self.md.detail = False
        self._rel = None
    def u32(self, o): return struct.unpack_from('<I', self.b, o)[0]
    def u64(self, o): return struct.unpack_from('<Q', self.b, o)[0]
    def relocs(self):
        """R_AARCH64_RELATIVE: {위치: 값}"""
        if self._rel is not None: return self._rel
        mod0 = self.u32(4); dyn = mod0 + struct.unpack_from('<i', self.b, mod0 + 4)[0]
        d = {}
        o = dyn
        while True:
            tag, val = struct.unpack_from('<qQ', self.b, o); o += 16
            if tag == 0: break
            d[tag] = val
        rela, sz = d[7], d[8]
        self._rel = {}
        for o in range(rela, rela + sz, 24):
            off, info, add = struct.unpack_from('<QQq', self.b, o)
            if info & 0xffffffff == 0x403: self._rel[off] = add
        return self._rel
    def ptrs_to(self, lo, hi):
        return sorted((k, v) for k, v in self.relocs().items() if lo <= v < hi)
    def adrp_refs(self, lo, hi, text_end=TEXT_END):
        """ADRP(+ADD/LDR) 로 [lo,hi) 를 만드는 코드 위치 (대략: ADRP 페이지 + 다음 4개 명령 안의 ADD/LDR 즉시값)."""
        out = []
        b = self.b
        plo, phi = lo & ~0xfff, (hi + 0xfff) & ~0xfff
        for pc in range(0, text_end, 4):
            w = struct.unpack_from('<I', b, pc)[0]
            if w & 0x9f000000 != 0x90000000: continue
            imm = ((w >> 29) & 3) | (((w >> 5) & 0x7ffff) << 2)
            if imm & (1 << 20): imm -= 1 << 21
            page = (pc & ~0xfff) + (imm << 12)
            if not (plo <= page < phi): continue
            rd = w & 31
            for k in range(1, 6):
                w2 = struct.unpack_from('<I', b, pc + 4 * k)[0]
                if (w2 & 0xffc00000) == 0x91000000 and ((w2 >> 5) & 31) == rd:  # add x
                    t = page + ((w2 >> 10) & 0xfff)
                    if lo <= t < hi: out.append((pc, t))
                    break
                if (w2 & 0x3b000000) == 0x39000000 and ((w2 >> 5) & 31) == rd:  # ldr/str unsigned imm
                    size = w2 >> 30; t = page + (((w2 >> 10) & 0xfff) << size)
                    if lo <= t < hi: out.append((pc, t))
                    break
        return out
    def dis(self, a, n=40):
        for i in self.md.disasm(self.b[a:a + 4 * n], a):
            print('%08x  %s %s' % (i.address, i.mnemonic, i.op_str))
