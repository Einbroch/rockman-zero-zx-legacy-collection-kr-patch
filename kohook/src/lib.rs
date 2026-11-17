//! 록맨 제로&ZX 레거시 컬렉션 한글 훅 모듈 (subsdk9).
//! main 의 가져오기 `_ZN2nn3ldn15MakeIpv4AddressEhhhh` 이름을 `kohook_dispatch_0000000000000000` 로 바꿔 이 모듈로 잇는다.
//! 훅 지점: `mov x15,x30 ; movz x14,#id ; movk x14,#0x4b4f,lsl#48 ; bl <PLT>` — x14 위 16비트가 0x4b4f 면 훅,
//! 아니면 진짜 MakeIpv4Address 로 그대로 넘긴다(x16/x17 만 씀).
#![no_std]
use core::arch::global_asm;
use core::ptr::{read_volatile, write_volatile};

mod rz1;
mod rz2;
mod rz3;
mod rz4;
mod vwf;
mod zx;

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}

/// main 모듈 시작 주소 (훅이 들어올 때마다 갱신)
#[no_mangle]
pub static mut MAIN_BASE: usize = 0;

#[inline(always)]
pub(crate) fn base() -> usize {
    unsafe { read_volatile(&raw const MAIN_BASE) }
}
#[inline(always)]
pub(crate) unsafe fn rd<T: Copy>(a: usize) -> T {
    read_volatile(a as *const T)
}
#[inline(always)]
pub(crate) unsafe fn wr<T>(a: usize, v: T) {
    write_volatile(a as *mut T, v)
}

