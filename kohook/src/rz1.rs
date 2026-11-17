//! 록맨 제로 1 — 12px 한글 가변폭 출력기 (GBA rz1/asm/vwf.s 이식).
//! 글자 = 4px 조각 n개, 칸(8px) = 조각 두 개(A,B). 칸마다 캐시 노드 하나를 쓰고, 노드에 가짜 코드
//! 0x200 + 문맥*0x50 + 노드번호(강조색이면 |0x8000)를 넣어 그 코드 자리의 글꼴 버퍼에 타일을 써 둔다.
//! 원래 업로드(0x470a70)가 노드 코드로 글꼴을 읽어 VRAM 에 옮기므로 업로드는 고치지 않는다.
use crate::{base, rd, wr};

static DATA: &[u8] = include_bytes!("../data/rz1.bin");

/// 결과 화면 데이터: [0] 8px 글꼴 0x800(실·패·성·공 칸), [0x800] u32 칭호 오프셋[20], 문자열(대사 인코딩)
#[repr(C, align(16))]
pub struct Al<T>(T);
const RES_LEN: usize = include_bytes!("../data/rz1_result.bin").len();
#[no_mangle]
pub static RZ1_RESULT: Al<[u8; RES_LEN]> = Al(*include_bytes!("../data/rz1_result.bin"));
#[no_mangle]
pub static RZ1_RESULT_LEN: usize = RES_LEN;
const TITLE_TAB: usize = 0x285ed78; // 일본판 칭호 포인터 20개 (8바이트)
static mut TITLE_ORIG: [usize; 20] = [0; 20];

// main 오프셋 (업데이트 v262144 기준)
const V_LANG: usize = 0x30c7c00; // u8, 0 = 일본판
const V_MODE: usize = 0x30cd158; // u32, 0 이면 문맥 B
const CTX_A: usize = 0x30ad408; // GOT f20
const CTX_B: usize = 0x30acc98; // GOT f28
const V_FONT: usize = 0x30adb88; // 현재 글꼴 포인터
const V_SYS_OT: usize = 0x30adb78;
const V_SYS_BODY: usize = 0x30adb80;
const JP_FONT: usize = 0x214e87c;
const JP_FONT_LEN: usize = 0x7c00;
const BANK_OT: usize = 0x28eaee0;
const BANK_BODY: usize = 0x28eaf78;

const PSEUDO: u32 = 0x200;
const FONT_LEN: usize = 0xA800;
#[repr(align(16))]
struct Font([u8; FONT_LEN]);
static mut FONT: Font = Font([0; FONT_LEN]);

fn h32(i: usize) -> usize {
    u32::from_le_bytes([DATA[i * 4], DATA[i * 4 + 1], DATA[i * 4 + 2], DATA[i * 4 + 3]]) as usize
}
fn ngtab() -> usize { h32(1) }
fn gtab(g: usize) -> u32 {
    let o = h32(2) + g * 4;
    u32::from_le_bytes([DATA[o], DATA[o + 1], DATA[o + 2], DATA[o + 3]])
}
fn qrow(q: usize, r: usize) -> u32 {
    let o = h32(3) + q * 32 + r * 2;
    u16::from_le_bytes([DATA[o], DATA[o + 1]]) as u32
}
fn text_ptr(off: usize) -> usize { DATA.as_ptr() as usize + h32(5) + off }
fn bank(i: usize) -> (usize, usize) { (h32(7 + i * 2), h32(8 + i * 2)) }

#[no_mangle]
pub unsafe extern "C" fn rz1_init(b: usize) {
    for i in 0..19 {
        let (ot, body) = bank(i);
        wr::<usize>(b + BANK_OT + 8 * i, text_ptr(ot));
        wr::<usize>(b + BANK_BODY + 8 * i, text_ptr(body));
    }
    // 칭호 표: 일본판이면 한글 문자열(대기열 출력기로 그림), 아니면 원래 값으로 되돌림
    let orig = &raw mut TITLE_ORIG;
    if (*orig)[0] == 0 {
        for i in 0..20 {
            (*orig)[i] = rd::<usize>(b + TITLE_TAB + 8 * i);
        }
    }
    let jp = rd::<u8>(b + V_LANG) == 0;
    let res = RZ1_RESULT.0.as_ptr() as usize;
    for i in 0..20 {
        let v = if jp {
            let o = 0x800 + 4 * i;
            res + u32::from_le_bytes([RZ1_RESULT.0[o], RZ1_RESULT.0[o + 1], RZ1_RESULT.0[o + 2], RZ1_RESULT.0[o + 3]]) as usize
        } else {
            (*orig)[i]
        };
        wr::<usize>(b + TITLE_TAB + 8 * i, v);
    }
    if !jp {
        return;
    }
    let f = (&raw mut FONT) as *mut u8;
    core::ptr::copy_nonoverlapping((b + JP_FONT) as *const u8, f, JP_FONT_LEN);
    wr::<usize>(b + V_FONT, f as usize);
    let (ot, body) = bank(19);
    wr::<usize>(b + V_SYS_OT, text_ptr(ot));
    wr::<usize>(b + V_SYS_BODY, text_ptr(body));
}

