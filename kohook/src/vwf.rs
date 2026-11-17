//! 록맨 제로 2·3 공용 — 12px 한글 가변폭 출력기 (GBA rz1/asm/vwf.s + 2·3편 확장 인코딩 이식).
//! 1편과 같은 4px 조각 칸 합성. 2·3편 공통:
//! - 글꼴 경로가 0x200 이상 코드를 다르게 다루므로 업로드의 노드 분기도 훅: 내 노드(코드 위 4비트 0xE)는 내 타일 버퍼에서 VRAM 으로.
//! - 인코딩: 모듈 블롭의 한글 구간 안의 글은 EC~F0 리드 + 트레일(g = (리드-0xEC+2)*0x100 + 트레일), 밖의 글은 원래 인코딩
//!   (F0 xx = 0xF0+xx). 글자 수는 원래 건너뛰기와 같은 셈: EC~EF 리드 쌍 = 2, F0 쌍 = 1.
//! - F7 xx = 팔레트 (xx + 기준), F2 = 강조색(픽셀 <<2).
//! 데이터 머리(u32): 0 마법, 1 ngtab, 2 gtab_off, 3 qdat_off, 4 nquanta, 5 text_off, 6 text_len, 7 한글 구간 길이,
//!   8 시스템 쌍 수, 9 시스템 쌍 위치(원래 오프셋 u32, 번역 오프셋 u32), 10 시스템 오프셋표 위치(0=없음), 11 시스템 본문 위치,
//!   12 뱅크 수, 13 한글 구간 시작(text 기준), 14~ 뱅크 (ot, body) — text 기준 오프셋.
use crate::{base, rd, wr};

pub const V_LANG: usize = 0x30c7c00; // u8, 0 = 일본판
pub const V_MODE: usize = 0x30cd158; // u32, 0 이면 문맥 B

// 문맥 안 캐시 위치: 노드는 +0x980 에서 0x10 씩 아래로 80개(2~4편 같음).
// 목록 기준(lists)에서 +0x10 활성, +0x18 지난, +0x20 빈, +0x28 이름 포인터 — 2·3편 0x980, 4편 0xa80
const NODE_TOP: usize = 0x980;
const NNODE: usize = 80;
pub const TAG: u32 = 0xE000;
const NSEL: usize = 6; // 타일 버퍼 칸: 2편 문맥 A/B = 0/1, 3편 = 2/3, 4편 = 4/5

#[repr(C, align(16))]
struct Tiles([u8; NSEL * NNODE * 64]);
static mut TILES: Tiles = Tiles([0; NSEL * NNODE * 64]);

pub enum Pal {
    Fixed(u16),     // 2편: xx + 2
    CtxI16(usize),  // 3편: xx + 문맥 +0xa (s16)
}

pub struct Game {
    pub data: &'static [u8],
    pub ctx_a: usize,
    pub ctx_b: usize,
    pub sel0: u32,
    pub lists: usize,
    pub bank_ot: usize,
    pub bank_body: usize,
    pub sys_text: usize, // 2편: main 시스템 본문(포인터 변환 대상), 0 = 없음
    pub sys_len: usize,
    pub sys_var_ot: usize, // 3편: 시스템 오프셋표·본문 변수, 0 = 없음
    pub sys_var_text: usize,
    pub pal: Pal,
}

impl Game {
    fn h32(&self, i: usize) -> usize { self.d32(i * 4) as usize }
    fn d32(&self, o: usize) -> u32 {
        let d = self.data;
        u32::from_le_bytes([d[o], d[o + 1], d[o + 2], d[o + 3]])
    }
    fn ngtab(&self) -> usize { self.h32(1) }
    fn gtab(&self, g: usize) -> u32 { self.d32(self.h32(2) + g * 4) }
    fn qrow(&self, q: usize, r: usize) -> u32 {
        let o = self.h32(3) + q * 32 + r * 2;
        u16::from_le_bytes([self.data[o], self.data[o + 1]]) as u32
    }
    fn blob(&self) -> usize { self.data.as_ptr() as usize }
    fn text_lo(&self) -> usize { self.blob() + self.h32(5) }
    fn kr_lo(&self) -> usize { self.text_lo() + self.h32(13) }
    fn kr_hi(&self) -> usize { self.kr_lo() + self.h32(7) }
}

pub fn jp(b: usize) -> bool { unsafe { rd::<u8>(b + V_LANG) == 0 } }

