"""록맨 ZX(컬렉션) 한글 데이터: NDS 한글패치 원고·인코더를 그대로 쓰고, 원문은 컬렉션 RomFS 파일 기준.
  python tools/zx_build.py
출력:
  build/romfs/nativeNXx64/RZZC/ZX/DATA/<대사 파일, font_jp.bin, 그림 파일>
  kohook/data/zx.bin : 한글 압축 글리프(16바이트/자, 한글 코드 순서) — kohook 의 ZX 훅이 임시 칸에 풀어 그린다.
게이트: 컬렉션이 내용을 바꾸지 않은 대사 파일은 NDS 한글판 롬의 파일과 바이트가 같아야 한다(인코딩·조립 경로 검증).
컬렉션이 바꾼 메시지(DS 시계 생일 문구 삭제 등)는 OVERRIDE 에 직접 번역을 둔다 — 원문이 OVERRIDE_JP 와 다르면 실패.
"""
import json
import os
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

SRC = os.path.join(ROOT, '_work', 'romfs', 'nativeNXx64', 'RZZC', 'ZX', 'DATA')
OUT = os.path.join(ROOT, 'build', 'romfs', 'nativeNXx64', 'RZZC', 'ZX', 'DATA')
BLOB = os.path.join(ROOT, 'kohook', 'data', 'zx.bin')
RAW_OUT = os.path.join(ROOT, 'build', 'zx_raw.json')   # main 직접 패치(이름표): [[주소, 원래 hex, 새 hex]]
IMG = os.path.join(ROOT, '_work', 'exefs_upd', 'main.img')
# 화자 이름표(NDS ARM9 정적 데이터)의 main 사본: (ARM9 주소, 길이, [main 주소…]) — 엔진 A·B 두 벌(GOT 0x2e417c0/d0, 0x2e41f10/20)
NAMEPLATE = [(0x020BE6B8, 88 * 12, [0x226b8a0, 0x227d080]),      # 이름 표
             (0x020BF118, 0x77 * 64, [0x226daa8, 0x227f288])]    # 8x8 글꼴
KR_ROM = os.path.join(NDS, 'out', 'zx_kr.nds')
KR_CRC = 0xEB5FA975          # NDS 한글판 zx-v0.9.3 (에일 쪽 호칭 수정 포함)

# 컬렉션판에서 바뀐 메시지: (파일, 번호) -> (컬렉션 원문, 번역)
OVERRIDE = {
    ('m_sub_jp.bin', 47): ('セレクトボタン…バスタ－エディット',
                           '셀렉트 버튼…버스터 에디트'),
    ('m_sub_jp.bin', 71): ('{F1:01}ケ－キ\n{F1:00}ライフが8めもり\nカイフクする',
                           '{F1:01}케이크\n{F1:00}라이프를 8칸\n회복한다'),
}
_TW2 = ('{F2:02}{F3:41}{F8:3c}運び屋さん！{p}\n{F2:02}{F3:41}{F8:3c}これ、あげる！{p}\n'
        '{F2:02}{F3:41}{F8:3c}わたしの手づくり…\nと いいたいところだけど{p}\n'
        '{F2:02}{F3:41}{F8:3c}半分いじょうは\nわたしのおねえちゃんに\n手伝ってもらっちゃった')
_TW2_KO = ('{F2:02}{F3:41}{F8:3c}배달부 오빠!{p}\n{F2:02}{F3:41}{F8:3c}이거, 줄게!{p}\n'
           '{F2:02}{F3:41}{F8:3c}내가 직접 만들었어…\n라고 말하고 싶지만{p}\n'
           '{F2:02}{F3:41}{F8:3c}절반 이상은\n우리 언니가\n도와줬어')
OVERRIDE[('talk_tw2_jp1.bin', 27)] = (_TW2, _TW2_KO)
OVERRIDE[('talk_tw2_jp2.bin', 27)] = (_TW2, _TW2_KO.replace('배달부 오빠', '배달부 언니'))   # 에일 쪽


def dump(b, cm):
    A, base, offs = zxtext.parse(b)
    end = A + 4
    i = base
    msgs = []
    while i < end:
        s0 = i
        s, i, term = zxtext.decode_msg(b, i, cm)
        assert zxtext.encode_jp(s, cm) == b[s0:i - 1]
        msgs.append({'off': s0 - base, 's': s, 'end': term})
    assert i == end
    return A, base, offs, msgs


