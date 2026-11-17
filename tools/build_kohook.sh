#!/bin/sh
# Rust 훅 모듈 → kohook.elf → build/exefs/subsdk9
set -e
cd "$(dirname "$0")/../kohook"
cargo build --release 2>&1 | grep -E "^(error|warning: unused)|-->|Finished" || true
LLD=$(ls ~/.rustup/toolchains/*/lib/rustlib/x86_64-pc-windows-msvc/bin/rust-lld.exe | head -1)
"$LLD" -flavor gnu -shared -T link.ld --whole-archive target/aarch64-unknown-none/release/libkohook.a --no-whole-archive \
  -z text --hash-style=sysv --gc-sections --export-dynamic -soname kohook -o kohook.elf
