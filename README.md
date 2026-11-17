# 록맨 제로&ZX 레거시 컬렉션 한글패치

Mega Man Zero/ZX Legacy Collection (Nintendo Switch, 010025C00D410000) 한글패치입니다.
런처와 여섯 게임(록맨 제로 1~4, 록맨 ZX, 록맨 ZX 어드벤트)의 **일본어(日本語) 칸**을 한국어로 바꿉니다. 다른 언어 칸은 그대로입니다.

> 게임 파일(NSP·추출물)은 이 저장소에 없습니다. 패치 파일은 [Releases](../../releases) 에서 받으세요.

## 대상

| 항목 | 값 |
|---|---|
| 본편 | 010025C00D410000 (v0) |
| 업데이트 | 010025C00D410800 **v262144 (1.0.4)** — 필수. 실행 파일 패치가 이 판에 맞춰져 있습니다 |
| DLC (리믹스 음악) | 있어도 없어도 됩니다 |

## 설치

### 스위치 (Atmosphere)

`MMZZXLC_KR_<버전>_atmosphere.zip` 을 SD 카드 루트에 풉니다.

- `atmosphere/contents/010025C00D410000/romfs/...` — 글꼴·대사·그림
- `atmosphere/contents/010025C00D410000/exefs/subsdk9` — 한글 출력 모듈
- `atmosphere/exefs_patches/MMZZXLC_KoreanPatch/48A7577F4E740FEDCB50BA59D7B45AF4.ips` — 실행 파일 패치

### 에뮬레이터 (Eden / yuzu 계열, Ryujinx)

`MMZZXLC_KR_<버전>_emulator.zip` 을 풀면 나오는 `KoreanPatch` 폴더를 게임의 모드 폴더에 넣습니다.

- Eden / yuzu 계열: `load/010025C00D410000/KoreanPatch/{romfs,exefs}`
- Ryujinx: `mods/contents/010025C00D410000/KoreanPatch/{romfs,exefs}`

## 한국어로 보기

1. **런처**: 「Option」 → 「Language」 에서 맨 위 「Japanese」 를 고릅니다. 이 칸이 「한국어」로 바뀌어 있습니다.
   이 설정은 게임에서 저장할 때 같이 기록되어 다음 실행에도 유지됩니다.
2. **각 게임**: 메뉴에서 게임을 고른 뒤 Y 버튼(판 바꾸기)으로 왼쪽 위 표시를 **「한국어판」**에 맞추고 시작합니다.

## 한글화 범위

