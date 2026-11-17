"""알파 전용 BC7 인코더(모드 6) — 런처 글꼴 페이지용. RGB 는 흰색(255) 고정, 알파 0~255.
모드 6: 7비트 끝점 RGBA ×2 + 끝점별 p비트, 4비트 색인 16개(첫 색인은 3비트 — 최상위 0 이어야 한다).
p비트가 RGB 와 알파에 같이 붙으므로 RGB 255 를 내려면 p=1, 알파 끝점은 홀수가 된다(0 은 1, 255 는 255)."""
import numpy as np

W4 = np.array([0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64], np.int32)


def encode(alpha):
    """alpha: (H, W) uint8 (H, W 는 4의 배수) → BC7 블록 바이트(행 우선, 블록 16바이트)"""
    H, W = alpha.shape
    a = alpha.reshape(H // 4, 4, W // 4, 4).transpose(0, 2, 1, 3).reshape(-1, 16).astype(np.int32)
    n = a.shape[0]
    lo = a.min(1)
    hi = a.max(1)
    q0 = np.clip((lo - 1) // 2, 0, 127)      # 7비트, 실제 값 = q*2+1
    q1 = np.clip((hi - 1 + 1) // 2, 0, 127)
    e0 = q0 * 2 + 1
    e1 = q1 * 2 + 1
    pal = ((64 - W4)[None, :] * e0[:, None] + W4[None, :] * e1[:, None] + 32) >> 6   # (n,16)
    idx = np.abs(a[:, :, None] - pal[:, None, :]).argmin(2)                          # (n,16)
    flip = idx[:, 0] >= 8
    q0f = np.where(flip, q1, q0)
    q1f = np.where(flip, q0, q1)
    idx = np.where(flip[:, None], 15 - idx, idx)
    # 128비트 조립: 낮은 64비트 / 높은 64비트
    bits = []   # (값 배열, 비트 수) 순서대로 LSB 부터
    bits.append((np.full(n, 0x40, np.int64), 7))          # 모드 6
    for ch in range(3):                                   # R0 R1 G0 G1 B0 B1 = 127
        bits.append((np.full(n, 127, np.int64), 7))
        bits.append((np.full(n, 127, np.int64), 7))
    bits.append((q0f.astype(np.int64), 7))
    bits.append((q1f.astype(np.int64), 7))
    bits.append((np.ones(n, np.int64), 1))                # P0
    bits.append((np.ones(n, np.int64), 1))                # P1
    bits.append((idx[:, 0].astype(np.int64), 3))
    for k in range(1, 16):
        bits.append((idx[:, k].astype(np.int64), 4))
    lo64 = np.zeros(n, np.uint64)
    hi64 = np.zeros(n, np.uint64)
    pos = 0
    for v, w in bits:
        v = v.astype(np.uint64)
        if pos + w <= 64:
            lo64 |= v << np.uint64(pos)
        elif pos >= 64:
            hi64 |= v << np.uint64(pos - 64)
        else:
            k = 64 - pos
            lo64 |= (v & np.uint64((1 << k) - 1)) << np.uint64(pos)
            hi64 |= v >> np.uint64(k)
        pos += w
    assert pos == 128
    out = np.empty((n, 2), np.uint64)
    out[:, 0] = lo64
    out[:, 1] = hi64
    return out.astype('<u8').tobytes()
