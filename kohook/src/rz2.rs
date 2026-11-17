//! 록맨 제로 2 — 공용 가변폭 출력기(vwf.rs) 설정.
//! 시스템 문자열은 main 본문을 GOT 로 직접 읽으므로(110곳), 출력기·글자 세기·건너뛰기·줄 대기열 입구에서 포인터를 번역문으로 바꾼다.
use crate::vwf::{self, Game, Pal};

static G: Game = Game {
    data: include_bytes!("../data/rz2.bin"),
    ctx_a: 0x30ae548, // GOT f50
    ctx_b: 0x30adb98, // GOT f58
    sel0: 0,
    lists: 0x980,
    bank_ot: 0x28eb0b0,
    bank_body: 0x28eb010,
    sys_text: 0x282d3c8,
    sys_len: 0x2458,
    sys_var_ot: 0,
    sys_var_text: 0,
    pal: Pal::Fixed(2),
};

#[no_mangle]
pub unsafe extern "C" fn rz2_init(b: usize) { vwf::init(&G, b) }

#[no_mangle]
pub unsafe extern "C" fn rz2_xlate(p: usize) -> usize { vwf::xlate(&G, p) }

/// 원래 0x471930 대체(일본판): dst = 타일맵, text = 글, count = 글자 수 → 남은 수
#[no_mangle]
pub unsafe extern "C" fn rz2_render(dst: *mut u16, text: *const u8, count: u32) -> u32 {
    let (ctx, sel) = vwf::ctx(&G);
    vwf::render(&G, ctx, sel, dst as usize, text as usize, count)
}