- **록맨 제로 1·2·3·4**: 대사, 시스템 문장(메뉴·엘프·칩 설명 등), 그림 글자(타이틀·서브 화면·결과 등), 오프닝 스크롤
  - 번역·글꼴은 [rockman-zero-kr-patch](https://github.com/Einbroch/rockman-zero-kr-patch)(GBA)와 같습니다.
- **록맨 ZX · ZX 어드벤트**: 대사·시스템 문장, 그림 글자, 대화창 화자 이름표
  - 번역·글꼴은 [rockman-zx-kr-patch](https://github.com/Einbroch/rockman-zx-kr-patch)(NDS)와 같습니다.
  - 컬렉션판은 DS 판과 문장이 다른 곳이 있어(서브 화면 조작, 명칭, 시계 기능 삭제 등) 그 문장 150개는 따로 옮겼습니다.
- **런처**: 메뉴·설명·안내 창·매뉴얼·ZZ 카드(도전과제)·갤러리 카드 설명·곡 목록(일본어 제목)·Z 체이서 등 문자열 926개, 한글 글꼴

## 알려진 점

- 아직 모든 화면을 확인하지 못한 **시험판(0.9)** 입니다. 에뮬레이터(Eden)에서 각 게임의 오프닝·초반 대사·주요 메뉴를 확인했고,
  **스위치 실기에서는 확인하지 못했습니다.** 깨지거나 일본어가 남은 화면을 이슈로 알려 주세요(화면 캡처와 진행 상황을 함께).
- 런처 스태프 롤(크레딧)과 영어 곡 제목은 원문 그대로입니다.
- 제로 3 로고 등장 연출, 제로 4 데모 화면 구석의 작은 로고는 일본어 그대로입니다.
- 런처의 「」 같은 전각 기호는 원래 일본어 글꼴 폭이라 뒤가 넓게 보입니다.

## 어떻게 바꾸나

컬렉션은 GBA·DS 게임을 에뮬레이트하지 않고 코드를 옮긴 네이티브 이식이라, 롬 패치를 그대로 쓸 수 없습니다.

- **한글 출력 모듈**(`kohook/`, Rust): 실행 파일의 안 쓰는 가져오기 함수 이름을 모듈 함수로 바꿔 잇고(`tools/mainpatch.py`),
  각 게임의 글자 출력 함수 몇 곳에 16바이트 훅을 겁니다. 제로 1~4 는 12px 가변폭 출력기를 통째로 대신하고,
  ZX·ZXA 는 2바이트 한글 코드를 읽어 임시 글리프 칸에 풀어 원래 그리기 경로로 그립니다.
- **데이터**: 제로 대사·글꼴은 GBA 한글판 빌드 결과에서, ZX·ZXA 대사·그림은 NDS 한글판 원고와 도구로 컬렉션 원문 기준으로 다시 만듭니다.
- **런처**: MT Framework GMD 문자열을 바꾸고, 글꼴(GFD + BC7 텍스처)에 한글 페이지를 더합니다.

## 빌드

필요: Python 3(`numpy`, `Pillow`, `ndspy`, `keystone-engine`, `capstone`), Rust(`aarch64-unknown-none` 대상, `rust-lld`),
GBA 한글판 저장소(`../Rockman Zero`), NDS 한글판 저장소(`../Rockman ZX, Advent`, 일본판 롬 두 개와 `out/` 빌드 결과),
본편+업데이트를 합쳐 추출한 RomFS(`_work/romfs/...`)와 업데이트의 실행 파일 `main`(`_work/exefs_upd/main`, 압축 해제본 `main.img`).
추출은 hactool 등 각자 도구로 합니다(키 파일 필요).

```bash
python tools/build_rz1.py
```

```bash
python tools/make_dist.py
```

결과는 `build/` 와 `dist/` 이고, zip 의 SHA-256 은 릴리즈의 `SHA256SUMS.txt` 와 같아야 합니다.

| 파일 | 하는 일 |
|---|---|
| `build_rz1.py` | 전체 빌드(데이터 → 모듈 → 실행 파일 패치 → 그림 → 런처) |
| `rz1~4_data.py`, `zcblob.py` | 제로 1~4 대사·시스템 문장 데이터(GBA 한글판 → 모듈 데이터, 컬렉션 원문과 쪽·칸 대조) |
| `rz1~4_gfx.py`, `zcpack.py`, `lz77.py` | 제로 1~4 그림 글자(컬렉션 그림 묶음에 제자리 재압축) |
| `zx_build.py`, `zxa_build.py`, `zxa_coll_ko.py` | ZX·ZXA 대사·글꼴·그림·이름표(컬렉션 원문 기준, 컬렉션 전용 문장 번역) |
| `launcher_build.py`, `gmd.py`, `gfd.py`, `bc7a.py`, `fonttex.py`, `arcpack.py`, `mtarc.py` | 런처 문자열·글꼴 |
| `mainpatch.py`, `elf2nso.py`, `build_kohook.sh` | 실행 파일 IPS·모듈 NSO |
| `make_dist.py` | 배포 zip 두 벌 + SHA256SUMS |
| `launcher/ko_*.json`, `zx/zxa_coll_ko.json` | 번역 원고 |

## 폰트

- 게임 안 한글: 갈무리(Galmuri), SIL Open Font License 1.1 — [LICENSE-Galmuri.txt](LICENSE-Galmuri.txt)
- 런처 한글: [에스코어 드림](https://www.s-core.co.kr/company/font/)(S-Core Dream)
