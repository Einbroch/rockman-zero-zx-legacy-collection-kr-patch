"""제로 2·3편 공용 모듈 데이터 형식 (kohook/src/vwf.rs 와 같아야 한다).
머리 u32: 0 마법, 1 ngtab, 2 gtab_off, 3 qdat_off, 4 nquanta, 5 text_off, 6 text_len, 7 한글 구간 길이(text 앞에서부터),
  8 시스템 쌍 수, 9 시스템 쌍 위치(원래 오프셋 u32, 번역 text 오프셋 u32; 오름차순), 10 시스템 오프셋표 위치(0=없음),
  11 시스템 본문 위치, 12 뱅크 수, 13 한글 구간 시작(text 기준), 14~ 뱅크 (ot, body) — text 기준 오프셋. 위치는 모두 블롭 시작 기준."""
import struct


def pack(magic, gtab, qdat, text, kr_len, sys_pairs, sys_ot, sys_text_off, banks, kr_start=0):
    """sys_ot: 시스템 오프셋표 바이트(없으면 None), sys_text_off: 시스템 본문 시작의 text 기준 오프셋."""
    assert len(gtab) % 4 == 0 and len(qdat) % 32 == 0 and kr_start + kr_len <= len(text)
    hdr_len = (4 * 14 + 8 * len(banks) + 15) // 16 * 16
    off_g = hdr_len
    off_q = off_g + len(gtab)
    off_s = off_q + len(qdat)
    off_o = off_s + 8 * len(sys_pairs)
    off_t = off_o + (len(sys_ot) if sys_ot else 0)
    off_t = (off_t + 3) & ~3
    hdr = struct.pack('<4s13I', magic, len(gtab) // 4, off_g, off_q, len(qdat) // 32, off_t, len(text), kr_len,
                      len(sys_pairs), off_s, off_o if sys_ot else 0,
                      off_t + sys_text_off if sys_ot else 0, len(banks), kr_start)
    for ot, body in banks:
        hdr += struct.pack('<II', ot, body)
    hdr = hdr.ljust(hdr_len, b'\0')
    blob = bytearray(hdr + gtab + qdat + b''.join(struct.pack('<II', a, b) for a, b in sys_pairs))
    if sys_ot:
        blob += sys_ot
    while len(blob) < off_t:
        blob.append(0)
    blob += text
    assert len(blob) == off_t + len(text)
    return bytes(blob)


def msg_end(b, a):
    """메시지 끝(0xFF 포함). F3~F8 은 인수 1바이트, F0 은 확장 글자 1바이트를 건너뛴다."""
    p = a
    while True:
        c = b[p]
        if c == 0xFF:
            return p + 1
        p += 2 if 0xF3 <= c <= 0xF8 or c == 0xF0 else 1


def pages(msg):
    """메시지(끝 FF 포함)를 쪽(FD/FE 구분) 경계 위치 목록으로. 반환: 각 쪽 끝 위치(구분 바이트 위치) 목록."""
    out, p = [], 0
    while True:
        c = msg[p]
        if c == 0xFF:
            out.append(p)
            return out
        if c in (0xFD, 0xFE):
            out.append(p)
        p += 2 if 0xF3 <= c <= 0xF8 or c == 0xF0 else 1


def native_cuts(src, img, relocs, offtab, texttab, nbanks, main_ot, main_body, title):
    """컬렉션 main 의 일본판 대사를 GBA 일본판과 칸마다 대조한다.
    같으면 통과, main 이 GBA 의 앞 n 쪽만 남긴 것이면 {(뱅크, 칸): n}, 같은 뱅크 다른 칸의 글로 바꿨으면
    {(뱅크, 칸): ('alias', 그 칸)}, 그 밖의 차이는 오류."""
    cuts = {}
    for i in range(nbanks):
        jo = struct.unpack_from('<I', src, offtab + 4 * i)[0] - 0x08000000
        jb = struct.unpack_from('<I', src, texttab + 4 * i)[0] - 0x08000000
        mo, mb = relocs.get(main_ot + 8 * i), relocs.get(main_body + 8 * i)
        if mo is None or mb is None:
            raise ValueError(f'{title} 뱅크 {i}: main 배열 재배치 없음')
        n = (jb - jo) // 2
        for s in range(n):
            a = struct.unpack_from('<H', src, jo + 2 * s)[0] + jb
            # 칸이 하나뿐인 뱅크의 오프셋표는 bss(0으로 채워짐)에 있다
            c = (struct.unpack_from('<H', img, mo + 2 * s)[0] if mo + 2 * s + 2 <= len(img) else 0) + mb
            ga, gc = src[a:msg_end(src, a)], img[c:msg_end(img, c)]
            if ga == gc:
                continue
            pa = pages(ga)
            k = len(pages(gc))
            if k < len(pa) and gc[:-1] == ga[:pa[k - 1]]:
                cuts[(i, s)] = k
                continue
            # 컬렉션판이 이 칸을 같은 뱅크의 다른 칸(일본판 그대로인 칸)과 같은 글로 돌려 놓은 경우
            same = [t for t in range(n) if t != s and
                    src[jb + struct.unpack_from('<H', src, jo + 2 * t)[0]:][:len(gc)] == gc]
            if same:
                cuts[(i, s)] = ('alias', same[0])
                continue
            raise ValueError(f'{title} {i:02X}{s:02X}: 컬렉션판 대사가 쪽 줄임이 아닌 방식으로 다름')
    return cuts


def apply_cuts(rom, cuts, offtab, texttab):
    """한글 롬 사본(bytearray)에서 cuts 의 칸을 앞 n 쪽에서 끝내거나(구분 바이트를 FF 로),
    ('alias', t) 면 그 칸의 오프셋을 t 칸 오프셋과 같게 한다."""
    for (i, s), k in sorted(cuts.items(), key=lambda kv: kv[0]):
        ot = struct.unpack_from('<I', rom, offtab + 4 * i)[0] - 0x08000000
        body = struct.unpack_from('<I', rom, texttab + 4 * i)[0] - 0x08000000
        if isinstance(k, tuple):
            struct.pack_into('<H', rom, ot + 2 * s, struct.unpack_from('<H', rom, ot + 2 * k[1])[0])
            continue
        a = body + struct.unpack_from('<H', rom, ot + 2 * s)[0]
        pg = pages(bytes(rom[a:msg_end(rom, a)]))
        if len(pg) <= k:
            raise ValueError(f'{i:02X}{s:02X}: 한글 번역 쪽 수({len(pg)})가 자를 쪽 수({k}) 이하')
        rom[a + pg[k - 1]] = 0xFF
