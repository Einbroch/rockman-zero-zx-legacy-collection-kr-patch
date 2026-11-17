"""GBA RZ2 한글 롬(rz2/build_dialogue.py --screens 산출물)에서 모듈 데이터 kohook/data/rz2.bin 을 만든다.
머리 형식은 tools/zcblob.py (kohook/src/vwf.rs 와 같음).
sys 표: (main 시스템 본문 기준 원래 오프셋 u32, text 블롭 기준 번역 오프셋 u32) × nsys, 원래 오프셋 오름차순.
text 블롭 안의 글은 한글 인코딩(EC~F0 리드 + 트레일), 그 밖(main 의 글)은 원래 인코딩으로 읽는다.
사용: python tools/rz2_data.py [_work/rz2_kr.gba]"""
import os, struct, sys, zlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_work', 'rz2_kr.gba')
JP = r'D:\Games\Kor Patch\CLude\Rockman Zero\roms\Rockman Zero 2 (Japan).gba'
IMG = os.path.join(ROOT, '_work', 'exefs_upd', 'main.img')
GBA = 0x08000000
GTAB_AT = 0x801000
OFFTAB_PTRS, TEXT_PTRS, NBANKS = 0x34E0A8, 0x34E0F8, 20
SYS_OT, SYS_TEXT, SYS_END = 0x34B6DC, 0x34BC44, 0x34E09C
NATIVE_COPY = 0xF00000
MAIN_SYS_OT, MAIN_SYS_TEXT = 0x282ce5c, 0x282d3c8
MAIN_BANK_OT, MAIN_BANK_BODY = 0x28eb0b0, 0x28eb010

rom = open(KR, 'rb').read(); src = open(JP, 'rb').read(); img = open(IMG, 'rb').read()
def fail(m): print('rz2_data FAIL', m); sys.exit(1)
if zlib.crc32(src) != 0x9B5C8A4C: fail('일본판 CRC')
if not rom[0x800800:].startswith(b'RZ2 KR PATCH'): fail('한글 롬 표식 없음')
u32 = lambda b, o: struct.unpack_from('<I', b, o)[0]

# 글리프표·조각: 출력기 리터럴 L_GTAB 다음 칸이 L_QDAT
lit = rom.find(struct.pack('<I', GBA + GTAB_AT), 0x800000, GTAB_AT)
qdat_at = u32(rom, lit + 4) - GBA
if lit < 0 or not GTAB_AT < qdat_at < GTAB_AT + 0x4000: fail('글리프표 리터럴')
n = (qdat_at - GTAB_AT) // 4
gtab = rom[GTAB_AT:qdat_at]
ents = struct.unpack(f'<{n}I', gtab)
nq = max((e & 0xFFFF) + ((e >> 16) & 0x7FFF) for e in ents)
qdat = rom[qdat_at:qdat_at + nq * 32]
if qdat[:32] != bytes(32): fail('조각 0 이 빈 조각이 아님')

def msg_end(b, a):
    """메시지 끝(0xFF 포함) — F3~F8 인수는 건너뛴다(인수가 FF 일 수 있음)"""
    p = a
    while True:
        c = b[p]
        if c == 0xFF: return p + 1
        p += 2 if 0xF3 <= c <= 0xF8 else 1

# 대사 뱅크: 한글 롬의 뱅크 포인터
banks = []
lo, hi = len(rom), 0
for i in range(NBANKS):
    ot = u32(rom, OFFTAB_PTRS + 4 * i) - GBA; body = u32(rom, TEXT_PTRS + 4 * i) - GBA
    if ot < 0x800000: fail(f'뱅크 {i} 가 확장 영역에 없음')
    cnt = (body - ot) // 2
    for s in range(cnt):
        hi = max(hi, msg_end(rom, body + struct.unpack_from('<H', rom, ot + 2 * s)[0]))
    lo = min(lo, ot)
    banks.append((ot, body))
# 컬렉션판 일본어 대사와 GBA 일본판 칸마다 대조(쪽 줄임이면 한글도 자름, 그 밖의 차이는 실패)
import zcblob, nso
_m = nso.Img(IMG)
cuts = zcblob.native_cuts(src, img, _m.relocs(), OFFTAB_PTRS, TEXT_PTRS, NBANKS, MAIN_BANK_OT, MAIN_BANK_BODY, 'RZ2')
if cuts:
    rom = bytearray(rom); zcblob.apply_cuts(rom, cuts, OFFTAB_PTRS, TEXT_PTRS); rom = bytes(rom)