struct R {
    ctx: usize,
    sel: u32,
    pos: usize,      // 현재 타일맵 칸 (u16*)
    pending: u32,    // 대기 조각 (u32::MAX = 없음), bit15 = 색
    color: u32,
}

impl R {
    unsafe fn node_idx(&self, n: usize) -> u32 { ((self.ctx + 0x740 - n) / 0x10) as u32 }

    unsafe fn compose(&self, code: u32, a: u32, bq: u32) {
        let c = (code & 0x7fff) as usize; // 색 비트는 업로드가 떼고 읽는다
        let off = ((c << 6) & 0x3ffc00) | ((c & 0xf) << 5);
        let f = (&raw mut FONT) as *mut u8 as usize;
        let qa = (a & 0x7fff) as usize;
        let qb = bq as usize;
        for r in 0..16 {
            let row = qrow(qa, r) | (qrow(qb, r) << 16);
            let at = if r < 8 { off + r * 4 } else { off + 0x200 + (r - 8) * 4 };
            wr::<u32>(f + at, row);
        }
    }

    unsafe fn put(&mut self, n: usize) {
        let t = rd::<u16>(n + 0xa) & 0x7fff;
        wr::<u16>(self.pos, t);
        wr::<u16>(self.pos + 0x40, t + 1);
        self.pos += 2;
    }

    fn matches(n: usize, code: u32, a: u32, bq: u32) -> bool {
        unsafe {
            rd::<u16>(n + 8) as u32 == code && rd::<u16>(n + 0xc) as u32 == a && rd::<u16>(n + 0xe) as u32 == bq
        }
    }

    /// 칸 하나 (A = 왼쪽 조각|색, B = 오른쪽 조각). false = 캐시 고갈
    unsafe fn cell(&mut self, a: u32, bq: u32) -> bool {
        let act = self.ctx + 0x750;
        let old = self.ctx + 0x758;
        let free = self.ctx + 0x760;
        // 활성 목록
        let mut n: usize = rd(act);
        while n != 0 {
            let code = (PSEUDO + self.sel * 0x50 + self.node_idx(n)) | (a & 0x8000);
            if Self::matches(n, code, a, bq) {
                self.put(n);
                return true;
            }
            n = rd(n);
        }
        // 지난 프레임 목록 → 떼어서 활성으로
        let mut prev = old;
        n = rd(old);
        while n != 0 {
            let code = (PSEUDO + self.sel * 0x50 + self.node_idx(n)) | (a & 0x8000);
            if Self::matches(n, code, a, bq) {
                wr::<usize>(prev, rd::<usize>(n));
                wr::<usize>(n, rd::<usize>(act));
                wr::<usize>(act, n);
                self.put(n);
                return true;
            }
            prev = n;
            n = rd(n);
        }
        // 빈 칸 (없으면 지난 프레임 목록 전체를 빈 칸으로)
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
        let code = (PSEUDO + self.sel * 0x50 + self.node_idx(n)) | (a & 0x8000);
        self.compose(code, a, bq);
        wr::<u16>(n + 8, code as u16);
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

/// 원래 0x470500 대체: dst = 타일맵, text = 글, count = 글자 수 → 남은 수
#[no_mangle]
pub unsafe extern "C" fn rz1_render(dst: *mut u16, text: *const u8, count: u32) -> u32 {
    let b = base();
    let mode: u32 = rd(b + V_MODE);
    let (ctx, sel) = if mode != 0 { (b + CTX_A, 0) } else { (b + CTX_B, 1) };
    let mut r = R { ctx, sel, pos: dst as usize, pending: u32::MAX, color: 0 };
    let mut line = dst as usize;
    let mut p = text as usize;
    let mut cnt = (count & 0xffff) as i32;
    let mut name_ret: usize = 0;
    let ng = ngtab();
    while cnt > 0 {
        let c = rd::<u8>(p) as u32;
        if c > 0xfc {
            if name_ret != 0 {
                p = name_ret + 1;
                name_ret = 0;
                continue;
            }
            break;
        }
        let g: usize;
        if c >= 0xf0 {
            match c {
                0xf1 => { r.color = 0; p += 1; }
                0xf2 => { r.color = 0x8000; p += 1; }
                0xfc => {
                    r.flush();
                    line += 0x80;
                    r.pos = line;
                    p += 1;
                }
                0xf9 => {
                    name_ret = p;
                    p = rd::<usize>(ctx + 0x768);
                }
                0xf0 | 0xf3..=0xf8 => p += 2,
                _ => p += 1,
            }
            continue;
        } else if c >= 0x80 {
            g = 0x80 + (c as usize - 0x80) * 0xf0 + rd::<u8>(p + 1) as usize;
            p += 2;
            cnt -= 2;
            if cnt < 0 { cnt = 0; }
        } else {
            g = c as usize;
            p += 1;
            cnt -= 1;
        }
        if g >= ng { continue; }
        let e = gtab(g);
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
