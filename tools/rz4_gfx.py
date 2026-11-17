"""RZ4 그림 글자: GBA 4편 한글 롬(_work/rz4_kr.gba)의 그림을 컬렉션 RomFS ZC/DATA/*_z4.bin 에 옮긴다.
1) 압축 타일셋(게임오버 0xB6C7F8, 타이틀 로고 0xB6C028, 시작 안내 0xB6C03C): rz2_gfx.run 과 같은 레코드 방식.
2) 무압축 타일(일시정지 네 쪽 BG 0xB78000~0xB86000, 코드네임 0xB8FE00~, 스프라이트 라벨 0xC61000~0xC6C000, 난이도·메뉴 단어 0xCAC000~): GBA 4편은 롬 제자리에서 고쳤다.
   컬렉션 항목(sub*_z4 #0, obj_fnt_z4 #53·#65·#172)은 GBA 롬 구간을 그대로 담고 있어(한 항목에 구간 여럿), 바뀐 GBA 타일마다
   그 항목의 주된 기준점(항목 오프셋 − 롬 주소) 자리에 일본어 타일이 있으면 거기, 없으면 항목 안 유일한 일본어 타일 자리에 쓴다.
   일본어 타일이 없는 자리(컬렉션판이 고친 타일)는 건너뛰고 센다.
3) 오프닝 문단 6개(글자가 아니라 그림): opening_z4 #0 = 20바이트 레코드(GBA 서술자 0xB6CD04+20k 와 같은 꼴) + [타일][팔레트],
   #1 = 맵(GBA 0xB67908+0x788k 의 머리 8바이트만 다르고 본문 같음). 타일은 같은 크기면 제자리, 늘어나면(5번 +2타일)
   무압축 항목 끝에 붙이고 레코드의 상대 위치·크기를 고친다. 맵 본문은 크기가 같아 제자리.
출력: build/romfs/nativeNXx64/RZZC/ZC/DATA/<파일>"""
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import rz2_gfx
import zcpack
from rz1_gfx import rebuild

JP_ROM = os.path.join(ROOT, '..', 'Rockman Zero', 'roms', 'Rockman Zero 4 (Japan).gba')
KR_ROM = os.path.join(ROOT, '_work', 'rz4_kr.gba')
SRC, OUT = rz2_gfx.SRC, rz2_gfx.OUT

TILESETS = [
    ('gameover_z4', 0, 0x00, 0xB6C7F8, False),   # 게임오버
    ('title_z4', 0, 0x00, 0xB6C028, 'merge'),    # 타이틀 로고(8bpp) — 컬렉션판이 고친 타일과 겹쳐 병합
    ('title_z4', 0, 0x14, 0xB6C03C, True),       # 시작 안내
]
RAW_REGIONS = [(0xB78000, 0xB86000), (0xB8FE00, 0xB92000), (0xC61000, 0xC6C000), (0xCAC000, 0xCB1000)]   # 일시정지 네 쪽(엘프 쪽 0xB844F4~ 포함), 코드네임(결과 화면), 스프라이트 라벨, 타이틀 메뉴·난이도 단어(OBJ 시트 0xCAE368)
RAW_ENTRIES = [('sub_z4', 0), ('sub_elf_z4', 0), ('sub_mini_z4', 0), ('sub_result_z4', 0), ('sub_save_z4', 0),
               ('obj_fnt_z4', 53), ('obj_fnt_z4', 65), ('obj_fnt_z4', 172)]


def fail(msg):
    print('rz4_gfx: ' + msg, file=sys.stderr)
    sys.exit(1)


