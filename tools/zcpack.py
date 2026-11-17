"""ZC/DATA/*.bin 묶음: u32 개수, u32 오프셋[개수](bit31 = GBA LZ10 압축), 끝은 파일 끝."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lz77


def entries(buf):
    n = struct.unpack_from('<I', buf, 0)[0]
    offs = struct.unpack_from(f'<{n}I', buf, 4)
    out = []
    for i, o in enumerate(offs):
        start = o & 0x7fffffff
        end = (offs[i + 1] & 0x7fffffff) if i + 1 < n else len(buf)
        comp = bool(o >> 31)
        raw = buf[start:end]
        out.append((start, end, comp, lz77.decompress(raw)[0] if comp and raw else raw))
    return out


if __name__ == '__main__':
    for p in sys.argv[1:]:
        b = open(p, 'rb').read()
        for i, (s, e, c, d) in enumerate(entries(b)):
            print(os.path.basename(p), i, hex(s), hex(e), 'LZ' if c else 'raw', hex(len(d)))
