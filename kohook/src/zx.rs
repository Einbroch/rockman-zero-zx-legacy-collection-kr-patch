//! 록맨 ZX · ZX 어드벤트 — NDS 한글패치(리드 바이트 한글)를 네이티브 출력기에 이식. 게임 번호: 0 = ZX, 1 = ZXA.
//! 인코딩: 0x40~0x4F 리드 + 둘째 바이트(<0xF0) → 한글 코드 (리드-0x40)*240+둘째. 글리프는 16바이트 압축(2~12행 × 11비트)으로
//! data/zx.bin·zxa.bin 에 상주하고, 출력 때 글꼴 버퍼의 임시 칸(ZX 0x18A/0x18B, ZXA 0x225/0x226)에 번갈아 풀어 원래 그리기 경로로 그린다.
//! 글꼴 버퍼 = 전역 구조체 +0x3c08(머리: 폭 u16, 높이 u16, 글자당 바이트 u32 …) / +0x3c28(글리프).
//! 글자 폭 = 글리프 0행 u16 의 위 4비트(0이면 12). 글꼴 폭이 12가 아니면(font_pal 등) 아무것도 바꾸지 않는다.
//! ZXA 는 F0 사슬(F0 FF.. xx = 0xF0 + 0xFF*n + xx).
use crate::{rd, wr};

struct Game {
    glyphs: &'static [u8],
    scr0: usize,
    fabuf: usize,
    chain: bool,
}

static GAMES: [Game; 2] = [
    Game { glyphs: include_bytes!("../data/zx.bin"), scr0: 0x18a, fabuf: 0xd588, chain: false },
    Game { glyphs: include_bytes!("../data/zxa.bin"), scr0: 0x225, fabuf: 0xe508, chain: true },
];
const HDR: usize = 0x3c08;
const FONT: usize = 0x3c28;
static mut TOGGLE: usize = 0;

#[inline(always)]
fn game(id: u32) -> &'static Game {
    &GAMES[(id as usize) & 1]
}

#[inline(always)]
unsafe fn is_kfont(st: usize) -> bool {
    rd::<u16>(st + HDR) == 12 && rd::<u32>(st + HDR + 4) == 32
}

#[inline(always)]
unsafe fn is_lead(p: usize) -> bool {
    let c = rd::<u8>(p);
    (0x40..=0x4f).contains(&c) && rd::<u8>(p + 1) < 0xf0
}

unsafe fn unpack(g: &Game, st: usize, k: usize) -> u32 {
    let t = (TOGGLE ^ 1) & 1;
    TOGGLE = t;
    let slot = g.scr0 + t;
    let dst = st + FONT + slot * 32;
    let n = g.glyphs.len() / 16;
    let mut bits: u128 = 0;
    if k < n {
        for (i, b) in g.glyphs[k * 16..k * 16 + 16].iter().enumerate() {
            bits |= (*b as u128) << (i * 8);
        }
    }
    wr::<u16>(dst, 0xc000);
    wr::<u16>(dst + 2, 0);
    for y in 0..11 {
        wr::<u16>(dst + 4 + y * 2, ((bits >> (y * 11)) & 0x7ff) as u16);
    }
    for y in 13..16 {
        wr::<u16>(dst + y * 2, 0);
    }
    slot as u32
}

/// 출력기 공통 지점: c = 글리프 번호(일반 바이트 또는 F0 확장), p = 글자 마지막 바이트 주소.
/// 반환: 새 글리프 번호 | 더 읽은 바이트 수 << 16 | 폭 << 24 (폭 0 = 그대로)
#[no_mangle]
pub unsafe extern "C" fn zx_glyph(st: usize, c: u32, p: usize, id: u32) -> u64 {
    if st == 0 || !is_kfont(st) {
        return c as u64;
    }
    let g = game(id);
    let mut c = c;
    let mut extra = 0u64;
    if (0x40..=0x4f).contains(&c) && rd::<u8>(p) as u32 == c && rd::<u8>(p + 1) < 0xf0 {
        let k = (c as usize - 0x40) * 240 + rd::<u8>(p + 1) as usize;
        c = unpack(g, st, k);
        extra = 1;
    }
    let mut w = (rd::<u16>(st + FONT + (c as usize) * 32) >> 12) as u64;
    if w == 0 {
        w = 12;
    }
    c as u64 | extra << 16 | w << 24
}

/// F0 확장 글리프의 마지막 바이트로(ZXA 는 FF 사슬)
#[inline(always)]
unsafe fn skip_f0(g: &Game, mut s: usize) -> usize {
    s += 1;
    if g.chain {
        while rd::<u8>(s) == 0xff {
            s += 1;
        }
    }
    s
}

/// 원래 건너뛰기(글, n) → n 글자 뒤 포인터. 원래 함수와 같이 n=0 이면 그대로 돌려주고,
/// 그 밖에는 제어 바이트를 n 과 상관없이 건너뛰며 n 글자를 센 뒤 **다음 글리프 앞**(FD 이상이면 거기)에서 멈춘다.
#[no_mangle]
pub unsafe extern "C" fn zx_skip(st: usize, mut s: usize, mut n: u32, id: u32) -> usize {
    if n == 0 {
        return s;
    }
    let g = game(id);
    let kf = st != 0 && is_kfont(st);
    loop {
        let c = rd::<u8>(s);
        if c >= 0xfd {
            break;
        }
        if c > 0xf0 {
            if c <= 0xf8 {
                s += 1;
            } else if c == 0xf9 {
                s += 2;
            }
            s += 1;
            continue;
        }
        if n == 0 {
            break;
        }
        if c == 0xf0 {
            s = skip_f0(g, s);
        } else if kf && is_lead(s) {
            s += 1;
        }
        n -= 1;
        s += 1;
    }
    s
}

/// 원래 글자 수 세기(글) → 글자 수. FA 는 FA 버퍼를 센다.
#[no_mangle]
pub unsafe extern "C" fn zx_count(st: usize, mut s: usize, _n: u32, id: u32) -> u32 {
    let g = game(id);
    let kf = st != 0 && is_kfont(st);
    let mut n = 0u32;
    let mut depth = 0;
    let mut ret = 0usize;
    loop {
        let c = rd::<u8>(s);
        if c >= 0xfd {
            if depth == 0 {
                break;
            }
            depth = 0;
            s = ret + 1;
            continue;
        }
        if c <= 0xf0 {
            n += 1;
            if c == 0xf0 {
                s = skip_f0(g, s);
            } else if kf && is_lead(s) {
                s += 1;
            }
        } else if c <= 0xf8 {
            s += 1;
        } else if c == 0xf9 {
            s += 2;
        } else if c == 0xfa && depth == 0 && st != 0 {
            depth = 1;
            ret = s;
            s = st + g.fabuf;
            continue;
        }
        s += 1;
    }
    n & 0xffff
}
