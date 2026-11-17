"""RZ1~4 한글: GBA 빌드 산출물 → 모듈 데이터 → Rust 모듈 → main IPS + subsdk9 (build/exefs).
  python tools/build_rz1.py [--gba] [--deploy]   (--gba: GBA 빌드부터, --deploy: Eden 모드 폴더로 복사)"""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mainpatch
ROOT = mainpatch.ROOT
GBA_DIR = r'D:\Games\Kor Patch\CLude\Rockman Zero'
def run(*a, **k):
    subprocess.check_call(list(a), **k)
if '--gba' in sys.argv:
    run(sys.executable, os.path.join(GBA_DIR, 'rz1', 'build.py'), '--out', os.path.join(ROOT, '_work', 'rz1_kr.gba'), cwd=GBA_DIR)
run(sys.executable, os.path.join(ROOT, 'tools', 'rz1_data.py'))
run(sys.executable, os.path.join(ROOT, 'tools', 'rz2_data.py'))
run(sys.executable, os.path.join(ROOT, 'tools', 'rz3_data.py'))
run(sys.executable, os.path.join(ROOT, 'tools', 'rz4_data.py'))
run(sys.executable, os.path.join(ROOT, 'tools', 'zx_build.py'))   # ZX 대사·글꼴·그림 → build/romfs, kohook/data/zx.bin
run(sys.executable, os.path.join(ROOT, 'tools', 'zxa_coll_ko.py'))   # 컬렉션 전용 ZXA 원문 번역
run(sys.executable, os.path.join(ROOT, 'tools', 'zxa_build.py'))   # ZXA 대사·글꼴·그림 → build/romfs, kohook/data/zxa.bin
run('sh', os.path.join(ROOT, 'tools', 'build_kohook.sh'))
out = os.path.join(ROOT, 'build', 'exefs')
HOOKS = [(0x470500, 0, 'ffc301d1fc6f01a9fa6702a9f85f03a9'),   # RZ1 대사→타일맵
         (0x46ff94, 1, 'a81e019008793391280100f904000014'),   # RZ1 글자 시스템 초기화 끝
         (0x396330, 2, 'e10f0032087d0453e2071f32205968f8'),   # RZ1 결과 상태(성공/실패)
         (0x396468, 3, 'da6a0394285501d0081145f909d58252'),   # RZ1 결과 칭호 출력 호출
         (0x470364, 4, '604e01b000a047f9fd7b42a9e2031532'),   # RZ1 8px 글꼴 로더 (결과 화면)
         (0x471930, 5, 'ff0302d1fc6f02a9fa6703a9f85f04a9'),   # RZ2 대사→타일맵
         (0x471364, 6, '881e01d008813391280100f904000014'),   # RZ2 글자 시스템 초기화 끝
         (0x471edc, 7, '5fff0771e8010054c802403949671a53'),   # RZ2 업로드 노드 분기 (문맥 B)
         (0x4721a4, 8, '5fff0771e8010054c802403949671a53'),   # RZ2 업로드 노드 분기 (문맥 A)
         (0x4723f0, 9, 'f657bda9f44f01a9fd7b02a9fd830091'),   # RZ2 글자 세기
         (0x472730, 10, '41020034080040391ff10371e8010054'),  # RZ2 글자 건너뛰기
         (0x472550, 11, 'fa67bba9f85f01a9f65702a9f44f03a9'),  # RZ2 줄 단위 대기열 (오프닝 스크롤)
         (0x473000, 12, 'ff8302d1fc6f04a9fa6705a9f85f06a9'),  # RZ3 대사→타일맵 (x, y, 글, 수)
         (0x4729e4, 13, '8a1e01b04a8933910a0100f9c8c3a252'),  # RZ3 글자 시스템 초기화 끝
         (0x473788, 14, '3fff077108020054c80240f929671a53'),  # RZ3 업로드 노드 분기 (문맥 B)
         (0x4739ac, 15, '3fff077108020054c80240f929671a53'),  # RZ3 업로드 노드 분기 (문맥 A)
         (0x474b10, 16, 'ffc302d1fc6f05a9fa6706a9f85f07a9'),  # RZ4 대사→타일맵 (x, y, 글, 수)
         (0x4744b0, 17, 'df010039090100390200001400000000'),  # RZ4 글자 시스템 초기화 끝 (b 0x4744c0 포함)
         (0x475228, 18, '3fff077108020054c80240f929671a53'),  # RZ4 업로드 노드 분기
         (0x47544c, 19, '3fff077108020054c80240f929671a53'),  # RZ4 업로드 노드 분기
         (0x12ab270, 20, 'ca324039a8c3da38f72b00b95f210071'),  # ZX 출력기 A 글리프 공통 지점
         (0x14fce30, 21, 'ca324039a8c3da38f72b00b95f210071'),  # ZX 출력기 B
         (0x12abc50, 22, '01030034080040391ff10371a8020054'),  # ZX 건너뛰기 A
         (0x14fd810, 23, '01030034080040391ff10371a8020054'),  # ZX 건너뛰기 B
         (0x12ab7f0, 24, 'f50f1df8f44f01a9fd7b02a9fd830091'),  # ZX 글자 수 A
         (0x14fd3b0, 25, 'f50f1df8f44f01a9fd7b02a9fd830091'),  # ZX 글자 수 B
         (0xd7ccbc, 26, 'ea4740b9f92b00f9f75b00b90b0601f0'),   # ZXA 출력기 A 글리프 공통 지점
         (0x102645c, 27, 'ea4740b9f92b00f9f75b00b9cbf000d0'),  # ZXA 출력기 B
         (0xd7d6b0, 28, '61030034080040391ff1037108030054'),   # ZXA 건너뛰기 A
         (0x1026e50, 29, '61030034080040391ff1037108030054'),  # ZXA 건너뛰기 B
         (0xd7d0d0, 30, 'f50f1df8f44f01a9fd7b02a9fd830091'),   # ZXA 글자 수 A
         (0x1026870, 31, 'f50f1df8f44f01a9fd7b02a9fd830091')]  # ZXA 글자 수 B
