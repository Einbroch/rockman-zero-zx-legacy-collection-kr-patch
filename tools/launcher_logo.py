"""런처 게임 고르기 화면의 록맨 제로 1~4·ZX·ZX 어드벤트 로고(TitleUI.arc launcher_13_HQ, 일본어 칸 = 한국어판)를 한글 로고로 바꾼다.

텍스처 형식(실측): MT TEX 형식 0x2B = BC3, Tegra 블록리니어, 2048x1024, 밉 12단계. 데이터는 파일 끝에서 v4 바이트
(머리 24바이트 + 밉 오프셋 표 등). 채널은 색이 아니라 R = Cr+128, G = 알파, B = Cb+128, A = Y (BT.601 전범위).
원본 그림: launcher/logo_src/{zero1..4,zx,zxa}_kr.png (사용자 제작, 투명 배경). 원래 로고의 알파 상자 안에 비율을 지켜 맞춘다.
launcher_build.py 다음에 돈다: build/romfs/.../TitleUI.arc 를 읽어 이 항목만 바꿔 다시 쓴다(텍스처 원본은 언제나 _work 원본).
"""
import os
import struct
import sys

import etcpak
import numpy as np
import texture2ddecoder
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import arcpack
import deswizzle
import fonttex
import mtarc

SRC = os.path.join(ROOT, '_work', 'romfs', 'nativeNXx64', 'RZZC', 'romNX', 'TitleUI.arc')
OUT = os.path.join(ROOT, 'build', 'romfs', 'nativeNXx64', 'RZZC', 'romNX', 'TitleUI.arc')
NAME = r'Common\ui\02_title\tex\launcher_13_HQ'
LOGO_DIR = os.path.join(ROOT, 'launcher', 'logo_src')
# 원래 로고 덩어리(알파 > 8) 상자 (x0, y0, x1, y1), 원본 시트에서 실측
SLOTS = {'zero1': (28, 46, 573, 260), 'zero4': (603, 46, 1201, 260), 'zero2': (19, 351, 581, 567), 'zero3': (8, 656, 593, 872),
         'zx': (674, 343, 1133, 573), 'zxa': (707, 626, 1097, 901)}   # 그림 파일 = launcher/logo_src/<키>_kr.png
CLEAR = 6        # 원래 로고의 옅은 빛 번짐까지 지우는 여백
BG = (123, 0, 123, 77)   # 원본 투명 칸 값(인코딩 공간)


def fail(m):
    sys.exit('launcher_logo: ' + m)


def mip_layout(tex):
    w = struct.unpack_from('<I', tex, 8)[0]
    W, H, mips = (w >> 6) & 0x1FFF, (w >> 19) & 0x1FFF, w & 0x3F
    total = struct.unpack_from('<I', tex, 16)[0]
    data_at = len(tex) - total
    offs = [0] + list(struct.unpack_from(f'<{mips - 1}I', tex, 24))
    sizes = []
    for k in range(mips):
        mw, mh = max(W >> k, 1), max(H >> k, 1)
        sizes.append((mw, mh))
    return W, H, mips, data_at, total, offs, sizes


def swz(lin, mw, mh):
    wb, hb = (mw + 3) // 4, (mh + 3) // 4
    return deswizzle.swizzle(lin, wb, hb, 16, fonttex.block_height(hb))


def unswz(data, mw, mh):
    wb, hb = (mw + 3) // 4, (mh + 3) // 4
    return deswizzle.deswizzle(data, wb, hb, 16, fonttex.block_height(hb))[0]


def to_enc(rgba):
    a = rgba.astype(np.float32)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = (b - y) / 1.772
    cr = (r - y) / 1.402
    out = np.stack([cr + 128, al, cb + 128, y], -1)
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def to_rgb(enc):
    a = enc.astype(np.float32)
    cr, al, cb, y = a[..., 0] - 128, a[..., 1], a[..., 2] - 128, a[..., 3]
    out = np.stack([y + 1.402 * cr, y - 0.344136 * cb - 0.714136 * cr, y + 1.772 * cb, al], -1)
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def bc3(enc):
    h, w = enc.shape[:2]
    return etcpak.compress_bc3(np.ascontiguousarray(enc).tobytes(), w, h)   # etcpak 은 RGBA 입력(BGRA 로 주면 R·B 가 뒤바뀜)


