"""록맨 ZX 어드벤트(컬렉션) 한글 데이터: NDS 한글패치(ZXA) 원고·인코더·그림 도구를 쓰고, 원문은 컬렉션 RomFS 파일 기준.
  python tools/zxa_build.py
출력:
  build/romfs/nativeNXx64/RZZC/ZXA/DATA/<대사 파일, font_jp.bin, 그림 파일>
  kohook/data/zxa.bin : 한글 압축 글리프(16바이트/자, 한글 코드 순서)
  build/zxa_raw.json  : main 직접 패치(화자 이름표) [[주소, 원래 hex, 새 hex]]
번역 출처(메시지마다): ① 같은 파일·같은 번호·같은 원문이면 그 칸 번역 ② 같은 원문의 번역(NDS 어디든)
  ③ zx/zxa_coll_ko.json(컬렉션에만 있는 원문, tools/zxa_coll_ko.py). 일본어가 남으면 실패(다운로드 플레이 자기 m_mg_ds 제외).
글꼴: 일본판 font_jp + NDS 한글판의 영숫자·문장부호 비례폭 다시 그림. 한글은 모듈(zxa.bin)에 상주시키므로
  NDS 판처럼 안 쓰는 칸을 한글 저장소로 덮지 않는다(컬렉션 원문이 쓰는 칸이 달라도 안전).
게이트: 대사 파일마다 인코딩 결과를 되읽어 계획한 문장과 같은지, 한글 음절 순서가 NDS 와 같으면 컬렉션이 원문을 안 바꾼 파일은
  NDS 한글판(out/zxa_kr.nds)과 바이트가 같은지.
"""
import json
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NDS = os.path.join(os.path.dirname(ROOT), 'Rockman ZX, Advent')
sys.path.insert(0, os.path.join(NDS, 'tools'))
import ndspy.rom  # noqa: E402
import zxtext  # noqa: E402
import build_zx as bz  # noqa: E402
import build_zxa as bza  # noqa: E402