global_asm!(r#"
.section .text.start,"ax"
.global __module_start
.hidden __module_start
__module_start:
    .word 0
    .word __nx_mod0 - __module_start

.section .rodata.mod0,"a"
.balign 4
__nx_mod0:
    .ascii "MOD0"
    .word _DYNAMIC - __nx_mod0
    .word __bss_start - __nx_mod0
    .word __bss_end - __nx_mod0
    .word 0
    .word 0
    .word __module_runtime - __nx_mod0

.section .bss.modrt,"aw",%nobits
.balign 8
__module_runtime:
    .space 0x200

.hidden MAIN_BASE
.hidden rz1_render
.hidden rz1_init
.hidden RZ1_RESULT
.hidden RZ1_RESULT_LEN
.hidden rz2_render
.hidden rz2_init
.hidden rz2_xlate
.hidden zc_upload
.hidden rz3_render
.hidden rz3_init
.hidden rz4_render
.hidden rz4_init
.hidden zx_glyph
.hidden zx_skip
.hidden zx_count
.section .text,"ax"
.global kohook_dispatch_0000000000000000
.type kohook_dispatch_0000000000000000,%function
kohook_dispatch_0000000000000000:
    lsr x16, x14, #48
    movz x17, #0x4b4f
    cmp x16, x17
    b.ne 1f
    and x16, x14, #0xffff
    adr x17, hook_table
    ldrsw x16, [x17, x16, lsl #2]
    add x17, x17, x16
    br x17
1:
    adrp x16, :got:_ZN2nn3ldn15MakeIpv4AddressEhhhh
    ldr x16, [x16, :got_lo12:_ZN2nn3ldn15MakeIpv4AddressEhhhh]
    br x16

.balign 4
hook_table:
    .word hook_rz1_render - hook_table
    .word hook_rz1_init - hook_table
    .word hook_rz1_status - hook_table
    .word hook_rz1_title - hook_table
    .word hook_rz1_font8 - hook_table
    .word hook_rz2_render - hook_table
    .word hook_rz2_init - hook_table
    .word hook_rz2_up1 - hook_table
    .word hook_rz2_up2 - hook_table
    .word hook_rz2_count - hook_table
    .word hook_rz2_skip - hook_table
    .word hook_rz2_lines - hook_table
    .word hook_rz3_render - hook_table
    .word hook_rz3_init - hook_table
    .word hook_rz3_up1 - hook_table
    .word hook_rz3_up2 - hook_table
    .word hook_rz4_render - hook_table
    .word hook_rz4_init - hook_table
    .word hook_rz4_up1 - hook_table
    .word hook_rz4_up2 - hook_table
    .word hook_zx_render_a - hook_table
    .word hook_zx_render_b - hook_table
    .word hook_zx_skip_a - hook_table
    .word hook_zx_skip_b - hook_table
    .word hook_zx_count_a - hook_table
    .word hook_zx_count_b - hook_table
    .word hook_zxa_render_a - hook_table
    .word hook_zxa_render_b - hook_table
    .word hook_zxa_skip_a - hook_table
    .word hook_zxa_skip_b - hook_table
    .word hook_zxa_count_a - hook_table
    .word hook_zxa_count_b - hook_table

/* x16 = main 기준 = x30 - (지점+16). MAIN_BASE 에 저장. 인수: 지점+16 상수를 x17 에 */
.macro SETBASE site_ret
    movz x17, #(\site_ret & 0xffff)
    movk x17, #((\site_ret >> 16) & 0xffff), lsl #16
    sub x16, x30, x17
    adrp x17, MAIN_BASE
    str x16, [x17, :lo12:MAIN_BASE]
.endm

/* RZ1 0x470500 대사→타일맵. 일본판(0x30c7c00 == 0)이면 한글 출력기로 통째 대체, 아니면 원래 함수 계속 */
hook_rz1_render:
    SETBASE 0x470510
    movz x17, #0x7c00
    movk x17, #0x30c, lsl #16
    ldrb w17, [x16, x17]
    cbnz w17, 2f
    mov x30, x15
    b rz1_render
2:
    mov x17, x30
    mov x30, x15
    sub sp, sp, #0x70
    stp x28, x27, [sp, #0x10]
    stp x26, x25, [sp, #0x20]
    stp x24, x23, [sp, #0x30]
    br x17

/* RZ1 0x46ff94 (글자 시스템 초기화 끝): 밀어낸 adrp/add/str 재현 → rz1_init → 0x46ffb0 으로 */
hook_rz1_init:
    SETBASE 0x46ffa4
    movz x17, #0x3cde
    movk x17, #0x284, lsl #16
    add x8, x16, x17
    str x8, [x9]
    stp x0, x1, [sp, #-0x60]!
    stp x2, x3, [sp, #0x10]
    stp x4, x5, [sp, #0x20]
    stp x6, x7, [sp, #0x30]
    stp x8, x9, [sp, #0x40]
    stp x15, x16, [sp, #0x50]
    mov x0, x16
    bl rz1_init
    ldp x2, x3, [sp, #0x10]
    ldp x4, x5, [sp, #0x20]
    ldp x6, x7, [sp, #0x30]
    ldp x8, x9, [sp, #0x40]
    ldp x15, x16, [sp, #0x50]
    ldp x0, x1, [sp], #0x60
    mov x30, x15
    movz x17, #0xffb0
    movk x17, #0x46, lsl #16
    add x17, x16, x17
    br x17

/* x17 = x16 + 상수 */
.macro MADDR off
    movz x17, #(\off & 0xffff)
    movk x17, #((\off >> 16) & 0xffff), lsl #16
    add x17, x16, x17
.endm

/* RZ1 결과 화면 상태(성공/실패) 0x396330: 밀어낸 mov w1,#0xf / lsr w8,w8,#4 / mov w2,#6 / ldr x0,[x9,w8,uxtw#3].
   일본판이면 한글 두 칸(실패=BC AF, 성공=BE B2; 8px 글꼴 칸)을 x=0x10 에 */
hook_rz1_status:
    SETBASE 0x396340
    lsr w8, w8, #4
    mov w2, #6
    ldr x0, [x9, w8, uxtw #3]
    mov w1, #0xf
    MADDR 0x30c7c00
    ldrb w17, [x17]
    cbnz w17, 1f
    cmp w8, #1
    b.hi 1f
    mov w1, #0x10
    adr x0, rz1_status_str
    add x0, x0, x8, lsl #2
1:
    mov x17, x30
    mov x30, x15
    br x17

.balign 4
rz1_status_str:
    .byte 0xbc, 0xaf, 0, 0, 0xbe, 0xb2, 0, 0

/* RZ1 결과 화면 칭호 0x396468: 밀어낸 bl 0x470fd0 / adrp+ldr x8,[GOT 0x2e3ca20] / mov w9,#0x16a8.
   글이 내 칭호 문자열이면 대기열(0x470ea0, 한글 출력기가 그림), 아니면 원래 고정폭 출력(0x470fd0) */
hook_rz1_title:
    SETBASE 0x396478
    stp x15, x16, [sp, #-16]!
    adrp x17, RZ1_RESULT
    add x17, x17, :lo12:RZ1_RESULT
    sub x17, x0, x17
    adrp x14, RZ1_RESULT_LEN
    ldr x14, [x14, :lo12:RZ1_RESULT_LEN]
    cmp x17, x14
    b.hs 1f
    MADDR 0x470ea0
    b 2f
1:
    MADDR 0x470fd0
2:
    blr x17
    ldp x15, x16, [sp], #16
    MADDR 0x2e3ca20
    ldr x8, [x17]
    mov w9, #0x16a8
    MADDR 0x396478
    mov x30, x15
    br x17

/* RZ1 8px 글꼴 로더 0x470364: 밀어낸 adrp+ldr x0,[GOT 0x2e3df40] / ldp x29,x30,[sp,#0x20] / mov w2,#0x800.
   일본판이고 결과 화면(복귀 0x395afc)에서 불렸으면 한글 칸을 넣은 글꼴로 */
hook_rz1_font8:
    SETBASE 0x470374
    MADDR 0x2e3df40
    ldr x0, [x17]
    ldp x29, x30, [sp, #0x20]
    mov w2, #0x800
    MADDR 0x30c7c00
    ldrb w17, [x17]
    cbnz w17, 1f
    MADDR 0x395afc
    cmp x30, x17
    b.ne 1f
    adrp x0, RZ1_RESULT
    add x0, x0, :lo12:RZ1_RESULT
1:
    MADDR 0x470374
    br x17
/* x17 = 일본판이면 0 (언어 바이트) — x16 = main 기준 */
.macro LANG
    movz x17, #0x7c00
    movk x17, #0x30c, lsl #16
    ldrb w17, [x16, x17]
.endm

/* RZ2 0x471930 대사→타일맵. 일본판이면 rz2_render 로 통째 대체, 아니면 밀어낸 4명령 재현 후 0x471940 */
hook_rz2_render:
    SETBASE 0x471940
    LANG
    cbnz w17, 1f
    mov x30, x15
    b rz2_render
1:
    mov x30, x15
    sub sp, sp, #0x80
    stp x28, x27, [sp, #0x20]
    stp x26, x25, [sp, #0x30]
    stp x24, x23, [sp, #0x40]
    MADDR 0x471940
    br x17

/* RZ2 0x471364 (글자 시스템 초기화 끝): 밀어낸 adrp/add/str 재현 → rz2_init → b 0x471380 */
hook_rz2_init:
    SETBASE 0x471374
    MADDR 0x2843ce0
    mov x8, x17
    str x8, [x9]
    stp x0, x1, [sp, #-0x60]!
    stp x2, x3, [sp, #0x10]
    stp x4, x5, [sp, #0x20]
    stp x6, x7, [sp, #0x30]
    stp x8, x9, [sp, #0x40]
    stp x15, x16, [sp, #0x50]
    mov x0, x16
    bl rz2_init
    ldp x2, x3, [sp, #0x10]
    ldp x4, x5, [sp, #0x20]
    ldp x6, x7, [sp, #0x30]
    ldp x8, x9, [sp, #0x40]
    ldp x15, x16, [sp, #0x50]
    ldp x0, x1, [sp], #0x60
    mov x30, x15
    MADDR 0x471380
    br x17

/* 2·3편 업로드 노드 분기: x21 노드, x19 VRAM 타일 기준, \code 코드.
   일본판이고 내 노드(코드 위 4비트 0xE)면 zc_upload 후 다음 노드로,
   아니면 cmp code,#0x1ff / b.hi / \ld / lsl w9,code,#6 재현.
   2편 0x471edc/0x4721a4 (w26, ldrb w8,[x22]), 3편 0x473788/0x4739ac (w25, ldr x8,[x22]) */
.macro ZC_UP site, hi_target, next, code, ld
    SETBASE (\site + 16)
    LANG
    cbnz w17, 1f
    lsr w17, \code, #12
    cmp w17, #0xe
    b.ne 1f
    stp x15, x16, [sp, #-16]!
    mov x0, x21
    mov x1, x19
    bl zc_upload
    ldp x15, x16, [sp], #16
    mov x30, x15
    MADDR \next
    br x17
1:
    mov x30, x15
    cmp \code, #0x1ff
    b.hi 2f
    \ld
    lsl w9, \code, #6
    MADDR (\site + 16)
    br x17
2:
    MADDR \hi_target
    br x17
.endm
hook_rz2_up1:
    ZC_UP 0x471edc, 0x471f1c, 0x472008, w26, "ldrb w8, [x22]"
hook_rz2_up2:
    ZC_UP 0x4721a4, 0x4721e4, 0x4722d0, w26, "ldrb w8, [x22]"
hook_rz3_up1:
    ZC_UP 0x473788, 0x4737cc, 0x4738b0, w25, "ldr x8, [x22]"
hook_rz3_up2:
    ZC_UP 0x4739ac, 0x4739f0, 0x473ad4, w25, "ldr x8, [x22]"
hook_rz4_up1:
    ZC_UP 0x475228, 0x47526c, 0x475350, w25, "ldr x8, [x22]"
hook_rz4_up2:
    ZC_UP 0x47544c, 0x475490, 0x475574, w25, "ldr x8, [x22]"

/* RZ4 0x474b10 출력기 (x, y, 글, 수). 일본판이면 rz4_render 로 통째 대체, 아니면 밀어낸 4명령 재현 후 0x474b20 */
hook_rz4_render:
    SETBASE 0x474b20
    LANG
    cbnz w17, 1f
    mov x30, x15
    b rz4_render
1:
    mov x30, x15
    sub sp, sp, #0xb0
    stp x28, x27, [sp, #0x50]
    stp x26, x25, [sp, #0x60]
    stp x24, x23, [sp, #0x70]
    MADDR 0x474b20
    br x17

/* RZ4 0x4744b0 (글자 시스템 초기화 끝): strb wzr,[x14] / strb w9,[x8] 재현 → rz4_init → b 0x4744c0 (원래 다음 명령) */
hook_rz4_init:
    SETBASE 0x4744c0
    strb wzr, [x14]
    strb w9, [x8]
    stp x0, x1, [sp, #-0x60]!
    stp x2, x3, [sp, #0x10]
    stp x4, x5, [sp, #0x20]
    stp x6, x7, [sp, #0x30]
    stp x8, x9, [sp, #0x40]
    stp x15, x16, [sp, #0x50]
    mov x0, x16
    bl rz4_init
    ldp x2, x3, [sp, #0x10]
    ldp x4, x5, [sp, #0x20]
    ldp x6, x7, [sp, #0x30]
    ldp x8, x9, [sp, #0x40]
    ldp x15, x16, [sp, #0x50]
    ldp x0, x1, [sp], #0x60
    mov x30, x15
    MADDR 0x4744c0
    br x17

/* RZ3 0x473000 출력기 (x, y, 글, 수). 일본판이면 rz3_render 로 통째 대체, 아니면 밀어낸 4명령 재현 후 0x473010 */
hook_rz3_render:
    SETBASE 0x473010
    LANG
    cbnz w17, 1f
    mov x30, x15
    b rz3_render
1:
    mov x30, x15
    sub sp, sp, #0xa0
    stp x28, x27, [sp, #0x40]
    stp x26, x25, [sp, #0x50]
    stp x24, x23, [sp, #0x60]
    MADDR 0x473010
    br x17

/* RZ3 0x4729e4 (글자 시스템 초기화 끝): adrp/add x10 = 0x2843ce2 / str x10,[x8] 재현 → rz3_init →
   mov w8,#0x161e0000 재현 후 0x4729f4 (다음 명령이 x9·w8 을 씀) */
hook_rz3_init:
    SETBASE 0x4729f4
    MADDR 0x2843ce2
    mov x10, x17
    str x10, [x8]
    stp x0, x1, [sp, #-0x60]!
    stp x2, x3, [sp, #0x10]
    stp x4, x5, [sp, #0x20]
    stp x6, x7, [sp, #0x30]
    stp x9, x10, [sp, #0x40]
    stp x15, x16, [sp, #0x50]
    mov x0, x16
    bl rz3_init
    ldp x2, x3, [sp, #0x10]
    ldp x4, x5, [sp, #0x20]
    ldp x6, x7, [sp, #0x30]
    ldp x9, x10, [sp, #0x40]
    ldp x15, x16, [sp, #0x50]
    ldp x0, x1, [sp], #0x60
    mov w8, #0x161e0000
    mov x30, x15
    MADDR 0x4729f4
    br x17

/* RZ2 0x4723f0 글자 세기 입구: x0 = rz2_xlate(x0), 밀어낸 프롤로그 재현 → 0x472400 */
hook_rz2_count:
    SETBASE 0x472400
    stp x15, x16, [sp, #-16]!
    bl rz2_xlate
    ldp x15, x16, [sp], #16
    mov x30, x15
    stp x22, x21, [sp, #-0x30]!
    stp x20, x19, [sp, #0x10]
    stp x29, x30, [sp, #0x20]
    add x29, sp, #0x20
    MADDR 0x472400
    br x17

/* RZ2 0x472730 글자 건너뛰기 입구 (x0 글, w1 수 → x0): x0 = rz2_xlate(x0),
   cbz w1,끝 / ldrb w8,[x0] / cmp w8,#0xfc / b.hi 끝 재현 → 0x472740 */
hook_rz2_skip:
    SETBASE 0x472740
    stp x15, x16, [sp, #-32]!
    str x1, [sp, #16]
    bl rz2_xlate
    ldr x1, [sp, #16]
    ldp x15, x16, [sp], #32
    mov x30, x15
    cbz w1, 1f
    ldrb w8, [x0]
    cmp w8, #0xfc
    b.hi 1f
    MADDR 0x472740
    br x17
1:
    ret

/* RZ2 0x472550 줄 단위 대기열(x0 글, w1 x, w2 y, w3 시작 줄, w4 끝 줄 — 오프닝 스크롤): x0 = rz2_xlate(x0),
   밀어낸 프롤로그(stp 4개) 재현 → 0x472560 */
hook_rz2_lines:
    SETBASE 0x472560
    stp x15, x16, [sp, #-48]!
    stp x1, x2, [sp, #16]
    stp x3, x4, [sp, #32]
    bl rz2_xlate
    ldp x1, x2, [sp, #16]
    ldp x3, x4, [sp, #32]
    ldp x15, x16, [sp], #48
    mov x30, x15
    stp x26, x25, [sp, #-0x50]!
    stp x24, x23, [sp, #0x10]
    stp x22, x21, [sp, #0x20]
    stp x20, x19, [sp, #0x30]
    MADDR 0x472560
    br x17
/* ZX 출력기 공통 지점(엔진 A 0x12ab270 / B 0x14fce30): w9 = 글리프 번호, x25 = 글자 마지막 바이트, w27 = 글자 폭.
   zx_glyph(전역, w9, x25) → w9 = 새 글리프, x25 += 더 읽은 바이트, 폭이 0 이 아니면 w27 = 폭, [sp+0x50] = 2(행 바이트).
   그 뒤 밀어낸 ldrb w10,[x22,#0xc] / ldursb w8,[x29,#-0x54] / str w23,[sp,#0x28] / cmp w10,#8 재현(플래그를 마지막에). */
.macro ZX_R site, got
    SETBASE (\site + 16)
    sub sp, sp, #0x80
    stp x0, x1, [sp]
    stp x2, x3, [sp, #0x10]
    stp x4, x5, [sp, #0x20]
    stp x6, x7, [sp, #0x30]
    stp x10, x11, [sp, #0x40]
    stp x12, x13, [sp, #0x50]
    stp x15, x16, [sp, #0x60]
    str x8, [sp, #0x70]
    MADDR \got
    ldr x0, [x17]
    mov w1, w9
    mov x2, x25
    mov w3, #0
    bl zx_glyph
    mov x14, x0
    ldp x2, x3, [sp, #0x10]
    ldp x4, x5, [sp, #0x20]
    ldp x6, x7, [sp, #0x30]
    ldp x10, x11, [sp, #0x40]
    ldp x12, x13, [sp, #0x50]
    ldp x15, x16, [sp, #0x60]
    ldr x8, [sp, #0x70]
    ldp x0, x1, [sp], #0x80
    and w9, w14, #0xffff
    ubfx x17, x14, #16, #8
    add x25, x25, x17
    ubfx x17, x14, #24, #8
    cbz w17, 1f
    mov w27, w17
    mov w17, #2
    str w17, [sp, #0x50]
1:
    ldrb w10, [x22, #0xc]
    ldursb w8, [x29, #-0x54]
    str w23, [sp, #0x28]
    cmp w10, #8
    mov x30, x15
    MADDR (\site + 16)
    br x17
.endm
hook_zx_render_a:
    ZX_R 0x12ab270, 0x2e41190
hook_zx_render_b:
    ZX_R 0x14fce30, 0x2e41900

/* ZX·ZXA 건너뛰기(x0 글, w1 수 → x0)·글자 수(x0 글 → w0) 통째 대체: fn(전역, 글, 수, 게임 번호).
   ZX 0x12abc50 / 0x14fd810 · 0x12ab7f0 / 0x14fd3b0, ZXA 0xd7d6b0 / 0x1026e50 · 0xd7d0d0 / 0x1026870 */
.macro ZX_S site, got, fn, gid=0
    SETBASE (\site + 16)
    stp x15, x16, [sp, #-16]!
    mov x2, x1
    mov x1, x0
    mov w3, #\gid
    MADDR \got
    ldr x0, [x17]
    bl \fn
    ldp x15, x16, [sp], #16
    mov x30, x15
    ret
.endm
hook_zx_skip_a:
    ZX_S 0x12abc50, 0x2e41190, zx_skip
hook_zx_skip_b:
    ZX_S 0x14fd810, 0x2e41900, zx_skip
hook_zx_count_a:
    ZX_S 0x12ab7f0, 0x2e41190, zx_count
hook_zx_count_b:
    ZX_S 0x14fd3b0, 0x2e41900, zx_count

/* ZXA 출력기 공통 지점(엔진 A 0xd7ccbc / B 0x102645c): w19 = 글리프 번호, x25 = 글자 마지막 바이트, w28 = 글자 폭,
   [sp+0x5c] = 행 바이트. 밀어낸 ldr w10,[sp,#0x44] / str x25,[sp,#0x50] / str w23,[sp,#0x58] / adrp x11,\page 재현. */
.macro ZXA_R site, got, page
    SETBASE (\site + 16)
    sub sp, sp, #0x80
    stp x0, x1, [sp]
    stp x2, x3, [sp, #0x10]
    stp x4, x5, [sp, #0x20]
    stp x6, x7, [sp, #0x30]
    stp x8, x9, [sp, #0x40]
    stp x12, x13, [sp, #0x50]
    stp x15, x16, [sp, #0x60]
    MADDR \got
    ldr x0, [x17]
    mov w1, w19
    mov x2, x25
    mov w3, #1
    bl zx_glyph
    mov x14, x0
    ldp x2, x3, [sp, #0x10]
    ldp x4, x5, [sp, #0x20]
    ldp x6, x7, [sp, #0x30]
    ldp x8, x9, [sp, #0x40]
    ldp x12, x13, [sp, #0x50]
    ldp x15, x16, [sp, #0x60]
    ldp x0, x1, [sp], #0x80
    and w19, w14, #0xffff
    ubfx x17, x14, #16, #8
    add x25, x25, x17
    ubfx x17, x14, #24, #8
    cbz w17, 1f
    mov w28, w17
    mov w17, #2
    str w17, [sp, #0x5c]
1:
    ldr w10, [sp, #0x44]
    str x25, [sp, #0x50]
    str w23, [sp, #0x58]
    MADDR \page
    mov x11, x17
    mov x30, x15
    MADDR (\site + 16)
    br x17
.endm
hook_zxa_render_a:
    ZXA_R 0xd7ccbc, 0x2e3ffe8, 0x2e3f000
hook_zxa_render_b:
    ZXA_R 0x102645c, 0x2e408f8, 0x2e40000
hook_zxa_skip_a:
    ZX_S 0xd7d6b0, 0x2e3ffe8, zx_skip, 1
hook_zxa_skip_b:
    ZX_S 0x1026e50, 0x2e408f8, zx_skip, 1
hook_zxa_count_a:
    ZX_S 0xd7d0d0, 0x2e3ffe8, zx_count, 1
hook_zxa_count_b:
    ZX_S 0x1026870, 0x2e408f8, zx_count, 1
"#);
