"""GBA RZ1 한글 롬(rz1/build.py 산출물)에서 모듈 데이터 kohook/data/rz1.bin 을 만든다.
머리(u32): 'RZ1K', ngtab, gtab_off, qdat_off, nquanta, text_off, text_len, 그다음 뱅크 19개 (ot, body), 시스템 (ot, body)
— ot/body 는 text 블롭 기준 오프셋. 사용: python tools/rz1_data.py [_work/rz1_kr.gba]"""
import os, struct, sys, zlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_work', 'rz1_kr.gba')
JP = r'D:\Games\Kor Patch\CLude\Rockman Zero\roms\Rockman Zero (Japan).gba'
GTAB_AT = 0x801000
rom = open(KR, 'rb').read(); src = open(JP, 'rb').read()
assert zlib.crc32(src) == 0xff2a67b1
def fail(m): print('FAIL', m); sys.exit(1)
# 글리프표 길이: 0x80 부터 이어지는 0 아닌 항목
n = 0x80
while struct.unpack_from('<I', rom, GTAB_AT + 4 * n)[0] != 0: n += 1
gtab = rom[GTAB_AT:GTAB_AT + 4 * n]
qdat_at = GTAB_AT + (n * 4 + 0xF) // 0x10 * 0x10
if rom[qdat_at:qdat_at + 96] != bytes(96): fail('qdat 시작(빈 조각 3개) 불일치')
nq = max(((g & 0xFFFF) + ((g >> 16) & 0x7FFF)) for (g,) in struct.iter_unpack('<I', gtab))
# 컬렉션판 일본어 대사가 GBA 일본판과 칸마다 같은지(쪽 줄임 등 차이가 생기면 1편도 자르기 처리가 필요 — 지금은 실패로)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zcblob, nso
_m = nso.Img()
if zcblob.native_cuts(src, _m.b, _m.relocs(), 0x2bad84, 0x2badd0, 19, 0x28eaee0, 0x28eaf78, 'RZ1'): fail('컬렉션판 1편 대사가 GBA 와 다름')
banks = []
for b in range(19):
    ot = struct.unpack_from('<I', rom, 0x2bad84 + 4 * b)[0] - 0x08000000
    tb = struct.unpack_from('<I', rom, 0x2badd0 + 4 * b)[0] - 0x08000000
    banks.append((ot, tb))
hit = src.find(struct.pack('<I', 0x082b8ef0)); hit2 = src.find(struct.pack('<I', 0x082b92de))
sys_ot = struct.unpack_from('<I', rom, hit)[0] - 0x08000000
sys_tb = struct.unpack_from('<I', rom, hit2)[0] - 0x08000000
banks.append((sys_ot, sys_tb))
text_at = min(x for p in banks for x in p)
if text_at < qdat_at + nq * 32: fail('대사가 조각 데이터와 겹침')
end = text_at
while rom[end:end + 0x100] != b'\xff' * 0x100: end += 0x100
qdat = rom[qdat_at:qdat_at + nq * 32]; text = rom[text_at:end]
hdr_len = 4 * 7 + 8 * 20
hdr_len = (hdr_len + 15) // 16 * 16
off_g = hdr_len; off_q = off_g + len(gtab); off_t = off_q + len(qdat)
hdr = struct.pack('<4s6I', b'RZ1K', n, off_g, off_q, nq, off_t, len(text))
for ot, tb in banks: hdr += struct.pack('<II', ot - text_at, tb - text_at)
hdr = hdr.ljust(hdr_len, b'\0')
out = os.path.join(ROOT, 'kohook', 'data', 'rz1.bin')
open(out, 'wb').write(hdr + gtab + qdat + text)
print(f'glyphs {n:#x} quanta {nq} text {len(text)} bytes -> {out} ({os.path.getsize(out)} B)')

# 결과 화면: 8px 글꼴(0x800, 실·패·성·공 4칸만 바뀜) + 칭호 20개(대사 인코딩, 0xFF 끝) → kohook/data/rz1_result.bin
# 형식: [0x000] 글꼴 0x800, [0x800] u32 칭호 오프셋[20](파일 기준), 그 뒤 문자열
STATUS_CODES = (bytes([0xBC, 0xAF]), bytes([0xBE, 0xB2]))   # 실패, 성공 (원래 シッパイ·セイコウ 의 앞 두 칸)
NATIVE_FONT = 0x215687c
lw = struct.unpack_from('<I', rom, 0xBBFDC + 4)[0]
if rom[0xBBFDC:0xBBFE0] != bytes.fromhex('004b1847') or not lw & 1: fail('결과 글꼴 로더 훅 없음')
font_at = (lw & ~1) - 0x08000000 + 0x40
jp_font = src[0xD169C:0xD1E9C]; kr_font = rom[font_at:font_at + 0x800]
diff = sorted({i // 32 for i in range(0x800) if jp_font[i] != kr_font[i]})
if diff != sorted(c[k] - 0xA0 for c in STATUS_CODES for k in range(2)): fail(f'결과 글꼴 바뀐 칸 {diff}')
img = open(os.path.join(ROOT, '_work', 'exefs_upd', 'main.img'), 'rb').read()
if img[NATIVE_FONT:NATIVE_FONT + 0x800] != jp_font: fail('main 8px 글꼴이 일본 롬과 다름')
for i, c in enumerate(STATUS_CODES):
    p = struct.unpack_from('<I', rom, 0x2C62C8 + 4 * i)[0] - 0x08000000
    if rom[p:p + 3] != c + b'\0': fail('결과 상태 문자열 불일치')
titles = []
for i in range(20):
    p = struct.unpack_from('<I', rom, 0x29F9F0 + 4 * i)[0] - 0x08000000
    e = rom.index(b'\xff', p)
    titles.append(rom[p:e + 1])
blob = bytearray(kr_font) + bytes(80)
for i, t in enumerate(titles):
    struct.pack_into('<I', blob, 0x800 + 4 * i, len(blob))
    blob += t
out = os.path.join(ROOT, 'kohook', 'data', 'rz1_result.bin')
open(out, 'wb').write(blob)
print(f'result font tiles {diff}, titles {len(titles)} -> {out} ({len(blob)} B)')