SRC = os.path.join(ROOT, '_work', 'romfs', 'nativeNXx64', 'RZZC', 'ZXA', 'DATA')
OUT = os.path.join(ROOT, 'build', 'romfs', 'nativeNXx64', 'RZZC', 'ZXA', 'DATA')
BLOB = os.path.join(ROOT, 'kohook', 'data', 'zxa.bin')
RAW_OUT = os.path.join(ROOT, 'build', 'zxa_raw.json')
COLL_KO = os.path.join(ROOT, 'zx', 'zxa_coll_ko.json')
IMG = os.path.join(ROOT, '_work', 'exefs_upd', 'main.img')
KR_ROM = os.path.join(NDS, 'out', 'zxa_kr.nds')
KR_CRC = 0x41792E4D          # NDS 한글판 ZXA (zxa-v0.9.0 + hn3 47 앞 줄바꿈 수정)
# 화자 이름표: NDS ARM9 이름 표(96칸 × 12바이트)를 컬렉션은 칸당 20바이트(12 + 0 8개)로 늘려 두었다. 두 벌(엔진 A·B).
NP_TABLE, NP_GLYPH, NP_N = 0x020DEAA8, 0x020DF968, 96
NP_MAIN = [(0x223fb53, 0x22432b4), (0x2258533, 0x225bc94)]   # (이름 표, 8x8 글꼴) — 간격 0x3761 로 짝


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    raw = open(KR_ROM, 'rb').read()
    assert zlib.crc32(raw) == KR_CRC, 'NDS 한글판 ZXA 롬 CRC 불일치'
    krom = ndspy.rom.NintendoDSRom(raw)
    jrom = ndspy.rom.NintendoDSRom.fromFile(bza.SRC_ROM)
    jp = json.load(open(os.path.join(NDS, 'data', 'zxa_jp.json'), encoding='utf-8'))
    cm = zxtext.prep(zxtext.load_charmap('zxa'), True)
    tr = bz.load_translations('zxa', jp)
    by_src = {}
    for f, v in jp.items():
        for i, m in enumerate(v['msgs']):
            t = tr.get((f[:-4], i))
            if t is not None:
                by_src.setdefault(m['s'], t)
    bz.address_gate('zxa', jp, tr, by_src)
    bz.lead_gate('zxa', jp, tr)
    coll_ko = json.load(open(COLL_KO, encoding='utf-8'))

    plans, colls, missing, used_coll = {}, {}, [], set()
    for f, v in jp.items():
        cb = open(os.path.join(SRC, f), 'rb').read()
        A, base, offs = zxtext.parse(cb)
        msgs, i = [], base
        while i < A + 4:
            s0 = i
            s, i, term = zxtext.decode_msg(cb, i, cm)
            assert zxtext.encode_jp(s, cm) == cb[s0:i - 1], (f, hex(s0))
            msgs.append({'off': s0 - base, 's': s, 'end': term})
        assert i == A + 4, f
        colls[f] = (cb, base, offs, msgs)
        plan = []
        for k, m in enumerate(msgs):
            s = m['s']
            t = None
            if k < len(v['msgs']) and v['msgs'][k]['s'] == s:
                t = tr.get((f[:-4], k))
            if t is None and s:
                t = by_src.get(s)
            if t is None and s in coll_ko:
                t = coll_ko[s]
                used_coll.add(s)
            if t is None and f not in bza.OTHER_FONT and re.search(r'[ぁ-んァ-ヶ一-龯]', s):
                missing.append((f, k))
            plan.append(t)
        plans[f] = plan
    if missing:
        raise SystemExit('미번역(일본어가 남음): %r' % missing[:20])
    unused = set(coll_ko) - used_coll
    assert not unused, ('쓰이지 않은 컬렉션 번역', [u[:30] for u in unused])
    over = []
    for f in jp:
        for k, t in enumerate(plans[f]):
            if t is not None:
                src = colls[f][3][k]['s']
                w, lim = max(bz.line_widths(t)), bz.width_limit(f[:-4], src)
                if w > lim:
                    over.append((f, k, w, lim))
    if over:
        print(f'줄 폭 초과(원문 최장 줄 기준) {len(over)}건:', over[:10])

    hangul = bz.collect_hangul([t for p in plans.values() for t in p if t])
    nds_hangul = bz.collect_hangul([t for t in (tr.get((f[:-4], i)) or by_src.get(m['s'])
                                                for f, v in jp.items() for i, m in enumerate(v['msgs'])) if t])
    same_order = hangul == nds_hangul
    kr = {ch: k for k, ch in enumerate(hangul)}
    inv_kr = {k: ch for ch, k in kr.items()}
    errors = []
    os.makedirs(OUT, exist_ok=True)
    n_same = n_diff = 0
    for f in jp:
        cb, base, offs, msgs = colls[f]
        A = struct.unpack_from('<H', cb, 0)[0]
        body, newoff = bytearray(), {}
        for k, m in enumerate(msgs):
            newoff[m['off']] = len(body)
            t = plans[f][k]
            if t is None:
                e = base + msgs[k + 1]['off'] if k + 1 < len(msgs) else A + 4
                body += cb[base + m['off']:e]
            else:
                enc = bza.encode_ko(t, kr, errors)
                assert decode_ko(enc, inv_kr) == normalize(t), (f, k)      # 되읽기 게이트
                body += enc + bytes([m['end']])
        offs2 = [newoff[o] for o in offs]
        B = len(offs) * 2
        assert len(body) + B < 0x10000, f
        out = struct.pack('<HH', B + len(body), B) + struct.pack('<%dH' % len(offs), *offs2) + bytes(body)
        if [m['s'] for m in msgs] == [m['s'] for m in jp[f]['msgs']]:
            if same_order:
                assert out == krom.getFileByName(f), ('NDS 한글판과 다름', f)
            n_same += 1
        else:
            n_diff += 1
        open(os.path.join(OUT, f), 'wb').write(out)
    if errors:
        raise SystemExit('인코딩 불가 문자: %r' % sorted(set(errors)))

    # 글꼴
    F = bytearray(open(os.path.join(SRC, 'font_jp.bin'), 'rb').read())
    assert bytes(F) == jrom.getFileByName('font_jp.bin')
    assert len(F) == 0x20 + bza.NGLYPH * 32 and struct.unpack_from('<H', F, 0)[0] == 12
    kf = krom.getFileByName('font_jp.bin')
    for ch, g in bz.REDRAW.items():
        F[0x20 + g * 32:0x20 + g * 32 + 32] = bz.glyph_bytes(ch)
    F[0x20:0x40] = bz.glyph_bytes(' ')
    # NDS 한글판과 비교: 다시 그린 칸·공백은 같아야 하고, 다른 칸은 NDS 가 한글 저장소로 쓴 칸(FREE·회수 칸)뿐이어야 한다
    for g in range(bza.NGLYPH):
        a, b = F[0x20 + g * 32:0x20 + g * 32 + 32], kf[0x20 + g * 32:0x20 + g * 32 + 32]
        if a != b:
            assert g in bza.FREE or g in (bza.SCR0, bza.SCR0 + 1) or (0x25 <= g < 0x3F) or (0xE5 <= g < 0x100), hex(g)
    for g in (bza.SCR0, bza.SCR0 + 1):
        F[0x20 + g * 32:0x20 + g * 32 + 32] = bytes(32)
    open(os.path.join(OUT, 'font_jp.bin'), 'wb').write(bytes(F))

    # 그림: 일본판 롬 객체에 컬렉션 파일을 끼워 NDS 그림 도구(gfx_zxa)를 그대로 돌린다
    import gfx_zxa
    shim = ndspy.rom.NintendoDSRom.fromFile(bza.SRC_ROM)
    coll = {}
    for i in range(len(shim.files)):
        nm = shim.filenames.filenameOf(i)
        if nm and '/' not in nm and os.path.exists(os.path.join(SRC, nm)):
            shim.files[i] = open(os.path.join(SRC, nm), 'rb').read()
            coll[i] = shim.files[i]
    gfx_zxa.apply(shim)
    n_gfx, merged = 0, []
    for i, cb in coll.items():
        nm = shim.filenames.filenameOf(i)
        if shim.files[i] == cb or nm.startswith(('talk_', 'm_')) or nm == 'font_jp.bin':
            continue
        if cb == jrom.files[i]:
            assert shim.files[i] == krom.files[i], ('NDS 한글판과 다른 그림', nm)
        else:
            merged.append(nm)
        open(os.path.join(OUT, nm), 'wb').write(shim.files[i])
        n_gfx += 1
    for i, jb in enumerate(jrom.files):
        nm = jrom.filenames.filenameOf(i)
        if nm and '/' not in nm and krom.files[i] != jb and not nm.startswith(('talk_', 'm_')) and nm != 'font_jp.bin':
            assert i in coll and shim.files[i] != coll[i], ('그림 도구가 안 다룬 한글판 변경 파일', nm)

    # 이름표: NDS 한글판 ARM9 의 이름 표(12바이트 칸)를 컬렉션의 20바이트 칸으로, 8x8 글꼴은 그대로
    j9 = jrom.loadArm9().sections[0].data
    k9 = krom.loadArm9().sections[0].data
    img = open(IMG, 'rb').read()
    raw_p = []
    gt, gn = NP_GLYPH - 0x02000000, 0x77 * 64
    for ta, ga in NP_MAIN:
        o = NP_TABLE - 0x02000000
        jt = b''.join(bytes(j9[o + 12 * e:o + 12 * e + 12]) + bytes(8) for e in range(NP_N))
        kt = b''.join(bytes(k9[o + 12 * e:o + 12 * e + 12]) + bytes(8) for e in range(NP_N))
        assert img[ta:ta + len(jt)] == jt, ('이름 표 사본 위치가 다름', hex(ta))
        raw_p.append([ta, jt.hex(), kt.hex()])
        assert img[ga:ga + gn] == bytes(j9[gt:gt + gn]), ('이름표 글꼴 사본 위치가 다름', hex(ga))
        raw_p.append([ga, bytes(j9[gt:gt + gn]).hex(), bytes(k9[gt:gt + gn]).hex()])
    json.dump(raw_p, open(RAW_OUT, 'w'))

    blob = b''.join(bz.pack_glyph(ch) for ch in hangul)
    open(BLOB, 'wb').write(blob)
    print(f'ZXA 대사 파일 {len(jp)}개 (원문 같음 {n_same}{"·NDS 와 바이트 동일" if same_order else ""}, 컬렉션 원문 {n_diff}), '
          f'컬렉션 전용 번역 {len(used_coll)}, 한글 {len(hangul)}자 -> {len(blob)}B, 임시 칸 {bza.SCR0:#x}')
    print(f'그림 파일 {n_gfx}개 (컬렉션 수정본에 병합: {merged})')