def raw_tiles(jp, kr):
    changed = [a for lo, hi in RAW_REGIONS for a in range(lo, hi, 32) if jp[a:a + 32] != kr[a:a + 32]]
    files = {}
    for fn, ei in RAW_ENTRIES:
        if fn not in files:
            files[fn] = (open(os.path.join(SRC, fn + '.bin'), 'rb').read(), {})
        buf, ch = files[fn]
        d = bytearray(zcpack.entries(buf)[ei][3])
        # 기준점: 유일하게 맞는 타일들의 (항목 오프셋 - 롬 주소) 중 5번 이상 나온 것
        votes = collections.Counter()
        for a in changed:
            o = d.find(jp[a:a + 32])
            if o >= 0 and d.find(jp[a:a + 32], o + 1) < 0:
                votes[o - a] += 1
        bases = [b for b, n in votes.most_common() if n >= 5]
        moved = skipped = merged = 0
        for a in changed:
            t = jp[a:a + 32]
            spot = None
            for b in bases:
                o = a + b
                if 0 <= o and d[o:o + 32] == t and (o - 0x14) % 4 == 0:
                    spot = o
                    break
            if spot is None:
                o = d.find(t)
                if o >= 0 and d.find(t, o + 1) < 0 and any(0 <= a + b < len(d) for b in bases):
                    # 항목이 이 롬 주소 근처 구간을 담는 경우에만(남의 타일과 우연히 같은 것 방지)
                    spot = o
            if spot is None:
                # 컬렉션판이 일부 고친 타일(단추 아이콘 자리 등): 주된 기준점 자리가 일본어 타일과 절반 이상 같으면
                # 한글판이 바꾼 바이트만 그 위에 덮는다(병합)
                o = a + bases[0] if bases else -1
                if 0 <= o <= len(d) - 32 and sum(x == y for x, y in zip(d[o:o + 32], t)) >= 16:
                    for k in range(32):
                        if jp[a + k] != kr[a + k]:
                            d[o + k] = kr[a + k]
                    merged += 1
                    continue
                if any(0 <= a + b <= len(d) - 32 for b in bases):
                    skipped += 1   # 이 항목이 담는 구간인데 일본어 타일이 아님 — 컬렉션판이 고친 타일
                continue
            d[spot:spot + 32] = kr[a:a + 32]
            moved += 1
        ch[ei] = d
        print(f'{fn}#{ei}: 기준점 {[hex(-b) for b in bases]}, 타일 {moved}개, 병합 {merged}, 건너뜀 {skipped}')
    os.makedirs(OUT, exist_ok=True)
    for fn, (buf, ch) in files.items():
        orig = zcpack.entries(buf)
        news = {i: bytes(v) for i, v in ch.items() if bytes(v) != orig[i][3]}
        if not news:
            fail(f'{fn}: 바뀐 것 없음')
        out = rebuild(buf, news)
        back = zcpack.entries(out)
        for k, (s_, e, c, dd) in enumerate(back):
            if dd != news.get(k, orig[k][3]) or c != orig[k][2]:
                fail(f'{fn}#{k} 되읽기 불일치')
        open(os.path.join(OUT, fn + '.bin'), 'wb').write(out)
        print(f'{fn}.bin: 항목 {sorted(news)} 교체')


def opening(jp, kr):
    import struct
    buf = open(os.path.join(SRC, 'opening_z4.bin'), 'rb').read()
    ents = zcpack.entries(buf)
    if ents[0][2]:
        fail('opening_z4 #0 이 압축 항목 — 끝에 붙이기 불가')
    d0, d1 = bytearray(ents[0][3]), bytearray(ents[1][3])
    for k in range(6):
        gd = 0xB6CD04 + 20 * k
        w, kw = struct.unpack_from('<5I', jp, gd), struct.unpack_from('<5I', kr, gd)
        ta, n = gd + 8 + w[2], w[3]
        kta, kn = gd + 8 + kw[2], kw[3]
        pos = d0.find(jp[ta:ta + n])
        rec = 0x3C + 0x14 * k
        if pos < 0 or d0.find(jp[ta:ta + n], pos + 1) >= 0:
            fail(f'오프닝 {k}: 타일 자리 {pos:#x}')
        rrel, rsize = struct.unpack_from('<II', d0, rec)
        if rec + rrel != pos or rsize & 0x3FFFFF != n:
            fail(f'오프닝 {k}: 레코드 {rec:#x} 불일치')
        if kn == n:
            d0[pos:pos + n] = kr[kta:kta + kn]
            where = '제자리'
        else:
            while len(d0) % 4:
                d0.append(0)
            new_at = len(d0)
            d0 += kr[kta:kta + kn]
            struct.pack_into('<II', d0, rec, new_at - rec, (rsize & ~0x3FFFFF) | kn)
            where = f'끝에 붙임({n:#x}->{kn:#x})'
        mp = 0xB67908 + 0x788 * k
        mpos = d1.find(jp[mp + 8:mp + 0x788])
        if mpos < 0 or d1.find(jp[mp + 8:mp + 0x788], mpos + 1) >= 0:
            fail(f'오프닝 {k}: 맵 자리')
        if kr[mp:mp + 8] != jp[mp:mp + 8]:
            fail(f'오프닝 {k}: 한글판 맵 머리가 바뀜')
        d1[mpos:mpos + 0x780] = kr[mp + 8:mp + 0x788]
        print(f'opening_z4 문단 {k}: 타일 {where}, 맵 {mpos:#x}')
    news = {0: bytes(d0), 1: bytes(d1)}
    out = rebuild(buf, news)
    back = zcpack.entries(out)
    for k2, (s_, e, c, dd) in enumerate(back):
        if dd != news.get(k2, ents[k2][3]) or c != ents[k2][2]:
            fail(f'opening_z4#{k2} 되읽기 불일치')
    open(os.path.join(OUT, 'opening_z4.bin'), 'wb').write(out)
    print(f'opening_z4.bin: {len(buf):#x} -> {len(out):#x}')


