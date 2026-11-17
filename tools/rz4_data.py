"""GBA RZ4 한글 롬(rz4/build_dialogue.py 산출물)에서 모듈 데이터 kohook/data/rz4.bin 을 만든다(형식: tools/zcblob.py).
GBA 4편은 롬이 이미 16MB 라 확장 영역이 없고, 원래 대사 창 [klo, khi) 를 한글 구간으로 쓴다. 시스템 표는 제자리(0x86CFF8)에서
원래 본문(0x86D6B4) 기준 오프셋 — 번역 칸은 한글 구간 안, 나머지는 원문. 그래서 text 블롭 = 롬 [SYS_TEXT, khi),
한글 구간 = [klo, khi), 뱅크·시스템 본문 모두 SYS_TEXT 기준.
사용: python tools/rz4_data.py [_work/rz4_kr.gba]"""
import os, struct, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import zcblob

KR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_work', 'rz4_kr.gba')
JP = r'D:\Games\Kor Patch\CLude\Rockman Zero\roms\Rockman Zero 4 (Japan).gba'
IMG = os.path.join(ROOT, '_work', 'exefs_upd', 'main.img')
GBA = 0x08000000
OFFTAB_PTRS, TEXT_PTRS, NBANKS = 0x870C74, 0x870CCC, 22
SYS_OT, SYS_TEXT, SYS_SLOTS = 0x86CFF8, 0x86D6B4, 862
MAIN_SYS_OT, MAIN_SYS_TEXT = 0x283ba6c, 0x283c12c
MAIN_BANK_OT, MAIN_BANK_BODY = 0x28eb6d0, 0x28eb780
WINDOW = (0x870DBC, 0x8A7000)   # GBA rz4 WINDOW_FULL

rom = bytearray(open(KR, 'rb').read()); src = open(JP, 'rb').read(); img = open(IMG, 'rb').read()
def fail(m): print('rz4_data FAIL', m); sys.exit(1)
u32 = lambda b, o: struct.unpack_from('<I', b, o)[0]
if zlib.crc32(src) != 0xECE42D0E: fail('일본판 CRC')
mk = rom.find(b'RZ4 KR PATCH')
if mk < 0: fail('한글 롬 표식 없음')

# 한글 구간: 출력기·스캐너 리터럴 (klo, khi) — 창 전체판이어야 한다
klo, khi = WINDOW
if rom.find(struct.pack('<II', GBA + klo, GBA + khi)) < 0: fail('한글 구간 리터럴(창 전체) 없음')

# 글리프표: 표식 뒤 16바이트 정렬, 출력기 리터럴 L_GTAB 다음 칸이 L_QDAT
marker_end = rom.index(0xFF, mk)
gtab_at = (marker_end + 15) & ~15
lit = rom.find(struct.pack('<I', GBA + gtab_at))
if lit < 0: fail('글리프표 리터럴')
qdat_at = u32(rom, lit + 4) - GBA
# 표 끝 = 빈 롬(0xFFFFFFFF)이 시작되는 곳 (확장 코드 0x200~ 마지막 글자 다음)
ents = []
while u32(rom, gtab_at + 4 * len(ents)) != 0xFFFFFFFF:
    ents.append(u32(rom, gtab_at + 4 * len(ents)))
last = len(ents) - 1
if last < 0x200 or any(e and not 1 <= (e >> 16) & 0x7FFF <= 4 for e in ents): fail('글리프표 형식')
gtab = bytes(rom[gtab_at:gtab_at + 4 * (last + 1)])
ents = ents[:last + 1]
nq = max((e & 0xFFFF) + ((e >> 16) & 0x7FFF) for e in ents)
qdat = bytes(rom[qdat_at:qdat_at + nq * 32])
if qdat[:32] != bytes(32): fail('조각 0 이 빈 조각이 아님')

# 컬렉션판 대사 차이(쪽 줄임)는 한글도 같이 자른다
import nso
_m = nso.Img(IMG)
cuts = zcblob.native_cuts(src, img, _m.relocs(), OFFTAB_PTRS, TEXT_PTRS, NBANKS, MAIN_BANK_OT, MAIN_BANK_BODY, 'RZ4')
zcblob.apply_cuts(rom, cuts, OFFTAB_PTRS, TEXT_PTRS)
print('rz4: 컬렉션판 차이', {f'{i:02X}{s:02X}': k for (i, s), k in cuts.items()})

banks = []
for i in range(NBANKS):
    ot = u32(rom, OFFTAB_PTRS + 4 * i) - GBA; body = u32(rom, TEXT_PTRS + 4 * i) - GBA
    jo = u32(src, OFFTAB_PTRS + 4 * i) - GBA; jb = u32(src, TEXT_PTRS + 4 * i) - GBA
    if not (klo <= ot < body < khi): fail(f'뱅크 {i} 가 한글 구간 밖')
    if (body - ot) != (jb - jo): fail(f'뱅크 {i} 슬롯 수 다름')
    for s in range((body - ot) // 2):
        if zcblob.msg_end(rom, body + struct.unpack_from('<H', rom, ot + 2 * s)[0]) > khi: fail(f'{i:02X}{s:02X} 구간 넘침')
    banks.append((ot - SYS_TEXT, body - SYS_TEXT))

# 시스템 표
if img[MAIN_SYS_OT:MAIN_SYS_OT + 2 * SYS_SLOTS] != src[SYS_OT:SYS_OT + 2 * SYS_SLOTS]: fail('main 시스템 오프셋표 ≠ 일본판')
joffs = struct.unpack_from(f'<{SYS_SLOTS}H', src, SYS_OT)
koffs = struct.unpack_from(f'<{SYS_SLOTS}H', rom, SYS_OT)
translated = 0
for s, (ko, jo) in enumerate(zip(koffs, joffs)):
    a = SYS_TEXT + ko
    if ko == jo:
        e = zcblob.msg_end(src, SYS_TEXT + jo)
        if img[MAIN_SYS_TEXT + jo:MAIN_SYS_TEXT + jo + e - SYS_TEXT - jo] != src[SYS_TEXT + jo:e]: fail(f'S{s:03X} main 원문 ≠ 일본판')
        if rom[SYS_TEXT + jo:e] != src[SYS_TEXT + jo:e]: fail(f'S{s:03X} 한글 롬 원문 자리 바뀜')
        continue
    if not (klo <= a and zcblob.msg_end(rom, a) <= khi): fail(f'S{s:03X} 번역이 한글 구간 밖')
    translated += 1
text = bytes(rom[SYS_TEXT:khi])
blob = zcblob.pack(b'RZ4K', gtab, qdat, text, khi - klo, [], bytes(rom[SYS_OT:SYS_OT + 2 * SYS_SLOTS]), 0,
                   banks, kr_start=klo - SYS_TEXT)
out = os.path.join(ROOT, 'kohook', 'data', 'rz4.bin')
open(out, 'wb').write(blob)
print(f'rz4: glyphs {len(ents):#x} quanta {nq} window {klo:#x}-{khi:#x}, system {translated}/{SYS_SLOTS} translated -> {out} ({len(blob)} B)')
