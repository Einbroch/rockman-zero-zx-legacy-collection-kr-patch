/* subsdk NSO 용 레이아웃: text / ro / data 각각 0x1000 정렬, bss 맨 앞에 모듈 런타임 */
PHDRS { text PT_LOAD FLAGS(5); ro PT_LOAD FLAGS(4); data PT_LOAD FLAGS(6); dyn PT_DYNAMIC FLAGS(6); }
SECTIONS {
  . = 0;
  __text_start = .;
  .text : { KEEP(*(.text.start)) *(.text .text.*) } :text
  . = ALIGN(0x1000);
  __ro_start = .;
  .rodata : { KEEP(*(.rodata.mod0)) *(.rodata .rodata.*) } :ro
  .dynsym : { *(.dynsym) } :ro
  .dynstr : { *(.dynstr) } :ro
  .hash : { *(.hash) } :ro
  .gnu.hash : { *(.gnu.hash) } :ro
  .rela.dyn : { *(.rela.dyn) *(.rela.plt) } :ro
  . = ALIGN(0x1000);
  __data_start = .;
  .dynamic : { *(.dynamic) } :data :dyn
  .got : { *(.got) *(.got.plt) } :data
  .data : { *(.data .data.*) } :data
  . = ALIGN(8);
  HIDDEN(__bss_start = .);
  .bss (NOLOAD) : { KEEP(*(.bss.modrt)) *(.bss .bss.*) *(COMMON) } :data
  . = ALIGN(8);
  HIDDEN(__bss_end = .);
  /DISCARD/ : { *(.eh_frame*) *(.comment) *(.note*) *(.ARM.*) }
}