def normalize(t):
    """encode_ko 가 받아들이는 표기를 되읽기와 같은 꼴로: 쪽 넘김 표기 통일, 별칭 문자 정규화."""
    return ''.join(bz.norm(c) if not c.startswith('{') else c for c in re.findall(r'\{[^}]*\}|.', t, re.S))


def decode_ko(b, inv_kr):
    inv = {}
    for ch, g in bza.CHARMAP.items():
        inv.setdefault(g, ch)
    out, i = [], 0
    while i < len(b):
        c = b[i]
        if 0x40 <= c <= 0x4f and i + 1 < len(b) and b[i + 1] < 0xf0:
            out.append(inv_kr[(c - 0x40) * 240 + b[i + 1]]); i += 2; continue
        if c == 0xfd:
            out.append('{p}\n'); i += 1; continue
        if c == 0xfc:
            out.append('\n'); i += 1; continue
        if c == 0xf0:
            g, i = 0xf0, i + 1
            while b[i] == 0xff:
                g += 0xff; i += 1
            g += b[i]; i += 1
            out.append(inv.get(g, '{J%03X}' % g)); continue
        if 0xf1 <= c <= 0xf8:
            out.append('{%02X:%s}' % (c, b[i + 1:i + 2].hex())); i += 2; continue
        if c == 0xf9:
            out.append('{%02X:%s}' % (c, b[i + 1:i + 3].hex())); i += 3; continue
        if c in (0xfa, 0xfb):
            out.append('{%02X}' % c); i += 1; continue
        out.append(inv.get(c, '{J%03X}' % c)); i += 1
    return ''.join(out)


if __name__ == '__main__':
    main()
