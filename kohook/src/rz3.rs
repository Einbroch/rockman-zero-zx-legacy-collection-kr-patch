//! 록맨 제로 3 — 공용 가변폭 출력기(vwf.rs) 설정.
//! 출력기 0x473000 은 (x, y, 글, 수): 타일맵 = [문맥 +0] + (y*32 + x)*2. 시스템 표는 초기화(0x472940)가 변수
//! 0x30acc80(오프셋표)·0x30acc88(본문)에 넣어 두고 쓰므로 일본판이면 그 변수를 내 표로 바꾼다(GBA 와 같은 표 구조:
//! 번역 칸은 한글 구간, 나머지는 원문 사본을 원래 인코딩으로).
use crate::rd;
use crate::vwf::{self, Game, Pal};

static G: Game = Game {
    data: include_bytes!("../data/rz3.bin"),
    ctx_a: 0x30af8b0, // GOT ff8
    ctx_b: 0x30aeef8, // GOT f90
    sel0: 2,
    lists: 0x980,
    bank_ot: 0x28eb2d0,
    bank_body: 0x28eb370,
    sys_text: 0,
    sys_len: 0,
    sys_var_ot: 0x30acc80,
    sys_var_text: 0x30acc88,
    pal: Pal::CtxI16(0xa),
};

#[no_mangle]
pub unsafe extern "C" fn rz3_init(b: usize) { vwf::init(&G, b) }

/// 원래 0x473000 대체(일본판): (x, y, 글, 수) → 남은 수
#[no_mangle]
pub unsafe extern "C" fn rz3_render(x: u32, y: u32, text: *const u8, count: u32) -> u32 {
    let (ctx, sel) = vwf::ctx(&G);
    let dst = rd::<usize>(ctx) + (((y & 0xff) as usize) * 32 + (x & 0xff) as usize) * 2;
    vwf::render(&G, ctx, sel, dst, text as usize, count)
}
