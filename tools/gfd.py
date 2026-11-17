"""MT Framework GFD(컬렉션 런처 글꼴 정의, 판 0x11107) 읽기/쓰기.
머리 u32 10개(0 마법 'GFD', 1 판, …, 6 텍스처 수, 7 글자 수, …, 9) + 실수 4+머리[9]개(0x28~) + u32 이름 길이 + 이름 + NUL,
그다음 글자 항목 36바이트 × 글자 수(코드포인트 오름차순): u32 코드, 실수 6개(폭, 높이, 왼쪽 여백, 위 여백, 전진폭, 줄 높이),
u32 위치(페이지 0~7비트 | x 8~19비트 | y 20~31비트), u32 (뜻 미상, 원본 값 그대로)."""
import struct


class Gfd:
    def __init__(self, b):
        assert b[:4] == b'GFD\0'
        self.head = list(struct.unpack_from('<10I', b, 0))
        nf = 4 + self.head[9]          # 실수 개수: 일본어·영어 등 5개(머리[9]=1), 번체 6개(머리[9]=2)
        self.floats = struct.unpack_from('<%df' % nf, b, 0x28)
        no = 0x28 + 4 * nf
        nl = struct.unpack_from('<I', b, no)[0]
        self.hdr_end = no + 4 + nl + 1
        self.prefix = b[:self.hdr_end]
        n = self.head[7]
        self.chars = []
        for i in range(n):
            o = self.hdr_end + i * 36
            code = struct.unpack_from('<I', b, o)[0]
            f = list(struct.unpack_from('<6f', b, o + 4))
            p1, p2 = struct.unpack_from('<II', b, o + 28)
            self.chars.append(dict(code=code, f=f, page=p1 & 0xFF, x=(p1 >> 8) & 0xFFF, y=p1 >> 20, p2=p2))
        self.tail = b[self.hdr_end + n * 36:]
        self.by_code = {c['code']: c for c in self.chars}

    @property
    def pages(self):
        return self.head[6]

    def build(self):
        chars = sorted(self.chars, key=lambda c: c['code'])
        prefix = bytearray(self.prefix)
        struct.pack_into('<I', prefix, 6 * 4, self.head[6])
        struct.pack_into('<I', prefix, 7 * 4, len(chars))
        out = bytearray(prefix)
        for c in chars:
            p1 = (c['page'] & 0xFF) | (c['x'] & 0xFFF) << 8 | (c['y'] & 0xFFF) << 20
            out += struct.pack('<I6fII', c['code'], *c['f'], p1, c['p2'])
        return bytes(out) + self.tail