/// 초기화: 대사 뱅크 배열(일본판 칸)을 덮고, 일본판이면 시스템 표 변수도 바꾼다.
pub unsafe fn init(g: &Game, b: usize) {
    for i in 0..g.h32(12) {
        let (ot, body) = (g.h32(14 + i * 2), g.h32(15 + i * 2));
        wr::<usize>(b + g.bank_ot + 8 * i, g.text_lo() + ot);
        wr::<usize>(b + g.bank_body + 8 * i, g.text_lo() + body);
    }
    if g.sys_var_ot != 0 && jp(b) && g.h32(10) != 0 {
        wr::<usize>(b + g.sys_var_ot, g.blob() + g.h32(10));
        wr::<usize>(b + g.sys_var_text, g.blob() + g.h32(11));
    }
}

/// main 시스템 문자열 시작 포인터 → 번역문 (2편, 일본판, 번역 칸만)
pub unsafe fn xlate(g: &Game, p: usize) -> usize {
    let b = base();
    if g.sys_text == 0 || !jp(b) || p < b + g.sys_text || p >= b + g.sys_text + g.sys_len {
        return p;
    }
    let key = (p - b - g.sys_text) as u32;
    let (n, at) = (g.h32(8), g.h32(9));
    let (mut lo, mut hi) = (0usize, n);
    while lo < hi {
        let mid = (lo + hi) / 2;
        let k = g.d32(at + mid * 8);
        if k == key {
            return g.text_lo() + g.d32(at + mid * 8 + 4) as usize;
        }
        if k < key { lo = mid + 1 } else { hi = mid }
    }
    p
}

/// 업로드 훅: 내 노드의 타일 두 장(64바이트)을 VRAM 타일 기준 vram 에 쓴다
#[no_mangle]
pub unsafe extern "C" fn zc_upload(node: usize, vram: usize) {
    let code = rd::<u16>(node + 8) as usize;
    let slot = (code >> 8 & 0xf) * NNODE + (code & 0xff);
    if slot >= NSEL * NNODE {
        return;
    }
    let tile = (rd::<u16>(node + 0xa) & 0xfff) as usize;
    let src = ((&raw const TILES) as *const u8).add(slot * 64);
    core::ptr::copy_nonoverlapping(src, (vram + tile * 32) as *mut u8, 64);
}

struct R<'a> {
    g: &'a Game,
    ctx: usize,
    sel: u32,
    pos: usize,
    pending: u32, // 대기 조각 (u32::MAX = 없음), bit15 = 강조색
    color: u32,
    pal: u16,
}

impl<'a> R<'a> {
    fn node_idx(&self, n: usize) -> u32 { ((self.ctx + NODE_TOP - n) / 0x10) as u32 }
    fn code(&self, n: usize) -> u32 { TAG | self.sel << 8 | self.node_idx(n) }

    unsafe fn compose(&self, n: usize, a: u32, bq: u32) {
        let idx = self.node_idx(n) as usize;
        if idx >= NNODE {
            return; // 노드 배치가 예상과 다름 — 남의 칸을 덮지 않는다
        }
        let slot = self.sel as usize * NNODE + idx;
        let t = ((&raw mut TILES) as *mut u8 as usize) + slot * 64;
        let qa = (a & 0x7fff) as usize;
        let qb = bq as usize;
        for r in 0..16 {
            let mut row = self.g.qrow(qa, r) | (self.g.qrow(qb, r) << 16);
            if a & 0x8000 != 0 {
                row <<= 2;
            }
            let at = if r < 8 { r * 4 } else { 32 + (r - 8) * 4 };
            wr::<u32>(t + at, row);
        }
    }

    unsafe fn put(&mut self, n: usize) {
        let t = (rd::<u16>(n + 0xa) & 0xfff) | (self.pal << 12);
        wr::<u16>(self.pos, t);
        wr::<u16>(self.pos + 0x40, t + 1);
        self.pos += 2;
    }

    unsafe fn matches(&self, n: usize, a: u32, bq: u32) -> bool {
        rd::<u16>(n + 8) as u32 == self.code(n) && rd::<u16>(n + 0xc) as u32 == a && rd::<u16>(n + 0xe) as u32 == bq
    }

