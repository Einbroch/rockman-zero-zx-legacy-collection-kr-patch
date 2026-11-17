"""RZ1 그림 글자: GBA 한글 빌드(_work/rz1_kr.gba)가 바꾼 그래픽 바이트를 컬렉션 RomFS ZC/DATA/*_z1.bin 에 옮긴다.

ZC/DATA 묶음 항목은 GBA 롬 구간을 (0x14 머리 + 본문) 형태로 담고 있다(일부 바이트는 컬렉션판이 고침).
- 선형 대응: 항목 오프셋 = 롬 주소 - base. GBA 빌드가 바꾼 바이트마다 컬렉션 바이트가 일본 롬과 같아야 옮긴다.
  다르면(컬렉션판이 이미 고친 바이트) 충돌로 세고, 허용 목록에 없는 구간이면 빌드 실패.
- 무기 라벨(obj_fnt 175)은 1D 스프라이트 배치로 재배열돼 있어 타일 단위 표로 옮긴다.
출력: build/romfs/nativeNXx64/RZZC/ZC/DATA/<파일> (바뀐 항목만 VRAM 안전 LZ 로 재압축, 나머지 원본 바이트 통과)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lz77
import zcpack

JP_ROM = os.path.join(ROOT, '..', 'Rockman Zero', 'roms', 'Rockman Zero (Japan).gba')
KR_ROM = os.path.join(ROOT, '_work', 'rz1_kr.gba')
SRC = os.path.join(ROOT, '_work', 'romfs', 'nativeNXx64', 'RZZC', 'ZC', 'DATA')
OUT = os.path.join(ROOT, 'build', 'romfs', 'nativeNXx64', 'RZZC', 'ZC', 'DATA')

# (파일, 항목, base, 롬 구간 lo, hi, 충돌 허용)
LINEAR = [
    ('sub_z1', 0, 0x2F5C00, 0x2F5C14, 0x2FDD94, False),       # 서브 화면 라벨·칭호·옵션
    ('sub_elf_z1', 0, 0x2F5C00, 0x2F5C14, 0x2FDD94, False),   # 엘프 화면에서 같은 그림
    ('result_z1', 0, 0x2FFC20, 0x2FFC34, 0x303CF4, False),    # 결과 화면 라벨
    ('title_z1', 0, 0x2F121C, 0x2F1294, 0x2F5B54, 'merge'),   # 타이틀 로고: 컬렉션판이 배경·저작권 줄·® 를 지움 → 한글 바뀐 바이트를 덮고 ® 지움은 옮긴다
    ('title_z1', 0, 0x303FDC, 0x308914, 0x30E014, False),     # 타이틀 메뉴 글자
]

# 무기 라벨: GBA 타일 번호(0x532C94 + t*32) -> obj_fnt 항목 175 안 오프셋
WEAPON_BASE = 0x532C94
WEAPON = {0: 0x114, 1: 0x134, 2: 0x154, 3: 0x174, 4: 0x794,
          16: 0x194, 17: 0x1b4, 18: 0x1d4, 19: 0x1f4, 20: 0x7b4,
          6: 0x234, 7: 0x254, 8: 0x274, 9: 0x994,      # 9 는 0x634(타일 42 사본)와 같은 그림 — 8x16 짝(9,25)=0x994/0x9b4
          22: 0x2b4, 23: 0x2d4, 24: 0x2f4,
          28: 0x334, 29: 0x354, 30: 0x374,
          44: 0x3b4, 45: 0x3d4, 46: 0x3f4}


def fail(msg):
    print('rz1_gfx: ' + msg, file=sys.stderr)
    sys.exit(1)


def rebuild(buf, new_entries):
    """new_entries: {항목: 해제 데이터}. 안 바뀐 항목은 원본 바이트 그대로."""
    ents = zcpack.entries(buf)
    n = len(ents)
    hdr = 4 + 4 * n
    first = ents[0][0]
    out = bytearray(buf[:first])
    offs = []
    for i, (s, e, comp, data) in enumerate(ents):
        while len(out) % 4:
            out.append(0)
        offs.append(len(out) | (0x80000000 if comp else 0))
        if i in new_entries:
            if not comp:
                out += new_entries[i]
            else:
                c = lz77.compress(new_entries[i])
                if lz77.decompress(c)[0] != new_entries[i]:
                    fail('LZ 왕복 실패')
                out += c
        else:
            out += buf[s:e]
    struct.pack_into(f'<{n}I', out, 4, *offs)
    assert hdr <= first
    return bytes(out)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    jp = open(JP_ROM, 'rb').read()
    kr = open(KR_ROM, 'rb').read()
    work = {}  # 파일 -> {항목: bytearray}

    def entry(fn, i):
        if fn not in work:
            work[fn] = (open(os.path.join(SRC, fn + '.bin'), 'rb').read(), {})
        buf, ch = work[fn]
        if i not in ch:
            ch[i] = bytearray(zcpack.entries(buf)[i][3])
        return ch[i]

    total = 0
    for fn, i, base, lo, hi, allow in LINEAR:
        d = entry(fn, i)
        hi = min(hi, base + len(d))
        moved = conflict = 0
        for a in range(lo, hi):
            if kr[a] == jp[a]:
                continue
            o = a - base
            if d[o] != jp[a]:
                conflict += 1
                if allow != 'merge':
                    continue
            d[o] = kr[a]
            moved += 1
        if conflict and not allow:
            fail(f'{fn}#{i} {base:#x}: 컬렉션판과 다른 바이트 {conflict}개')
        print(f'{fn}#{i} {lo:#x}-{hi:#x}: {moved} 바이트, 충돌 {conflict}' + (' (한글 바이트로 덮음)' if allow == 'merge' else ''))
        if fn == 'title_z1' and lo == 0x2F1294:   # 로고: 컬렉션이 지운 ® 를 한글 ® 자리에서도 지운다
            coll = zcpack.entries(work[fn][0])[i][3]
            ent = struct.unpack_from('<1024H', jp, 0x2E008C)
            at = lambda x, y: 0x2F1294 + (ent[(y // 8) * 32 + x // 8] & 0x3FF) * 64 + (y % 8) * 8 + x % 8
            def setter(a, v, d=d, base=base):
                d[a - base] = v
            import rz2_gfx   # rz2_gfx 가 이 모듈의 rebuild 를 가져가므로 여기서 늦게
            rz2_gfx.move_registered_erase(1, jp.__getitem__, kr.__getitem__, lambda a: coll[a - base], setter, at, 'title_z1 로고')
        total += moved

    # 무기 라벨
    d = entry('obj_fnt_z1', 175)
    for t in range(48):
        a = WEAPON_BASE + t * 32
        if kr[a:a + 32] == jp[a:a + 32]:
            continue
        if t not in WEAPON:
            fail(f'무기 라벨 타일 {t} 대응 없음')
        o = WEAPON[t]
        if d[o:o + 32] != jp[a:a + 32]:
            fail(f'무기 라벨 타일 {t} 원본 불일치')
        d[o:o + 32] = kr[a:a + 32]
        total += 32
    # 바뀐 GBA 타일은 모두 표에 있어야 한다 (표에 있는데 안 바뀐 것도 없어야)
    changed = {t for t in range(48) if kr[WEAPON_BASE + t * 32:WEAPON_BASE + t * 32 + 32] != jp[WEAPON_BASE + t * 32:WEAPON_BASE + t * 32 + 32]}
    if changed != set(WEAPON):
        fail(f'무기 라벨 표 불일치: {sorted(changed ^ set(WEAPON))}')

    os.makedirs(OUT, exist_ok=True)
    for fn, (buf, ch) in work.items():
        orig = zcpack.entries(buf)
        news = {i: bytes(v) for i, v in ch.items() if bytes(v) != orig[i][3]}
        if not news:
            fail(f'{fn}: 바뀐 것 없음')
        out = rebuild(buf, news)
        # 되읽기: 바뀐 항목은 새 데이터, 나머지는 원본과 같아야
        back = zcpack.entries(out)
        for k, (s, e, c, dd) in enumerate(back):
            want = news.get(k, orig[k][3])
            if dd != want or c != orig[k][2]:
                fail(f'{fn}#{k} 되읽기 불일치')
        open(os.path.join(OUT, fn + '.bin'), 'wb').write(out)
        print(f'{fn}.bin: 항목 {sorted(news)} 교체, {len(buf):#x} -> {len(out):#x}')
    print(f'합계 {total} 바이트')


if __name__ == '__main__':
    main()
