"""GBA BIOS LZ77(type 0x10) 해제·압축.
VRAM 해제(LZ77UnCompVram)는 16비트 단위로 쓰므로 거리 1 매치를 쓰면 안 된다 (vram_safe=True)."""


def decompress(data, off=0):
    """-> (출력 bytes, 소비한 입력 길이)"""
    assert data[off] == 0x10, f'not LZ77 at {off:#x}'
    size = data[off + 1] | data[off + 2] << 8 | data[off + 3] << 16
    out = bytearray()
    p = off + 4
    while len(out) < size:
        flags = data[p]; p += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> bit):
                b1, b2 = data[p], data[p + 1]; p += 2
                n = (b1 >> 4) + 3
                d = ((b1 & 0xF) << 8 | b2) + 1
                for _ in range(n):
                    out.append(out[-d])
            else:
                out.append(data[p]); p += 1
    return bytes(out[:size]), p - off


def compress(data, vram_safe=True):
    n = len(data)
    out = bytearray([0x10, n & 0xFF, n >> 8 & 0xFF, n >> 16 & 0xFF])
    mind = 2 if vram_safe else 1
    # 해시로 후보 찾기 (3바이트)
    heads = {}
    i = 0
    while i < n:
        flag_pos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if i >= n:
                break
            best_len = 0; best_d = 0
            key = data[i:i + 3]
            if len(key) == 3:
                for j in reversed(heads.get(key, [])[-64:]):
                    d = i - j
                    if d > 0x1000:
                        break
                    if d < mind:
                        continue
                    l = 0
                    while l < 18 and i + l < n and data[j + l] == data[i + l]:
                        l += 1
                    if l > best_len:
                        best_len, best_d = l, d
                        if l == 18:
                            break
            if best_len >= 3:
                flags |= 0x80 >> bit
                v = (best_len - 3) << 12 | (best_d - 1)
                out += bytes([v >> 8, v & 0xFF])
                step = best_len
            else:
                out.append(data[i]); step = 1
            for k in range(step):
                if i + k + 3 <= n:
                    heads.setdefault(data[i + k:i + k + 3], []).append(i + k)
            i += step
        out[flag_pos] = flags
    while len(out) % 4:
        out.append(0)
    return bytes(out)


def compress_optimal(data, vram_safe=True):
    """최단 길이 분할(DP). 같은 해제 결과에서 compress() 보다 짧거나 같다."""
    n = len(data)
    mind = 2 if vram_safe else 1
    heads = {}
    longest = [(0, 0)] * n   # 위치마다 (가장 긴 일치 길이, 거리)
    for i in range(n):
        key = data[i:i + 3]
        best_l = best_d = 0
        if len(key) == 3:
            for j in reversed(heads.get(key, [])):
                d = i - j
                if d > 0x1000:
                    break
                if d < mind:
                    continue
                l = 3
                while l < 18 and i + l < n and data[j + l] == data[i + l]:
                    l += 1
                if l > best_l:
                    best_l, best_d = l, d
                    if l == 18:
                        break
            heads.setdefault(key, []).append(i)
        longest[i] = (best_l, best_d)
    cost = [0] * (n + 1)
    choice = [0] * n
    for i in range(n - 1, -1, -1):
        c, ch = 9 + cost[i + 1], 1
        l, _ = longest[i]
        for k in range(3, l + 1):
            v = 17 + cost[i + k]
            if v < c:
                c, ch = v, k
        cost[i], choice[i] = c, ch
    out = bytearray([0x10, n & 0xFF, n >> 8 & 0xFF, n >> 16 & 0xFF])
    i = 0
    while i < n:
        flag_pos = len(out); out.append(0); flags = 0
        for bit in range(8):
            if i >= n:
                break
            k = choice[i]
            if k >= 3:
                d = longest[i][1]
                flags |= 0x80 >> bit
                v = (k - 3) << 12 | (d - 1)
                out += bytes([v >> 8, v & 0xFF])
            else:
                out.append(data[i])
            i += k
        out[flag_pos] = flags
    while len(out) % 4:
        out.append(0)
    return bytes(out)