    unsafe fn cell(&mut self, a: u32, bq: u32) -> bool {
        let act = self.ctx + self.g.lists + 0x10;
        let old = self.ctx + self.g.lists + 0x18;
        let free = self.ctx + self.g.lists + 0x20;
        let mut n: usize = rd(act);
        while n != 0 {
            if self.matches(n, a, bq) {
                self.put(n);
                return true;
            }
            n = rd(n);
        }
        let mut prev = old;
        n = rd(old);
        while n != 0 {
            if self.matches(n, a, bq) {
                wr::<usize>(prev, rd::<usize>(n));
                wr::<usize>(n, rd::<usize>(act));
                wr::<usize>(act, n);
                self.put(n);
                return true;
            }
            prev = n;
            n = rd(n);
        }
        n = rd(free);
        if n == 0 {
            n = rd(old);
            wr::<usize>(free, n);
            wr::<usize>(old, 0);
            if n == 0 {
                return false;
            }
        }
        wr::<usize>(free, rd::<usize>(n));
        wr::<usize>(n, rd::<usize>(act));
        wr::<usize>(act, n);
        self.compose(n, a, bq);
        wr::<u16>(n + 8, self.code(n) as u16);
        wr::<u16>(n + 0xc, a as u16);
        wr::<u16>(n + 0xe, bq as u16);
        self.put(n);
        let t = rd::<u16>(n + 0xa);
        wr::<u16>(n + 0xa, t | 0x8000);
        true
    }

    unsafe fn emit(&mut self, q: u32) -> bool {
        if self.pending == u32::MAX {
            self.pending = q | self.color;
            return true;
        }
        let a = self.pending;
        self.pending = u32::MAX;
        self.cell(a, q)
    }

    unsafe fn flush(&mut self) -> bool {
        if self.pending != u32::MAX { self.emit(0) } else { true }
    }
}

/// 문맥 (모드 ≠ 0 → A, 0 → B)
pub unsafe fn ctx(g: &Game) -> (usize, u32) {
    let b = base();
    let mode: u32 = rd(b + V_MODE);
    if mode != 0 { (b + g.ctx_a, g.sel0) } else { (b + g.ctx_b, g.sel0 + 1) }
}

/// 대사 → 타일맵. dst = 타일맵 칸, text = 글, count = 글자 수 → 남은 수
pub unsafe fn render(g: &Game, ctx: usize, sel: u32, dst: usize, text: usize, count: u32) -> u32 {
    let mut r = R { g, ctx, sel, pos: dst, pending: u32::MAX, color: 0, pal: 0 };
    let mut line = dst;
    let mut p = xlate(g, text);
    let mut cnt = (count & 0xffff) as i32;
    let mut name_ret: usize = 0;
    let (klo, khi) = (g.kr_lo(), g.kr_hi());
    let ng = g.ngtab();
    while cnt > 0 {
        let c = rd::<u8>(p) as u32;
        let kr = p >= klo && p < khi;
        if c > 0xfc {
            if name_ret != 0 {
                p = name_ret + 1;
                name_ret = 0;
                continue;
            }
            break;
        }
        let gl: usize;
        if kr && (0xec..=0xf0).contains(&c) {
            gl = ((c as usize - 0xec + 2) << 8) + rd::<u8>(p + 1) as usize;
            p += 2;
            cnt -= if c == 0xf0 { 1 } else { 2 };
            if cnt < 0 { cnt = 0; }
        } else if c == 0xf0 {
            gl = 0xf0 + rd::<u8>(p + 1) as usize;
            p += 2;
            cnt -= 1;
        } else if c > 0xf0 {
            match c {
                0xf1 => { r.color = 0; r.pal = 0; p += 1; }
                0xf2 => { r.color = 0x8000; r.pal = 0; p += 1; }
                0xf7 => {
                    let base_pal = match g.pal {
                        Pal::Fixed(v) => v,
                        Pal::CtxI16(o) => rd::<i16>(ctx + o) as u16,
                    };
                    r.color = 0;
                    r.pal = (rd::<u8>(p + 1) as u16).wrapping_add(base_pal) & 0xf;
                    p += 2;
                }
                0xfc => {
                    r.flush();
                    line += 0x80;
                    r.pos = line;
                    p += 1;
                }
                0xf9 => {
                    name_ret = p;
                    p = rd::<usize>(ctx + g.lists + 0x28);
                }
                0xf3..=0xf8 => p += 2,
                _ => p += 1,
            }
            continue;
        } else {
            gl = c as usize;
            p += 1;
            cnt -= 1;
        }
        if gl >= ng { continue; }
        let e = g.gtab(gl);
        let rep = e >> 31 != 0;
        let mut q = e & 0xffff;
        for _ in 0..((e >> 16) & 0x7fff) {
            if !r.emit(q) {
                return cnt as u32;
            }
            if !rep { q += 1; }
        }
    }
    r.flush();
    cnt as u32
}