# ZX FA(이름 삽입) 진행: 글자 수×폭 대신 안쪽 출력기가 남긴 커서 [ctx+0x30] 를 쓴다(가변폭). mov w23,w0 / ldrh w19,[x22,#0x30] / nop / nop
FA_OLD = bytes.fromhex('e83e0012f703002a0821204b134d1b1b')
FA_NEW = bytes.fromhex('f703002ad36240791f2003d51f2003d5')
RAW = {0x12ab6f4: (FA_OLD, FA_NEW), 0x14fd2b4: (FA_OLD, FA_NEW)}
# ZXA FA 진행: madd w26,w8,w28,w26 → mov w23,w0 / ldrh w26,[x22,#0x30] / nop / nop
FAA_OLD = bytes.fromhex('e83e0012f703002a0821204b1a691c1b')
FAA_NEW = bytes.fromhex('f703002ada6240791f2003d51f2003d5')
RAW[0xd7d000] = (FAA_OLD, FAA_NEW)
RAW[0x10267a0] = (FAA_OLD, FAA_NEW)
import json
for a, o, n in json.load(open(os.path.join(ROOT, 'build', 'zx_raw.json'))) + json.load(open(os.path.join(ROOT, 'build', 'zxa_raw.json'))):   # ZX·ZXA 화자 이름표
    RAW[a] = (bytes.fromhex(o), bytes.fromhex(n))
recs = mainpatch.build([(a, i) for a, i, _ in HOOKS], {a: bytes.fromhex(h) for a, _, h in HOOKS}, out, RAW)
run(sys.executable, os.path.join(ROOT, 'tools', 'elf2nso.py'), os.path.join(ROOT, 'kohook', 'kohook.elf'), os.path.join(out, 'subsdk9'))
print('IPS records', recs)
run(sys.executable, '-I', os.path.join(ROOT, 'tools', 'rz1_gfx.py'))   # 그림 글자 → build/romfs
run(sys.executable, '-I', os.path.join(ROOT, 'tools', 'rz2_gfx.py'))
run(sys.executable, '-I', os.path.join(ROOT, 'tools', 'rz3_gfx.py'))
run(sys.executable, '-I', os.path.join(ROOT, 'tools', 'rz4_gfx.py'))
run(sys.executable, '-I', os.path.join(ROOT, 'tools', 'launcher_build.py'))   # 런처 GMD·글꼴 → build/romfs/.../romNX
if '--deploy' in sys.argv:   # Eden 모드 폴더에 복사
    import shutil
    mod = r'D:\Games\Kor Patch\CLude\eden emul\user\load\010025C00D410000\KoreanPatch'
    for sub in ('exefs', 'romfs'):
        shutil.copytree(os.path.join(ROOT, 'build', sub), os.path.join(mod, sub), dirs_exist_ok=True)
    print('deployed ->', mod)
