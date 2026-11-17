"""컬렉션 런처 한국어: launcher/ko_*.json(일본어 원문 → 한국어)을 일본어 GMD 에 넣고,
번역에 쓰인 글자 중 글꼴에 없는 글자를 Font_jpn.arc 6개 슬롯에 새 BC7 페이지로 추가한다.
출력: build/romfs/nativeNXx64/RZZC/romNX/<arc> (바뀐 arc 만, 바뀐 항목만 재압축)
  python tools/launcher_build.py [--report]
"""
import glob
import json
from collections import Counter
import os
import re
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arcpack
import bc7a
import deswizzle
import fonttex
import gfd
import gmd
import mtarc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '_work', 'romfs', 'nativeNXx64', 'RZZC', 'romNX')
OUT = os.path.join(ROOT, 'build', 'romfs', 'nativeNXx64', 'RZZC', 'romNX')
FONT_DIR = r'D:\Games\Kor Patch\CLude\폰트\S-Core_Dream_OTF'
GMD_HASH = 0x242bb29a
TEX_HASH = 0x241f5deb
# 슬롯 → (글꼴 굵기). 짝수 슬롯 = SL0(본문, 가는 글꼴), 홀수 슬롯 = SL1(제목, 굵은 기울임 글꼴)
SLOT_WEIGHT = {0: 5, 1: 7, 2: 5, 3: 7, 4: 5, 5: 7}
PAGE = 1024
GLYPH_ALIAS = {'・': '·'}   # 에스코어 드림에 없는 글자 → 모양이 같은 글자로 그림
LANGS = ('jpn', 'eng', 'fre', 'ger', 'ita', 'spa', 'chT', 'chS')
GAP = 3
TAG = re.compile(r'<[^<>]*>')


def load_tr():
    tr = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'launcher', 'ko_*.json'))):
        d = json.load(open(p, encoding='utf-8'))
        for k, v in d.items():
            if k in tr and tr[k] != v:
                raise SystemExit(f'번역 충돌: {k!r} ({p})')
            tr[k] = v
    return tr


def text_chars(s):
    return set(TAG.sub('', s)) - set('\r\n')


def apply_gmd(tr):
    """→ {arc 경로: {항목 이름: 새 GMD 바이트}}, 쓰인 번역 키 집합, SL 별 필요한 글자"""
    changes, used = {}, set()
    need = {0: set(), 1: set()}
    for p in sorted(glob.glob(os.path.join(SRC, '**', '*.arc'), recursive=True)):
        d, _, _, es = mtarc.parse(p)
        for e in es:
            if e['hash'] != GMD_HASH or not e['name'].endswith('_jpn'):
                continue
            g = gmd.Gmd(mtarc.blob(d, e))
            sl = 1 if '_SL1_' in e['name'] else 0
            hit = False
            for i, t in enumerate(g.texts):
                if t in tr:
                    g.texts[i] = tr[t]
                    used.add(t)
                    hit = True
                    need[sl] |= text_chars(tr[t])
            if hit:
                changes.setdefault(p, {})[e['name']] = g.build()
    return changes, used, need


def render_glyph(font, ch, S, asc):
    """→ (알파 배열, 측정값 f[6] 중 앞 5개: 폭, 높이, 왼쪽, 위, 전진폭)"""
    adv = font.getlength(ch)
    l, t, r, b = font.getbbox(ch, anchor='ls')
    if r <= l or b <= t:
        return None, [0.0, 0.0, 0.0, 0.0, float(adv)]
    w, h = r - l, b - t
    im = Image.new('L', (w, h), 0)
    ImageDraw.Draw(im).text((-l, -t), ch, font=font, fill=255, anchor='ls')
    return np.array(im), [float(w), float(h), float(l), float(asc + t), float(adv)]


def pack(sizes):
    """선반 채우기: sizes [(w,h)] → [(page, x, y)], 페이지 수"""
    pos, page, x, y, row = [], 0, 0, 0, 0
    for w, h in sizes:
        if x + w > PAGE:
            x, y, row = 0, y + row + GAP, 0
        if y + h > PAGE:
            page, x, y, row = page + 1, 0, 0, 0
        pos.append((page, x, y))
        x += w + GAP
        row = max(row, h)
    return pos, (page + 1 if sizes else 0)