def build():
    d, _, _, es = mtarc.parse(SRC)
    E = {e['name']: e for e in es}
    tex = mtarc.blob(d, E[NAME])
    if tex[:4] != b'TEX\0' or (struct.unpack_from('<I', tex, 12)[0] >> 8) & 0xFF != 0x2B:
        fail('텍스처 형식이 BC3(0x2B) 가 아님')
    W, H, mips, data_at, total, offs, sizes = mip_layout(tex)
    data = tex[data_at:]
    # 게이트: 원본 모든 밉을 풀었다 다시 배치하면 원본 바이트와 같아야 한다(배치 계산이 맞는지)
    for k, (mw, mh) in enumerate(sizes):
        end = offs[k + 1] if k + 1 < mips else total
        lin = unswz(data[offs[k]:end], mw, mh)
        back = swz(lin, mw, mh)
        if back != data[offs[k]:offs[k] + len(back)] or offs[k] + len(back) > end:
            fail(f'밉 {k} 배치 왕복 불일치')
    lin0 = unswz(data[:offs[1]], W, H)
    enc = np.frombuffer(texture2ddecoder.decode_bc3(lin0, W, H), np.uint8).reshape(H, W, 4)[..., [2, 1, 0, 3]].copy()
    if tuple(enc[2, 2]) != BG:
        fail(f'원본 투명 칸 값이 예상과 다름 {tuple(enc[2, 2])}')
    for n, (x0, y0, x1, y1) in SLOTS.items():
        a = enc[y0:y1 + 1, x0:x1 + 1, 1]
        if (a > 8).mean() < 0.3:
            fail(f'{n} 로고 자리에 원래 로고가 없음')
        enc[max(y0 - CLEAR, 0):y1 + CLEAR + 1, max(x0 - CLEAR, 0):x1 + CLEAR + 1] = BG
        logo = Image.open(os.path.join(LOGO_DIR, f'{n}_kr.png')).convert('RGBA')
        logo = logo.crop(logo.getbbox())
        bw, bh = x1 - x0 + 1, y1 - y0 + 1
        s = min(bw / logo.width, bh / logo.height)
        lw, lh = round(logo.width * s), round(logo.height * s)
        small = np.asarray(logo.resize((lw, lh), Image.LANCZOS))
        e = to_enc(small)
        e[small[..., 3] == 0] = BG
        ox, oy = x0 + (bw - lw) // 2, y0 + (bh - lh) // 2
        region = enc[oy:oy + lh, ox:ox + lw]
        m = small[..., 3:4] > 0
        enc[oy:oy + lh, ox:ox + lw] = np.where(m, e, region)
        print(f'{n}: {logo.width}x{logo.height} -> {lw}x{lh} @ ({ox},{oy}) 상자 {bw}x{bh}')
    # 밉: 인코딩 공간에서 2x2 평균(원래 텍스처도 같은 공간의 밉)
    out = bytearray(total)
    level = enc
    for k, (mw, mh) in enumerate(sizes):
        if k:
            p = level.astype(np.float32)
            ph, pw = p.shape[:2]
            if ph > 1 and pw > 1:
                p = (p[0:ph - ph % 2:2, 0:pw - pw % 2:2] + p[1::2, 0:pw - pw % 2:2] + p[0:ph - ph % 2:2, 1::2] + p[1::2, 1::2]) / 4
            level = np.clip(np.rint(p), 0, 255).astype(np.uint8)
        pad = np.zeros(((mh + 3) // 4 * 4, (mw + 3) // 4 * 4, 4), np.uint8)
        pad[...] = BG
        pad[:mh, :mw] = level[:mh, :mw]
        blk = swz(bc3(pad), mw, mh)
        end = offs[k + 1] if k + 1 < mips else total
        if offs[k] + len(blk) > end:
            fail(f'밉 {k} 크기 초과')
        out[offs[k]:offs[k] + len(blk)] = blk
    new = tex[:data_at] + bytes(out)
    # 되읽기: 밉 0 을 풀어 RGB 로 바꾼 미리 보기
    chk = np.frombuffer(texture2ddecoder.decode_bc3(unswz(bytes(out[:offs[1]]), W, H), W, H), np.uint8).reshape(H, W, 4)[..., [2, 1, 0, 3]]
    return new, to_rgb(chk)


def main():
    new, preview = build()
    if not os.path.exists(OUT):
        fail('build 의 TitleUI.arc 가 없다 — launcher_build.py 먼저')
    data = arcpack.rebuild(OUT, replace={NAME: new})
    open(OUT, 'wb').write(data)
    d, _, _, es = mtarc.parse(OUT)
    if mtarc.blob(d, {e['name']: e for e in es}[NAME]) != new:
        fail('arc 되읽기 불일치')
    if '--preview' in sys.argv:
        Image.fromarray(preview, 'RGBA').save(sys.argv[sys.argv.index('--preview') + 1])
    print('launcher_logo: 제로 1~4·ZX·ZXA 로고 교체 ->', OUT)


if __name__ == '__main__':
    main()
