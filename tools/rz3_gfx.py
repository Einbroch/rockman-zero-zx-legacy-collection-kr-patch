"""RZ3 그림 글자: GBA 3편 한글 롬(_work/rz3_kr.gba)이 다시 그린 타일셋·스프라이트를 컬렉션 RomFS ZC/DATA/*_z3.bin 에 옮긴다.
방식은 rz2_gfx.run 과 같다(레코드 = GBA 서술자, 타일 단위 차이 이식, 최단 분할 LZ 로 제자리 재압축).
레코드 위치는 컬렉션 묶음의 LZ 덩어리를 풀어 GBA 일본판 타일셋과 대조해 찾았다(_work/z3map.py).
스프라이트: obj_fnt_z3 #15 = 0x5D7A24(메인·서브·헤드·보디·풋·서브탱크·에스케이프, 팔레트 순서 같음),
#82 = 0x5D7F60(엘프 목록 단추; 팔레트 0x5FD950 과 순서까지 같음, 타일도 GBA 순서 그대로 —
같은 일본어 그림이 여러 자리에 있어 순서 규칙으로 자리를 정한다)."""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import rz2_gfx

JP_ROM = os.path.join(ROOT, '..', 'Rockman Zero', 'roms', 'Rockman Zero 3 (Japan).gba')
KR_ROM = os.path.join(ROOT, '_work', 'rz3_kr.gba')

# (파일, 항목, 레코드 위치, GBA 서술자, 충돌 허용)
# 서브 화면 타일셋 4종은 컬렉션판이 L/R 단추 아이콘 타일(HD 로 덧그림)을 비워 둠 → 그 타일은 컬렉션 그대로(충돌 타일 건너뜀)
TILESETS = [
    ('sub_z3', 0, 0x00, 0x547410, True ),       # 상태
    ('sub_z3', 0, 0x14, 0x547424, True ),       # EX 스킬
    ('sub_z3', 0, 0x28, 0x547438, True ),       # 옵션 + 결과
    ('sub_z3', 0, 0x3C, 0x54744C, True ),       # 엘프 목록
    ('sub_z3', 0, 0x190, 0x5475DC, False),      # 코드네임
    ('sub_mini_z3', 0, 0x00, 0x547438, True ),  # 미니 게임 쪽
    ('sdisk_z3', 0, 0x00, 0x547438, True ),     # 시크릿 디스크 쪽
    ('result_z3', 0, 0x00, 0x547438, True ),    # 결과 화면
    ('result_z3', 0, 0x14, 0x5475DC, False),    # 결과 화면 코드네임
    ('g_over_z3', 0, 0x00, 0x547A78, False),    # 게임오버
    ('title_z3', 0, 0x00, 0x5472A8, 'merge'),   # 타이틀 로고: 컬렉션판이 ® 를 지움 → 한글판 바뀐 바이트를 덮고(ㅈ 가 그 자리) ® 지움은 옮긴다
    ('title_z3', 0, 0x14, 0x5472BC, False),     # 시작 안내
]
SPRITES = [
    dict(kind='tileset', desc=0x5D7A24, gpal=0x5DF7AC, entry=15),
    dict(kind='tileset', desc=0x5D7F60, gpal=0x5FD950, entry=82, linear=True),
    # 로고 등장 연출 글자 띠: 98 번부터 컬렉션이 작은 스프라이트마다 4타일 칸으로 띄워 담았다(GBA 112장 → 133장)
    dict(kind='tileset', desc=0x5D849C, gpal=0x61B11C, entry=149, linear=True,
         remap={98: 100, 99: 101, 100: 104, 101: 105, 102: 108, 103: 109, 104: 112, 105: 113,
                106: 116, 107: 117, 108: 120, 109: 124, 110: 128, 111: 132}),
]

if __name__ == '__main__':
    rz2_gfx.run(JP_ROM, KR_ROM, TILESETS, SPRITES, 'obj_fnt_z3', post={('title_z3', 0, 0x00): rz2_gfx.logo_post(3, 0x522ED0, 0x100, cols=30)})
