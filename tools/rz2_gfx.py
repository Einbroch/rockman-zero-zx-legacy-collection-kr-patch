"""RZ2 그림 글자: GBA 2편 한글 롬(_work/rz2_kr.gba)이 다시 그린 타일셋·라벨 스프라이트를 컬렉션 RomFS ZC/DATA/*_z2.bin 에 옮긴다.

GBA 2편 패치는 압축 타일셋을 확장 영역에 새로 써 넣고 서술자(상대 오프셋, 크기|플래그, 배치)를 고쳤다.
컬렉션 묶음 항목 0 은 이 서술자들(+ 팔레트 서술자, 20바이트 레코드)과 압축 데이터를 담고 있다.
- 타일셋: 레코드가 가리키는 LZ 데이터를 풀어, GBA 일본판 → 한글판 바이트 차이를 옮긴다(컬렉션 바이트가 일본판과 같은 곳만).
  컬렉션판이 이미 고친 바이트와 겹치면 충돌 — 제목 타일셋만 허용(컬렉션이 메뉴 글자를 지움). 최단 분할 LZ 로 다시 압축해 제자리에 넣는다(넘치면 빌드 실패 — 항목 크기를 키우지 않는다).
- 라벨 스프라이트(obj_fnt_z2 #66 주황판, #67 초록판): GBA 행(16타일 x 5) → 1D 스프라이트 배치로 재배열돼 있고 팔레트 순서도 다르다.
  GBA 팔레트와 컬렉션 팔레트를 맞대어 색 번호 대응을 만들고, 일본판 타일(색 변환 후)과 정확히 같은 자리를 찾아 한글 타일을 쓴다.
출력: build/romfs/nativeNXx64/RZZC/ZC/DATA/<파일>
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import lz77
import zcpack
from rz1_gfx import rebuild

JP_ROM = os.path.join(ROOT, '..', 'Rockman Zero', 'roms', 'Rockman Zero 2 (Japan).gba')
KR_ROM = os.path.join(ROOT, '_work', 'rz2_kr.gba')
SRC = os.path.join(ROOT, '_work', 'romfs', 'nativeNXx64', 'RZZC', 'ZC', 'DATA')
OUT = os.path.join(ROOT, 'build', 'romfs', 'nativeNXx64', 'RZZC', 'ZC', 'DATA')

# (파일, 항목, 레코드 위치, GBA 서술자, 충돌 허용)
TILESETS = [
    ('sub_old_z2', 0, 0x00, 0x391850, False),   # 첫 미션 서브 화면(주황판)
    ('sub_new_z2', 0, 0x00, 0x391864, False),   # 초록판 상태
    ('sub_new_z2', 0, 0x14, 0x391878, False),   # 초록판 폼
    ('sub_new_z2', 0, 0x28, 0x39188C, False),   # 초록판 옵션+결과
    ('sub_new_z2', 0, 0x3C, 0x3918A0, False),   # 초록판 엘프 목록
    ('sub_new_z2', 0, 0x50, 0x391ECC, False),   # 칭호(코드네임)
    ('sub_elf_z2', 0, 0x00, 0x3918A0, False),   # 엘프 화면
    ('result_z2', 0, 0x00, 0x39188C, False),    # 결과 화면
    ('result_z2', 0, 0x14, 0x391ECC, False),    # 결과 화면 칭호
    ('sub_com_z2', 0, 0x00, 0x3918B4, False),   # 통신 대전
    ('sub_com_z2', 0, 0x14, 0x391E54, False),   # 통신 대전 쪽 게임오버
    ('gameover_z2', 0, 0x00, 0x391E54, False),  # 게임오버
    ('title_z2', 0, 0x14, 0x391EA4, 'merge'),   # 타이틀 로고: 컬렉션판이 메뉴 글자·® 를 지움 → 한글 바뀐 바이트를 덮고 ® 지움은 옮긴다
]

# 라벨 스프라이트: (GBA 스트림 서술자, GBA 팔레트, obj_fnt_z2 항목, 모호한 자리 지정 {(행, 타일): 항목 오프셋})
SPRITES = [
    (0x433228, 0x46876C, 66, {(0, 10): 0x214, (2, 0): 0x314, (1, 10): 0x294, (3, 0): 0x394,
                              (0, 14): 0x994, (2, 15): 0x634, (1, 14): 0x9B4, (3, 4): 0xA34}),
    (0x43323C, 0x469020, 67, {}),
]


def fail(msg):
    print('rz2_gfx: ' + msg, file=sys.stderr)
    sys.exit(1)


def gba_tileset(rom, desc):
    rel, size, layout = struct.unpack_from('<III', rom, desc)
    raw, consumed = lz77.decompress(rom, desc + rel)
    if consumed > size & 0x3FFFFF:
        fail(f'GBA 서술자 {desc:#x} 크기')
    return raw, layout


def stream_rows(rom, desc):
    off, flags = struct.unpack_from('<II', rom, desc)
    cur = desc + off
    end = cur + (flags & 0x3FFFFF)
    rows = []
    while cur < end:
        h, = struct.unpack_from('<I', rom, cur)
        n = h & 0x7FFFFFFF
        chunk = rom[cur + 4:cur + n]
        rows.append(lz77.decompress(chunk)[0] if h >> 31 else chunk)
        cur += n
    if cur != end or any(len(r) != 0x200 for r in rows):
        fail(f'스프라이트 스트림 {desc:#x} 형식')
    return rows


def pixels(tile):
    return [v for x in tile for v in (x & 15, x >> 4)]


def unpixels(px):
    return bytes(px[i] | px[i + 1] << 4 for i in range(0, 64, 2))


def sprite_tiles(rom, sp):
    """{키: 32바이트 타일}. 스트림(2편)은 (행, 타일), 압축 타일셋(3편)은 타일 번호."""
    if sp['kind'] == 'stream':
        rows = stream_rows(rom, sp['desc'])
        return {(r, t): rows[r][t * 32:t * 32 + 32] for r in range(len(rows)) for t in range(16)}
    raw, _ = gba_tileset(rom, sp['desc'])
    return {t: raw[t * 32:t * 32 + 32] for t in range(len(raw) // 32)}


def canon(tile):
    m = {}
    return tuple(m.setdefault(v, len(m)) for v in pixels(tile))


def color_map(d, prel, jp, kr, sp, jt, tiles):
    """GBA 색 번호 -> 컬렉션 색 번호. 팔레트 위치를 알면 팔레트끼리, 모르면(같은 색이 겹친 팔레트)
    모양이 한 자리에만 맞는 타일들에서 대응을 모은다."""
    if sp.get('gpal') is not None:
        cpal = struct.unpack_from('<16H', d, 0xC + prel)
        jpal = struct.unpack_from('<16H', jp, sp['gpal'])
        if struct.unpack_from('<16H', kr, sp['gpal']) == jpal == cpal:
            return list(range(16))   # 순서까지 같은 팔레트(같은 색이 겹쳐도 됨)
        if struct.unpack_from('<16H', kr, sp['gpal']) != jpal or sorted(jpal) != sorted(cpal) or len(set(cpal)) != 16:
            fail(f"스프라이트 {sp['desc']:#x} 팔레트 대응 불가")
        return [cpal.index(c) for c in jpal]
    by_canon = {}
    for o, v in tiles.items():
        by_canon.setdefault(canon(v), []).append(o)
    votes = {}
    for key, t in jt.items():
        if len(set(t)) <= 6:
            continue
        spots = by_canon.get(canon(t), [])
        if len(spots) != 1:
            continue
        for a, b in zip(pixels(t), pixels(tiles[spots[0]])):
            votes.setdefault(a, {}).setdefault(b, 0)
            votes[a][b] += 1
    cmap = [None] * 16
    for a, c in votes.items():
        b, n = max(c.items(), key=lambda kv: kv[1])
        if n * 4 < sum(c.values()) * 3:
            fail(f"스프라이트 {sp['desc']:#x} 색 {a} 대응이 한 가지로 모이지 않음 {c}")
        cmap[a] = b
    return cmap


def gba_logo_modules(title):
    """GBA 저장소의 logo_redraw 와 편별 로고 모듈(rzN/logo_rzN.py)"""
    g = os.path.join(ROOT, '..', 'Rockman Zero')
    for q in (os.path.join(g, 'tools'), os.path.join(g, f'rz{title}')):
        if q not in sys.path:
            sys.path.insert(0, q)
    import importlib
    return importlib.import_module('logo_redraw'), importlib.import_module(f'logo_rz{title}')


def move_registered_erase(title, get_jp, get_kr, get_coll, set_new, at, label):
    """컬렉션판은 일본어 로고의 ® 를 지웠다. 한글판(logo_redraw)은 ® 를 「록맨」 뒤 판 위로 옮겼으므로 그 칸을 판 색으로 메운다
    (® 없는 컬렉션 로고와 맞춤). 컬렉션 지움 값을 그대로 옮기면 일본어 ® 둘레의 글자 테두리 조각까지 따라온다.
    logo_redraw 가 ® 칸이 판 안이고 글자·테두리와 안 겹침을 이미 검사한다. at(x, y) = 타일셋 공간 위치."""
    TL, LM = gba_logo_modules(title)
    rx0, ry0, rx1, ry1 = LM.SPEC['registered']
    kx = TL.registered_x(LM.SPEC)
    plate = LM.SPEC['plate']
    if not any(get_coll(at(rx0 + dx, ry0 + dy)) != get_jp(at(rx0 + dx, ry0 + dy))
               for dy in range(ry1 - ry0 + 1) for dx in range(rx1 - rx0 + 1)):
        fail(f'{label}: 컬렉션이 ® 를 지우지 않았음 — 이 처리 재검토')
    n = 0
    for dy in range(ry1 - ry0 + 1):
        for dx in range(rx1 - rx0 + 1):
            src, dst = at(rx0 + dx, ry0 + dy), at(kx + dx, ry0 + dy)
            if get_kr(dst) != get_jp(src):
                fail(f'{label}: 한글 ® 자리 ({kx + dx}, {ry0 + dy}) 가 일본어 ® 칸과 다름')
            set_new(dst, plate)
            n += 1
    print(f'{label}: 한글 ® 칸(x {kx}~{kx + rx1 - rx0}, y {ry0}~{ry1}) {n}픽셀을 판 색 {plate} 으로 지움(컬렉션판처럼 ® 없음)')


def run(jp_path, kr_path, tilesets, sprites, objfile, post=None):
    """post: {(파일, 항목, 레코드): f(new, jraw, kraw, coll)} — 이식 뒤 타일셋을 더 고칠 때(예: 컬렉션이 지운 ® 를 옮긴 자리에서도 지움)"""
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    jp = open(jp_path, 'rb').read()
    kr = open(kr_path, 'rb').read()
    work = {}   # 파일 -> (원본 묶음, {항목: bytearray})

    def entry(fn, i):
        if fn not in work:
            work[fn] = (open(os.path.join(SRC, fn + '.bin'), 'rb').read(), {})
        buf, ch = work[fn]
        if i not in ch:
            ch[i] = bytearray(zcpack.entries(buf)[i][3])
        return ch[i]

    for fn, i, rec, desc, allow in tilesets:
        d = entry(fn, i)
        rel, size = struct.unpack_from('<II', d, rec)
        at = rec + rel
        coll, consumed = lz77.decompress(d, at)
        jraw, jlay = gba_tileset(jp, desc)
        kraw, klay = gba_tileset(kr, desc)
        if jlay != klay or len(jraw) != len(kraw) or len(coll) != len(jraw):
            fail(f'{fn}#{i}@{rec:#x}: 크기·배치 불일치')
        new = bytearray(coll)
        moved = conflict = skipped = 0
        for t0 in range(0, len(jraw), 32):   # 타일 단위: 충돌이 하나라도 있으면 그 타일은 컬렉션 그대로
            ks = [k for k in range(t0, t0 + 32) if jraw[k] != kraw[k]]
            bad = [k for k in ks if coll[k] != jraw[k]]
            if bad and allow == 'merge':   # 로고: 한글판이 바꾼 바이트는 컬렉션 수정 위에 덮는다(나머지 컬렉션 수정은 유지)
                conflict += len(bad)
                for k in ks:
                    new[k] = kraw[k]
                moved += len(ks)
                continue
            if bad:
                conflict += len(bad)
                skipped += 1
                continue
            for k in ks:
                new[k] = kraw[k]
            moved += len(ks)
        if conflict and not allow:
            fail(f'{fn}#{i}@{rec:#x} ({desc:#x}): 컬렉션판이 고친 바이트와 겹침 {conflict}')
        if post and (fn, i, rec) in post:
            post[(fn, i, rec)](new, jraw, kraw, coll)
        packed = lz77.compress_optimal(bytes(new))
        if lz77.decompress(packed)[0] != new:
            fail('LZ 왕복 실패')
        room = size & 0x3FFFFF
        if len(packed) > room:   # 항목을 키우면 해제 버퍼 크기를 모른다 — 제자리만 허용
            fail(f'{fn}#{i}@{rec:#x}: 다시 압축한 크기 {len(packed):#x} > 자리 {room:#x}')
        d[at:at + len(packed)] = packed
        struct.pack_into('<I', d, rec + 4, (size & ~0x3FFFFF) | len(packed))
        print(f'{fn}#{i}@{rec:#x} ({desc:#x}): {moved} 바이트, 충돌 {conflict}(타일 {skipped}개 건너뜀), {len(packed):#x}/{room:#x} 제자리')

    for sp in sprites:
        ei, fixed = sp['entry'], sp.get('fixed', {})
        d = entry(objfile, ei)
        prel, = struct.unpack_from('<I', d, 0xC)
        jt, kt = sprite_tiles(jp, sp), sprite_tiles(kr, sp)
        if jt.keys() != kt.keys():
            fail('스프라이트 타일 수')
        tiles = {o: bytes(d[o:o + 32]) for o in range(0x14, prel + 0xC - 31, 32)}
        cmap = color_map(d, prel, jp, kr, sp, jt, tiles)
        # 같은 일본어 타일이 여러 GBA 자리에 있으면 컬렉션 자리도 같은 수여야 하고, 순서대로 짝짓는다
        groups = {}
        for key in sorted(jt):
            if jt[key] != kt[key]:
                groups.setdefault(jt[key], []).append(key)
        n = 0
        if sp.get('linear'):   # 컬렉션이 GBA 타일 순서 그대로(타일 t -> 0x14 + 32t, remap 으로 예외 지정)
            remap = sp.get('remap', {})
            for jtile, keys in groups.items():
                for k in keys:
                    o = 0x14 + 32 * remap.get(k, k)
                    if tiles.get(o) != unpixels([cmap[p] for p in pixels(jtile)]):
                        fail(f"스프라이트 {sp['desc']:#x} 타일 {k}: 순서대로 자리에 일본어 타일이 없음")
                    d[o:o + 32] = unpixels([cmap[p] for p in pixels(kt[k])])
                    n += 1
            groups = {}
        for jtile, keys in groups.items():
            if any(cmap[p] is None for p in pixels(jtile)) or any(cmap[p] is None for k in keys for p in pixels(kt[k])):
                fail(f"스프라이트 {sp['desc']:#x} {keys[0]}: 대응 없는 색")
            want = unpixels([cmap[p] for p in pixels(jtile)])
            spots = sorted(o for o, v in tiles.items() if v == want)
            pinned = [k for k in keys if k in fixed]
            for k in pinned:
                if fixed[k] not in spots:
                    fail(f"스프라이트 {sp['desc']:#x} {k} 지정 자리 불일치")
            free_keys = [k for k in keys if k not in fixed]
            free_spots = [o for o in spots if o not in {fixed[k] for k in pinned}]
            if len(free_keys) != len(free_spots) and not (len(free_keys) == 0):
                # 같은 그림 사본이 더 많으면 모든 사본에 쓴다(그 그림의 한글이 한 가지일 때만)
                if len({kt[k] for k in keys}) == 1 and free_spots:
                    for o in spots:
                        d[o:o + 32] = unpixels([cmap[p] for p in pixels(kt[keys[0]])])
                    n += len(keys)
                    continue
                fail(f"스프라이트 {sp['desc']:#x} {keys}: 자리 {len(spots)}곳")
            pairs = [(k, fixed[k]) for k in pinned] + list(zip(free_keys, free_spots))
            for k, o in pairs:
                d[o:o + 32] = unpixels([cmap[p] for p in pixels(kt[k])])
                n += 1
        print(f"{objfile}#{ei} ({sp['desc']:#x}): 타일 {n}개")

    os.makedirs(OUT, exist_ok=True)
    for fn, (buf, ch) in work.items():
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
        print(f'{fn}.bin: 항목 {sorted(news)} 교체, {len(buf):#x} -> {len(out):#x}')


def logo_post(title, map_addr, tile0, cols=32):
    """타일셋 레코드 로고(2·3편): 타일 번호 = (맵 칸 & 0x3FF) - tile0, 맵 한 행 cols 칸 (GBA logo_rzN 과 같은 계산)"""
    def f(new, jraw, kraw, coll):
        jp = open(JP_ROM if title == 2 else os.path.join(ROOT, '..', 'Rockman Zero', 'roms', f'Rockman Zero {title} (Japan).gba'), 'rb').read()
        at = lambda x, y: ((struct.unpack_from('<H', jp, map_addr + ((y // 8) * cols + x // 8) * 2)[0] & 0x3FF) - tile0) * 64             + (y % 8) * 8 + x % 8
        move_registered_erase(title, jraw.__getitem__, kraw.__getitem__, coll.__getitem__, new.__setitem__, at, f'title_z{title} 로고')
    return f


def main():
    run(JP_ROM, KR_ROM, TILESETS,
        [dict(kind='stream', desc=desc, gpal=gpal, entry=ei, fixed=fixed) for desc, gpal, ei, fixed in SPRITES],
        'obj_fnt_z2', post={('title_z2', 0, 0x14): logo_post(2, 0x3873B0, 0)})


if __name__ == '__main__':
    main()
