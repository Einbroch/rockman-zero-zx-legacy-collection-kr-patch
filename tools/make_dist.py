"""배포 zip 두 벌: Atmosphere(LayeredFS + exefs 덮어쓰기 + exefs_patches) / 에뮬레이터(모드 폴더).

    python tools/make_dist.py

입력: build/romfs/**, build/exefs/<빌드ID>.ips, build/exefs/subsdk9, dist_README.md, LICENSE-Galmuri.txt
출력: dist/MMZZXLC_KR_<버전>_atmosphere.zip, dist/MMZZXLC_KR_<버전>_emulator.zip, dist/SHA256SUMS.txt
게이트: romfs 파일이 전부 원본 RomFS(_work/romfs)에 같은 경로로 있을 것, IPS 가 하나이고 이름이 main 의 빌드 ID 일 것,
subsdk9 이 NSO 일 것.
"""
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'v0.9.5'
TID = '010025C00D410000'
NAME = 'MMZZXLC'
FIXED_TIME = (2026, 11, 17, 0, 0, 0)   # 같은 입력이면 같은 zip


def add(z, arc, src):
    info = zipfile.ZipInfo(arc, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, Path(src).read_bytes())


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    romfs = ROOT / 'build' / 'romfs'
    files = sorted(p for p in romfs.rglob('*') if p.is_file())
    src = ROOT / '_work' / 'romfs'
    bad = [p for p in files if not (src / p.relative_to(romfs)).is_file()]
    if bad:
        raise SystemExit(f'원본 RomFS 에 없는 경로: {bad[:5]}')
    exefs = ROOT / 'build' / 'exefs'
    ips = list(exefs.glob('*.ips'))
    if len(ips) != 1:
        raise SystemExit(f'IPS 가 하나가 아니다: {ips}')
    ips = ips[0]
    main_nso = (ROOT / '_work' / 'exefs_upd' / 'main').read_bytes()
    build_id = main_nso[0x40:0x60].hex().upper().rstrip('0')
    if not ips.stem.upper().startswith(build_id) or len(ips.stem) % 2:
        raise SystemExit(f'IPS 이름 {ips.stem} 이 main 빌드 ID {build_id} 와 다름')
    sub = exefs / 'subsdk9'
    if sub.read_bytes()[:4] != b'NSO0':
        raise SystemExit('subsdk9 이 NSO 가 아니다')
    readme = ROOT / 'dist_README.md'
    lic = ROOT / 'LICENSE-Galmuri.txt'
    out = ROOT / 'dist'
    out.mkdir(exist_ok=True)
    a = out / f'{NAME}_KR_{VERSION}_atmosphere.zip'
    e = out / f'{NAME}_KR_{VERSION}_emulator.zip'
    with zipfile.ZipFile(a, 'w') as z:
        for p in files:
            add(z, f'atmosphere/contents/{TID}/romfs/{p.relative_to(romfs).as_posix()}', p)
        add(z, f'atmosphere/contents/{TID}/exefs/subsdk9', sub)
        add(z, f'atmosphere/exefs_patches/{NAME}_KoreanPatch/{ips.name}', ips)
        add(z, 'README.md', readme)
        add(z, 'LICENSE-Galmuri.txt', lic)
    with zipfile.ZipFile(e, 'w') as z:
        for p in files:
            add(z, f'KoreanPatch/romfs/{p.relative_to(romfs).as_posix()}', p)
        add(z, 'KoreanPatch/exefs/subsdk9', sub)
        add(z, f'KoreanPatch/exefs/{ips.name}', ips)
        add(z, 'README.md', readme)
        add(z, 'LICENSE-Galmuri.txt', lic)
    sums = []
    for f in (a, e):
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        sums.append(f'{h}  {f.name}')
        print(f.name, f'{f.stat().st_size / 1e6:.1f} MB', h[:16])
    # LF 고정: 윈도 write_text 는 CRLF 로 써서 sha256sum -c 가 파일 이름 끝 \r 때문에 실패한다
    (out / 'SHA256SUMS.txt').write_bytes(('\n'.join(sums) + '\n').encode('utf-8'))
    print('romfs 파일', len(files), '/ IPS', ips.name, '/ subsdk9', sub.stat().st_size)


if __name__ == '__main__':
    main()
