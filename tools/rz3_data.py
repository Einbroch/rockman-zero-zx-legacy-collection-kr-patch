"""GBA RZ3 한글 롬(rz3/build_dialogue.py 산출물)에서 모듈 데이터 kohook/data/rz3.bin 을 만든다(형식: tools/zcblob.py).
- 대사 20뱅크: 한글 롬의 뱅크 포인터표를 따라 확장 영역을 그대로 가져온다.
- 시스템 표(1,096칸): GBA 와 같은 구조 — 오프셋표 기준 text_base = NATIVE_COPY - 0x8000, 번역 칸은 그 앞 0x8000 안(한글 구간),
  안 바꾼 칸은 0x8000 + 원래 오프셋(원문 사본, 원래 인코딩). 초기화 훅이 main 변수(0x30acc80/88)를 이 표로 바꾼다.
사용: python tools/rz3_data.py [_work/rz3_kr.gba]"""
import os, struct, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import zcblob

KR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_work', 'rz3_kr.gba')
JP = r'D:\Games\Kor Patch\CLude\Rockman Zero\roms\Rockman Zero 3 (Japan).gba'
IMG = os.path.join(ROOT, '_work', 'exefs_upd', 'main.img')
GBA = 0x08000000
GTAB_AT = 0x801000
OFFTAB_PTRS, TEXT_PTRS, NBANKS = 0x3767B8, 0x376808, 20
SYS_OT, SYS_TEXT = 0x372210, 0x372AA0
NATIVE_COPY = 0xF00000
MAIN_SYS_OT, MAIN_SYS_TEXT = 0x2832796, 0x283302a
MAIN_BANK_OT, MAIN_BANK_BODY = 0x28eb2d0, 0x28eb370

rom = open(KR, 'rb').read(); src = open(JP, 'rb').read(); img = open(IMG, 'rb').read()
def fail(m): print('rz3_data FAIL', m); sys.exit(1)
u32 = lambda b, o: struct.unpack_from('<I', b, o)[0]
if zlib.crc32(src) != 0x5A2C41A9: fail('일본판 CRC')
if not rom[0x800800:].startswith(b'RZ3 KR PATCH'): fail('한글 롬 표식 없음')

def msg_end(b, a):
    p = a
    while True:
        c = b[p]
        if c == 0xFF: return p + 1
        p += 2 if 0xF3 <= c <= 0xF8 else 1

# 글리프표·조각: 출력기 리터럴 L_GTAB 다음 칸이 L_QDAT
lit = rom.find(struct.pack('<I', GBA + GTAB_AT), 0x800000, GTAB_AT)
if lit < 0: fail('글리프표 리터럴')
qdat_at = u32(rom, lit + 4) - GBA
if not GTAB_AT < qdat_at < GTAB_AT + 0x4000: fail('조각 위치')
gtab = rom[GTAB_AT:qdat_at]
ents = struct.unpack(f'<{len(gtab) // 4}I', gtab)
nq = max((e & 0xFFFF) + ((e >> 16) & 0x7FFF) for e in ents)
qdat = rom[qdat_at:qdat_at + nq * 32]
if qdat[:32] != bytes(32): fail('조각 0 이 빈 조각이 아님')

# 컬렉션판이 일본어 대사에서 뒤쪽 쪽을 뺀 칸은 한글도 같은 쪽 수에서 끝낸다(그 밖의 차이는 실패)
import nso
_m = nso.Img(IMG)
cuts = zcblob.native_cuts(src, img, _m.relocs(), OFFTAB_PTRS, TEXT_PTRS, NBANKS, MAIN_BANK_OT, MAIN_BANK_BODY, 'RZ3')
rom = bytearray(rom)
zcblob.apply_cuts(rom, cuts, OFFTAB_PTRS, TEXT_PTRS)
rom = bytes(rom)
print('rz3: 컬렉션판 쪽 줄임', {f'{i:02X}{s:02X}': k for (i, s), k in cuts.items()})