def build_font(need, lang='jpn', report=False):
    """need: {0: SL0 글자, 1: SL1 글자} → 새 Font_<lang>.arc 바이트(바뀐 게 없으면 None)"""
    path = os.path.join(SRC, f'Font_{lang}.arc')
    d, _, _, es = mtarc.parse(path)
    E = {e['name']: e for e in es}
    tex_head = None
    for e in es:
        if e['hash'] == TEX_HASH:
            b = mtarc.blob(d, e)
            if fonttex.tex_dims(b) == (PAGE, PAGE):
                tex_head = b[:24]
                break
    replace, add = {}, []
    for slot, wt in SLOT_WEIGHT.items():
        gname = r'Font\Slot\SLOT%02d_zoom_' % slot + lang
        g = gfd.Gfd(mtarc.blob(d, E[gname]))
        S, LH, ASC = g.floats[0], g.floats[1], g.floats[2]
        missing = sorted(c for c in need[slot % 2] if ord(c) not in g.by_code)
        if not missing:
            continue
        font = ImageFont.truetype(os.path.join(FONT_DIR, f'SCDream{wt}.otf'), int(round(S)))
        p2 = Counter(c['p2'] for c in g.chars).most_common(1)[0][0]   # 거의 모든 글자가 같은 값
        imgs, metas = [], []
        for ch in missing:
            a, f = render_glyph(font, GLYPH_ALIAS.get(ch, ch), S, ASC)
            if a is None and not ch.isspace():
                raise SystemExit(f'글꼴에 없는 글자: {ch!r} U+{ord(ch):04X}')
            if a is None:
                a = np.zeros((1, 1), np.uint8)
                f[0] = f[1] = 1.0
            imgs.append(a)
            metas.append(f)
        pos, npages = pack([(a.shape[1], a.shape[0]) for a in imgs])
        canv = [np.zeros((PAGE, PAGE), np.uint8) for _ in range(npages)]
        base = g.head[6]
        for ch, a, f, (pg, x, y) in zip(missing, imgs, metas, pos):
            canv[pg][y:y + a.shape[0], x:x + a.shape[1]] = a
            g.chars.append(dict(code=ord(ch), f=f + [float(LH)], page=base + pg, x=x, y=y, p2=p2))
        g.head[6] = base + npages
        hb = PAGE // 4
        for k, c in enumerate(canv):
            lin = bc7a.encode(c)
            sw = deswizzle.swizzle(lin, PAGE // 4, hb, 16, fonttex.block_height(hb))
            add.append((r'Font\Slot\SLOT%02d_zoom_%s_%02d_ID' % (slot, lang, base + k), TEX_HASH, tex_head + sw))
            if report:
                Image.fromarray(c).save(os.path.join(ROOT, '_work', 'shots', f'lfont_{lang}_s{slot}_p{base + k}.png'))
        replace[gname] = g.build()
        print(f'  {lang} SLOT{slot:02d}: 글자 {len(missing)}개 추가, 새 페이지 {npages}장 (크기 {S:g}, 굵기 {wt})')
    if not replace:
        return None
    return arcpack.rebuild(path, replace=replace, add=add)


def main():
    report = '--report' in sys.argv
    tr = load_tr()
    changes, used, need = apply_gmd(tr)
    unused = [k for k in tr if k not in used]
    print(f'번역 {len(tr)}개 중 적용 {len(used)}개, GMD {sum(len(v) for v in changes.values())}개 / arc {len(changes)}개')
    if unused:
        for k in unused:
            print('  쓰이지 않은 번역 키:', repr(k[:40]))
        raise SystemExit('쓰이지 않은 번역 키가 있다 (원문 오타?)')
    os.makedirs(OUT, exist_ok=True)
    for p, rep in changes.items():
        rel = os.path.relpath(p, SRC)
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.basename(p).startswith('Font_'):
            raise SystemExit(f'{p} 에 GMD 가 있다: 처리 순서 재검토 필요')
        open(dst, 'wb').write(arcpack.rebuild(p, replace=rep))
    # 한글은 모든 언어 글꼴에 넣는다: 크레딧처럼 런처 언어가 아니라 본체 언어 글꼴로 그리는 화면이 있다(11/17 실측)
    for lang in LANGS:
        fa = build_font(need, lang, report)
        if fa is None:
            continue
        name = f'Font_{lang}.arc'
        open(os.path.join(OUT, name), 'wb').write(fa)
        # 다시 읽어 검증: 모든 번역 글자가 해당 슬롯 GFD 에 있고 페이지 텍스처가 있다
        d, _, _, es = mtarc.parse(os.path.join(OUT, name))
        E = {e['name']: e for e in es}
        for slot in SLOT_WEIGHT:
            g = gfd.Gfd(mtarc.blob(d, E[r'Font\Slot\SLOT%02d_zoom_' % slot + lang]))
            miss = [c for c in need[slot % 2] if ord(c) not in g.by_code]
            assert not miss, (lang, slot, miss[:10])
            for k in range(g.head[6]):
                assert r'Font\Slot\SLOT%02d_zoom_%s_%02d_ID' % (slot, lang, k) in E, (lang, slot, k)
    print('출력 ->', OUT)


if __name__ == '__main__':
    main()