print('rz2: 컬렉션판 쪽 줄임', {f'{i:02X}{s:02X}': k for (i, s), k in cuts.items()})
# 뱅크 수·슬롯 수가 main 원본(일본판)과 같은지
for i in range(NBANKS):
    jo = u32(src, OFFTAB_PTRS + 4 * i) - GBA; jb = u32(src, TEXT_PTRS + 4 * i) - GBA
    ko, kb = banks[i]
    if (jb - jo) != (kb - ko): fail(f'뱅크 {i} 슬롯 수 다름')
    if img.find(src[jb:jb + 32]) < 0: fail(f'뱅크 {i} 본문이 main 에 없음')

# 시스템 문자열: 번역 칸만 (원래 오프셋 → 번역문)
if img[MAIN_SYS_OT:MAIN_SYS_OT + (SYS_TEXT - SYS_OT)] != src[SYS_OT:SYS_TEXT]: fail('main 시스템 오프셋표 ≠ 일본판')
if img[MAIN_SYS_TEXT:MAIN_SYS_TEXT + (SYS_END - SYS_TEXT) - 1] != src[SYS_TEXT:SYS_END - 1]: fail('main 시스템 본문 ≠ 일본판')   # 마지막 1바이트는 문자열 밖 패딩(컬렉션판 0xAC)
nslot = (SYS_TEXT - SYS_OT) // 2
table = NATIVE_COPY + ((SYS_END - SYS_TEXT + 3) & ~3)
text_base = NATIVE_COPY - 0x8000
if rom[NATIVE_COPY:NATIVE_COPY + SYS_END - SYS_TEXT] != src[SYS_TEXT:SYS_END]: fail('한글 롬 원문 사본 불일치')
sys_map = {}
sys_lo, sys_hi = len(rom), 0
for s in range(nslot):
    ko = struct.unpack_from('<H', rom, table + 2 * s)[0]
    jo = struct.unpack_from('<H', src, SYS_OT + 2 * s)[0]
    if ko >= 0x8000:
        if ko != 0x8000 + jo: fail(f'시스템 {s} 미번역 칸이 옮겨짐')
        continue
    a = text_base + ko
    e = msg_end(rom, a)
    sys_lo, sys_hi = min(sys_lo, a), max(sys_hi, e)
    if sys_map.get(jo, a) != a: fail(f'시스템 원래 오프셋 {jo:#x} 를 서로 다른 번역이 공유')
    sys_map[jo] = a
if sys_hi > NATIVE_COPY: fail('시스템 번역이 원문 사본과 겹침')

text = rom[lo:hi] + rom[sys_lo:sys_hi]
sys_new = {jo: len(rom[lo:hi]) + a - sys_lo for jo, a in sys_map.items()}

# 오프닝 스크롤 = 시스템 9번. GBA 는 미리 그린 타일로 대체해 번역문이 롬에 없다 → GBA 원고(screen_text.SCROLL)를
# GBA 와 같은 코드 배정으로 인코딩해 넣는다. 줄마다 일본어 줄의 가운데(8px 칸 기준)에 맞춘다.
RZ = r'D:\Games\Kor Patch\CLude\Rockman Zero'
for p_ in (RZ, os.path.join(RZ, 'tools'), os.path.join(RZ, 'rz2')):
    sys.path.insert(0, p_)
