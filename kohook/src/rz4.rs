//! 록맨 제로 4 — 공용 가변폭 출력기(vwf.rs) 설정.
//! 출력기 0x474b10 은 3편과 같은 (x, y, 글, 수). 노드는 2·3편처럼 +0x980 부터지만 목록·이름은 0x100 뒤(+0xa90~, 이름 +0xaa8).
//! 시스템 표는 초기화(0x4743c0)가 변수 0x30b1ae0(오프셋표)·0x30b1ae8(본문)에 넣어 두고 쓰므로 일본판이면 그 변수를 내 표로 바꾼다
//! (GBA 4편과 같은 구조: 원래 본문 기준 오프셋, 번역 칸은 한글 구간 [klo, khi) 안, 나머지는 원문).
use crate::rd;
use crate::vwf::{self, Game, Pal};

static G: Game = Game {
    data: include_bytes!("../data/rz4.bin"),
    ctx_a: 0x30b1028, // GOT e58
    ctx_b: 0x30b0570, // GOT e68
    sel0: 4,
    lists: 0xa80,
    bank_ot: 0x28eb6d0,
    bank_body: 0x28eb780,
    sys_text: 0,
    sys_len: 0,
    sys_var_ot: 0x30b1ae0,
    sys_var_text: 0x30b1ae8,
    pal: Pal::CtxI16(0xa),
};

#[no_mangle]
pub unsafe extern "C" fn rz4_init(b: usize) { vwf::init(&G, b) }

/// 원래 0x474b10 대체(일본판): (x, y, 글, 수) → 남은 수
#[no_mangle]
pub unsafe extern "C" fn rz4_render(x: u32, y: u32, text: *const u8, count: u32) -> u32 {
    let (ctx, sel) = vwf::ctx(&G);
    let dst = rd::<usize>(ctx) + (((y & 0xff) as usize) * 32 + (x & 0xff) as usize) * 2;
    vwf::render(&G, ctx, sel, dst, text as usize, count)
}