LOGO_MAP = 0xB2CCE0


def logo_erase_registered(new, jraw, kraw, coll):
    """컬렉션판은 일본어 로고의 ® 를 「ゼ」 획을 늘려 지웠다(x 110~131, y 51~59 의 바뀐 픽셀 = 지움 영역).
    한글판(logo4)은 ® 를 제자리에 두고 「제」 를 옆에 그려, 병합하면 한글판이 안 바꾼 픽셀에 컬렉션의 「ゼ」 조각이 남는다.
    → 지움 영역 중 한글판이 안 바꾼 픽셀은 같은 행에서 가장 가까운 지움 영역 밖 픽셀(병합 결과)로 메워 ® 없이 둔다."""
    jp = open(JP_ROM, 'rb').read()
    ent = struct.unpack_from('<1024H', jp, LOGO_MAP)
    at = lambda x, y: ((ent[(y // 8) * 32 + x // 8] & 0x3FF) - 0x100) * 64 + (y % 8) * 8 + x % 8
    inside = lambda x, y: 0 <= at(x, y) < len(jraw)
    erased = {(x, y) for y in range(30, 80) for x in range(240) if inside(x, y) and coll[at(x, y)] != jraw[at(x, y)]}   # 로고 띠만(저작권 줄 수정은 따로)
    if not erased:
        fail('title_z4: 컬렉션이 로고를 고치지 않았음 — 이 처리 재검토')
    if max(y for x, y in erased) - min(y for x, y in erased) > 12 or max(x for x, y in erased) - min(x for x, y in erased) > 32:
        fail('title_z4: 컬렉션 수정 범위가 ® 자리보다 넓음 — 이 처리 재검토')
    fill = [(x, y) for x, y in erased if kraw[at(x, y)] == jraw[at(x, y)]]
    src = dict(((x, y), new[at(x, y)]) for y in range(160) for x in range(240) if inside(x, y) and (x, y) not in erased)
    for x, y in fill:
        for d in range(1, 40):
            hit = [src.get((x - d, y)), src.get((x + d, y))]
            hit = [h for h in hit if h is not None]
            if hit:
                new[at(x, y)] = hit[0]
                break
        else:
            fail(f'title_z4: ({x}, {y}) 메울 이웃 없음')
    print(f'title_z4 로고: 컬렉션 ® 지움 자리 {len(erased)}픽셀 중 한글판이 안 바꾼 {len(fill)}픽셀을 같은 행 이웃으로 메움')


if __name__ == '__main__':
    rz2_gfx.run(JP_ROM, KR_ROM, TILESETS, [], 'obj_fnt_z4', post={('title_z4', 0, 0x00): logo_erase_registered})
    _jp, _kr = open(JP_ROM, 'rb').read(), open(KR_ROM, 'rb').read()
    raw_tiles(_jp, _kr)
    opening(_jp, _kr)