_cwd = os.getcwd(); os.chdir(os.path.join(RZ, 'rz2'))
import build_dialogue as bd, screen_text
from dump_sequel_text import load_map
from build_poc import kfont
_orig, _msgs = bd.load_text()
_native = load_map(bd.ROOT / 'tools/rz234_jp_charmap.txt')
_native.update({b'\xd5': ',', b'\xe4': '…', b'\xe5': '.'})
_glyphs = {raw: ch for raw, ch in _native.items() if raw[0] not in bd.LEADS}
_screen = screen_text.translations()
_visible = {c for t in (*_msgs.values(), *_screen.values()) for c in bd.CONTROLS.sub('', t) if c != '\n'}
_extra = sorted(_visible.difference(_glyphs.values()))
codes = {ch: raw for raw, ch in _glyphs.items()}
codes.update({ch: bytes((0xEC + i // 0xF0, i % 0xF0)) for i, ch in enumerate(_extra)})
codes['\n'] = b'\xfc'
os.chdir(_cwd)
# 코드 배정 검사: 번역된 시스템 칸을 이 배정으로 인코딩하면 한글 롬 바이트와 같아야 한다
_checked = 0
for slot, wording in _screen.items():
    ko = struct.unpack_from('<H', rom, table + 2 * slot)[0]
    if ko >= 0x8000:
        continue
    a = text_base + ko
    got = rom[a:msg_end(rom, a)]
    if got.startswith(b'\xf7'):
        got = got[2:]
    if bd.encode(wording + '{end}', codes) != got:
        fail(f'코드 배정 불일치 (시스템 {slot})')
    _checked += 1
if _checked < 300: fail('코드 배정 검사 칸 수 부족')
# 새 글자(오프닝에만 쓰는 글자): 다음 확장 코드 + 갈무리11 12px 조각
_bdf = kfont.load_bdf(bd.ROOT / 'external/fonts/Galmuri11.bdf')
_w, _px = kfont.render(_bdf, '부', 12)
_e = struct.unpack_from('<I', gtab, 4 * (((codes['부'][0] - 0xEC + 2) << 8) + codes['부'][1]))[0]
if bytes(kfont.to_quanta(_w, _px)) != qdat[(_e & 0xFFFF) * 32:((_e & 0xFFFF) + ((_e >> 16) & 0x7FFF)) * 32]:
    fail('갈무리11 렌더가 한글 롬 글리프와 다름')
gtab = bytearray(gtab); qdat = bytearray(qdat)
new_chars = sorted({c for line in screen_text.SCROLL for c in line} - set(codes))
for k, ch in enumerate(new_chars):
    i = len(_extra) + k
    raw = bytes((0xEC + i // 0xF0, i % 0xF0))
    if raw[0] > 0xF0: fail('확장 코드 고갈')
    g = ((raw[0] - 0xEC + 2) << 8) + raw[1]
    w, px = kfont.render(_bdf, ch, 12 if '가' <= ch <= '힣' else 8)
    q = kfont.to_quanta(w, px)
    while len(gtab) < 4 * (g + 1):
        gtab += bytes(4)
    struct.pack_into('<I', gtab, 4 * g, len(qdat) // 32 | (w // 4) << 16)
    qdat += bytes(q)
    codes[ch] = raw
n = len(gtab) // 4
nq = len(qdat) // 32
_jp9 = src[SYS_TEXT + 29:msg_end(src, SYS_TEXT + 29) - 1].split(b'\xfc')
if len(_jp9) != len(screen_text.SCROLL): fail('오프닝 줄 수 불일치')
def _cols(line):   # (앞 공백 칸, 전체 칸) — 8px 칸
    lead = len(line) - len(line.lstrip(b'\x00'))
    i = cols = 0
    while i < len(line):
        i += 2 if line[i] == 0xF0 else 1
        cols += 1
    return lead, cols
_lines = []
for jl, kl in zip(_jp9, screen_text.SCROLL):
    lead, cols = _cols(jl)
    if not kl:
        _lines.append(b'')
        continue
    width = sum(12 if '가' <= c <= '힣' else 8 for c in kl)
    center = (lead + (cols - lead) / 2) * 8
    pad = max(0, round((center - width / 2) / 8))
    if pad * 8 + width > 240: fail(f'오프닝 줄 폭 초과: {kl}')
    _lines.append(codes[' '] * pad + bd.encode(kl, codes))
scroll = b'\xfc'.join(_lines) + b'\xff'
if 29 in sys_new: fail('시스템 9번이 이미 번역돼 있음')
sys_new[29] = len(text)
text += scroll
print(f'opening: {len(_lines)} lines, new glyphs {new_chars}, code check {_checked} slots')
sys_pairs = sorted(sys_new.items())
import zcblob   # 공용 머리 형식 (kohook/src/vwf.rs)
blob = zcblob.pack(b'RZ2K', bytes(gtab), bytes(qdat), text, len(text), sys_pairs, None, None,
                   [(ot - lo, body - lo) for ot, body in banks])
out = os.path.join(ROOT, 'kohook', 'data', 'rz2.bin')
open(out, 'wb').write(blob)
print(f'rz2: glyphs {n:#x} quanta {nq} dialogue {hi - lo} B, system {len(sys_pairs)} slots {sys_hi - sys_lo} B -> {out} ({len(blob)} B)')