def assemble(b, base, offs, msgs, plan, kr, errors):
    body = bytearray()
    newoff = {}
    A = struct.unpack_from('<H', b, 0)[0]
    for i, m in enumerate(msgs):
        newoff[m['off']] = len(body)
        t = plan[i]
        if t is None:
            e = base + msgs[i + 1]['off'] if i + 1 < len(msgs) else A + 4
            body += b[base + m['off']:e]
        else:
            body += bz.encode_ko(t, kr, errors) + bytes([m['end']])
    offs2 = [newoff[o] for o in offs]
    B = len(offs) * 2
    assert len(body) + B < 0x10000
    return struct.pack('<HH', B + len(body), B) + struct.pack('<%dH' % len(offs), *offs2) + bytes(body)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    raw = open(KR_ROM, 'rb').read()
    assert zlib.crc32(raw) == KR_CRC, 'NDS 한글판 롬 CRC 불일치'
    krom = ndspy.rom.NintendoDSRom(raw)
    jrom = ndspy.rom.NintendoDSRom.fromFile(bz.SRC_ROM)
    jp = json.load(open(os.path.join(NDS, 'data', 'zx_jp.json'), encoding='utf-8'))
    cm = zxtext.prep(zxtext.load_charmap('zx'), False)
    tr = bz.load_translations('zx', jp)
    by_src = {}
    for f, v in jp.items():
        for i, m in enumerate(v['msgs']):
            t = tr.get((f[:-4], i))
            if t is not None:
                by_src.setdefault(m['s'], t)
    bz.address_gate('zx', jp, tr, by_src)   # 주인공 호칭(반/에일) 게이트

    # 컬렉션 원문 기준 계획
    plans, colls, used_ov = {}, {}, set()
    for f, v in jp.items():
        cb = open(os.path.join(SRC, f), 'rb').read()
        A, base, offs, msgs = dump(cb, cm)
        colls[f] = (cb, base, offs, msgs)
        assert len(msgs) == len(v['msgs']), f
        plan = []
        for i, m in enumerate(msgs):
            if (f, i) in OVERRIDE:
                src, ko = OVERRIDE[(f, i)]
                assert m['s'] == src, ('컬렉션 원문이 OVERRIDE 와 다름', f, i)
                plan.append(ko)
                used_ov.add((f, i))
                continue
            assert m['s'] == v['msgs'][i]['s'], ('OVERRIDE 없는 원문 차이', f, i, m['s'])
            t = tr.get((f[:-4], i))
            if t is None and m['s']:
                t = by_src.get(m['s'])
            plan.append(t)
        plans[f] = plan
    assert used_ov == set(OVERRIDE), set(OVERRIDE) - used_ov

    hangul = bz.collect_hangul([t for p in plans.values() for t in p if t])
    assert len(hangul) <= bz.NLEAD * bz.TRAIL
    kr = {ch: k for k, ch in enumerate(hangul)}
    errors = []
    os.makedirs(OUT, exist_ok=True)
    n_same = n_ov = 0
    for f in jp:
        cb, base, offs, msgs = colls[f]
        out = assemble(cb, base, offs, msgs, plans[f], kr, errors)
        if any((f, i) in OVERRIDE for i in range(len(msgs))):
            n_ov += 1
        else:
            kb = krom.getFileByName(f)
            assert out == kb, ('NDS 한글판과 다름', f)   # 게이트: 같은 원고·원문이면 같은 바이트
            n_same += 1
        open(os.path.join(OUT, f), 'wb').write(out)
    if errors:
        raise SystemExit('인코딩 불가 문자: %r' % sorted(set(errors)))

    # 글꼴: NDS 한글판 font_jp.bin (영숫자·문장부호 비례폭, 폭은 0행 위 4비트). 압축 한글 저장 칸 내용은 쓰지 않는다.
    fj = krom.getFileByName('font_jp.bin')
    assert open(os.path.join(SRC, 'font_jp.bin'), 'rb').read() == jrom.getFileByName('font_jp.bin')
    open(os.path.join(OUT, 'font_jp.bin'), 'wb').write(fj)

    # 그림 파일: 일본판 롬 객체의 파일을 컬렉션 파일로 바꿔 끼우고 NDS 그림 도구를 그대로 돌린다
    # (컬렉션이 고친 h01·sub·title 은 그 위에 한글이 얹힘). 게이트: 컬렉션이 일본판 그대로인 파일은 NDS 한글판과 같아야 한다.
    import gfx_zx, gfx_sub, gfx_bg, logo_zx
    shim = ndspy.rom.NintendoDSRom.fromFile(bz.SRC_ROM)
    coll = {}
    for i in range(len(shim.files)):
        nm = shim.filenames.filenameOf(i)
        if nm and '/' not in nm and os.path.exists(os.path.join(SRC, nm)):
            shim.files[i] = open(os.path.join(SRC, nm), 'rb').read()
            coll[i] = shim.files[i]
    for f in (gfx_zx.apply, gfx_sub.apply, gfx_bg.apply, logo_zx.apply):
        f(shim)
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
    for i, jb in enumerate(jrom.files):   # 한글판이 바꿨는데 위 도구가 안 다룬 파일이 있으면 실패
        nm = jrom.filenames.filenameOf(i)
        if nm and '/' not in nm and krom.files[i] != jb and not nm.startswith(('talk_', 'm_')) and nm != 'font_jp.bin':
            assert i in coll and shim.files[i] != coll[i], ('그림 도구가 안 다룬 한글판 변경 파일', nm)

    # 이름표: NDS 한글판 ARM9 의 같은 구간을 main 사본에 그대로
    j9 = jrom.loadArm9().sections[0].data
    k9 = krom.loadArm9().sections[0].data
    img = open(IMG, 'rb').read()
    raw_p = []
    for a9, n, mains in NAMEPLATE:
        o = a9 - 0x02000000
        jb, kb = bytes(j9[o:o + n]), bytes(k9[o:o + n])
        for ma in mains:
            assert img[ma:ma + n] == jb, ('이름표 사본 위치가 다름', hex(ma))
            raw_p.append([ma, jb.hex(), kb.hex()])
    json.dump(raw_p, open(RAW_OUT, 'w'))

    blob = b''.join(bz.pack_glyph(ch) for ch in hangul)
    os.makedirs(os.path.dirname(BLOB), exist_ok=True)
    open(BLOB, 'wb').write(blob)
    print(f'대사 파일 {len(jp)}개 (NDS 한글판과 같음 {n_same}, 컬렉션 차이 반영 {n_ov}), 한글 {len(hangul)}자 -> {BLOB} {len(blob)}B')
    print(f'그림 파일 {n_gfx}개 (컬렉션 수정본에 병합: {merged})')


if __name__ == '__main__':
    main()