# 대사 뱅크
banks, lo, hi = [], len(rom), 0
for i in range(NBANKS):
    ot = u32(rom, OFFTAB_PTRS + 4 * i) - GBA; body = u32(rom, TEXT_PTRS + 4 * i) - GBA
    jo = u32(src, OFFTAB_PTRS + 4 * i) - GBA; jb = u32(src, TEXT_PTRS + 4 * i) - GBA
    if ot < 0x800000: fail(f'뱅크 {i} 가 확장 영역에 없음')
    if (body - ot) != (jb - jo): fail(f'뱅크 {i} 슬롯 수 다름')
    for s in range((body - ot) // 2):
        hi = max(hi, msg_end(rom, body + struct.unpack_from('<H', rom, ot + 2 * s)[0]))
    lo = min(lo, ot)
    banks.append((ot, body))

# 시스템 표
count = (SYS_TEXT - SYS_OT) // 2
joffs = struct.unpack_from(f'<{count}H', src, SYS_OT)
last = max(joffs)
end = SYS_TEXT + last + src[SYS_TEXT + last:].index(0xFF) + 1
original = src[SYS_TEXT:end]
if img[MAIN_SYS_OT:MAIN_SYS_OT + 2 * count] != src[SYS_OT:SYS_TEXT]: fail('main 시스템 오프셋표 ≠ 일본판')
if img[MAIN_SYS_TEXT:MAIN_SYS_TEXT + len(original)] != original: fail('main 시스템 본문 ≠ 일본판')
text_base = NATIVE_COPY - 0x8000
table = NATIVE_COPY + ((len(original) + 3) & ~3)
if rom[NATIVE_COPY:NATIVE_COPY + len(original)] != original: fail('한글 롬 원문 사본 불일치')
koffs = struct.unpack_from(f'<{count}H', rom, table)
translated = 0
for s, (ko, jo) in enumerate(zip(koffs, joffs)):
    if ko >= 0x8000:
        if ko != 0x8000 + jo: fail(f'시스템 S{s:03X} 미번역 칸이 옮겨짐')
    else:
        if msg_end(rom, text_base + ko) > NATIVE_COPY: fail(f'시스템 S{s:03X} 번역이 원문 사본과 겹침')
        translated += 1
sys_region = bytearray(rom[text_base:NATIVE_COPY + len(original)])
sys_table = bytearray(rom[table:table + 2 * count])

# 오프닝 스크롤(S00A): 일본어는 줄 앞 공백으로 가운데를 맞추는데, GBA 한글판은 줄 타일을 미리 가운데로 합성해(scroll.py)
# 번역문엔 앞 공백이 없다 → 컬렉션은 출력기로 그리므로 왼쪽에 붙는다. 줄마다 일본어 줄의 가운데에 오도록
# 한글 공백(4px)을 앞에 붙인 사본을 번역 창 빈자리에 쓰고 S00A 오프셋을 옮긴다(2편 rz2_data 와 같은 기준).
SCROLL_SLOT, KR_SPACE = 0x0A, b'\xec\x04'
def _glyph_w(b, i):
    c = b[i]
    if 0xEC <= c <= 0xEF:
        return ((ents[((c - 0xEC + 2) << 8) + b[i + 1]] >> 16) & 0x7FFF) * 4, 2
    if 0xF3 <= c <= 0xF8:
        return 0, 2
    return ((ents[c] >> 16) & 0x7FFF) * 4, 1
def _jp_cols(line):   # (앞 공백 칸, 전체 칸) — 8px 칸
    lead = len(line) - len(line.lstrip(b'\x00'))
    i = cols = 0
    while i < len(line):
        i += 2 if line[i] == 0xF0 else 1
        cols += 1
    return lead, cols
_ka = text_base + koffs[SCROLL_SLOT]
_kr_lines = rom[_ka:msg_end(rom, _ka) - 1].split(b'\xfc')
_ja = SYS_TEXT + joffs[SCROLL_SLOT]
_jp_lines = src[_ja:msg_end(src, _ja) - 1].split(b'\xfc')
if len(_kr_lines) != len(_jp_lines): fail(f'오프닝 줄 수 불일치 {len(_kr_lines)} != {len(_jp_lines)}')
_out = []
for jl, kl in zip(_jp_lines, _kr_lines):
    if not kl or kl.startswith(KR_SPACE) or kl[:1] == b'\x00':
        if kl and not jl: fail('오프닝: 일본어 빈 줄에 한글')
        _out.append(kl)
        continue
    width, i = 0, 0
    while i < len(kl):
        w, n = _glyph_w(kl, i); width += w; i += n
    lead, cols = _jp_cols(jl)
    center = (lead + (cols - lead) / 2) * 8 if jl.strip(b'\x00') else 120
    pad = max(0, round((center - width / 2) / 4))
    if pad * 4 + width > 240: fail(f'오프닝 줄 폭 초과 ({width}px)')
    _out.append(KR_SPACE * pad + kl)
_scroll = b'\xfc'.join(_out) + b'\xff'
_free = (max(msg_end(rom, text_base + k) for k in koffs if k < 0x8000) - text_base + 3) & ~3
if _free + len(_scroll) > 0x8000 or any(b != 0xFF for b in sys_region[_free:_free + len(_scroll)]):
    fail('오프닝 사본 자리 없음')
sys_region[_free:_free + len(_scroll)] = _scroll
struct.pack_into('<H', sys_table, 2 * SCROLL_SLOT, _free)
print(f'rz3: opening {len(_out)} lines centred ({len(_scroll)} B at window {_free:#x})')
sys_region = bytes(sys_region)

dialogue = rom[lo:hi]
text = dialogue + sys_region
kr_len = len(dialogue) + 0x8000          # 한글 구간: 대사 + 시스템 번역 창
blob = zcblob.pack(b"RZ3K", gtab, qdat, text, kr_len, [], bytes(sys_table), len(dialogue),
                   [(ot - lo, body - lo) for ot, body in banks])
out = os.path.join(ROOT, 'kohook', 'data', 'rz3.bin')
open(out, 'wb').write(blob)
print(f'rz3: glyphs {len(ents):#x} quanta {nq} dialogue {len(dialogue)} B, system {translated}/{count} translated -> {out} ({len(blob)} B)')
