**Developer architecture reference for the Tengai Makyou II (ATMJ) Korean patch.** 모든 파일 경로는 `patch/` 기준 상대경로입니다.

# ARCHITECTURE — 천외마경II 卍MARU 한국어 패치

이 문서는 패치의 빌드 파이프라인과 각 단계가 다루는 바이너리 포맷을 개발자 관점에서 설명합니다. 대상은 닌텐도 DS용 **천외마경II 卍MARU**(일본판, 게임코드 `ATMJ`, 128 MiB / 134,217,728 바이트)입니다.

---

## 1. 전체 빌드 파이프라인

빌드의 진입점은 `dialogue/build_ko.py`이며, `patch.py`(루트)가 대사 단계와 메뉴 단계를 순서대로 호출합니다.

```
                 입력: 깨끗한 ATMJ 일본판 ROM (.nds)
                                │
   ┌────────────────────────────┴─────────────────────────────┐
   │ patch.py (통합 러너)                                       │
   │                                                            │
   │  1단계: dialogue/build_ko.py --no-menu                      │
   │    ┌──────────────────────────────────────────────────┐    │
   │    │ a. 폰트 디코드   tengai_cobj_font.decode_font       │    │
   │    │ b. 매핑 생성     font_mapping.build_mapping         │    │
   │    │      (KS2350 한글 ↔ 한자 슬롯/SJIS 코드)            │    │
   │    │ c. 폰트 주입     galmuri_bdf.render_char            │    │
   │    │      → tengai_cobj_font.encode_into (슬롯 in-place) │    │
   │    │ d. 대사 재조립   translation.json                   │    │
   │    │      scs_segment.from_segments → scs_repack.rebuild │    │
   │    │ e. 시스템 텍스트 arm9_text.apply_entries            │    │
   │    │      (ARM9 + 오버레이, SJIS 길이 보존)              │    │
   │    └──────────────────────────────────────────────────┘    │
   │                                                            │
   │  2단계: menu/patch_all.py → menu_insert.py                  │
   │    ┌──────────────────────────────────────────────────┐    │
   │    │ menu/png/*.png → 타일/팔레트/타일맵 역패킹           │    │
   │    │ → LZ10/CMP 재압축 → tools.append_repoint            │    │
   │    └──────────────────────────────────────────────────┘    │
   │                                                            │
   │  3단계: 원본 크기보다 작으면 0xFF 패딩                       │
   └────────────────────────────┬─────────────────────────────┘
                                │
                 출력: 한글 ROM (.nds, 134,217,728 바이트)
                                │
                 dist/*.xdelta = (원본 → 한글 ROM) 바이너리 델타
```

모든 단계는 ROM의 빈 패딩 영역에 데이터를 추가하고 **FAT 엔트리만 갱신**하므로 헤더(0x00~0x15D)와 CRC는 손상되지 않습니다. 따라서 대사·폰트·메뉴 단계를 안전하게 순차 조합할 수 있습니다.

번역 데이터를 갱신한 뒤에는 항상 `patch.py`로 재빌드해야 게임에 반영됩니다. 통일/배너 도구(`merge_unify*.py`, `banner_tool.py`)는 JSON만 인플레이스로 수정하고 ROM 빌드는 하지 않습니다.

---

## 2. SCS 대사 컨테이너 포맷

대사는 `.scs` 컨테이너에 저장되며, `.scb`가 텍스트를 인덱스로 참조합니다. 따라서 **엔트리 개수·순서는 절대 불변**이고 내용만 교체합니다.

### 2.1 컨테이너 레이아웃 (`scs_repack.py`)

`.scs = [u16 LE 포인터 테이블 헤더] + [엔트리 본문 바이트열]`

- `u16[0]` = 본문 시작 오프셋(= 헤더 길이)
- `u16[1]` = reserved (전 파일 0)
- `u16[2..]` = 각 엔트리 시작오프셋 ÷ 2 (본문 시작 기준 상대, 워드 단위)
- 엔트리 개수 = `(u16[0] - 4) / 2`

`split_entries(scs)`는 포인터를 절대 오프셋(`start + p*2`)으로 변환해 본문을 슬라이스합니다. `rebuild(reserved, body)`는 각 엔트리를 홀수면 `\x00`으로 짝수 정렬한 뒤 누적 오프셋÷2를 포인터로 재계산해 `struct.pack('<{2+n}H', start, reserved, *ptrs)`로 헤더를 재생성합니다. 텍스트 길이가 변해도 헤더가 자동 재계산되며, 2,272개 `.scs` 전수 round-trip 100% 바이트 일치가 검증되어 있습니다.

### 2.2 엔트리 본문 인코딩 (`scs_segment.py`, `scs_text.py`)

본문은 다음 토큰의 혼합입니다.

| 분류 | 바이트 | 비고 |
| --- | --- | --- |
| 전각 SJIS | 2B (리드 `0x81–0x9F`/`0xE0–0xFC` + 트레일) | 한자/히라가나/전각 |
| 반각 카나 | 1B (`0xA1–0xDF`) | |
| 반각 ASCII | 1B (`0x20–0x7E`) | |
| 제어코드 `0x10`/`0x11` | 4B (`OP 00 PARAM 00`) | 화자/초상, 인라인 명령 |
| 기타 제어 (`0x0D` 줄바꿈 / `0x0C` 화면지움 / `0x12` 버튼대기 / `0x00` NUL) | 2B (`XX 00`) | |

특수 시퀀스:
- 페이지 구분 = `12 00 0D 00 0C 00` (버튼대기 → 줄바꿈 → 화면지움)
- 엔트리 종료 = `12 00 00 00`
- 전각 공백 = `0x8140`

`scs_segment.to_segments(bytes)`는 본문을 좌→우 스캔해 **제어코드 세그먼트(`{'c': hex}`)** 와 **번역가능 텍스트 세그먼트(`{'jp':.., 'ko':''}`)** 로 분리합니다. 화자/초상·인라인명령·줄바꿈·페이지 구분은 모두 `c` 세그먼트로 원형 보존됩니다. SJIS 디코드 실패 시 `'〓'`로 대체하고 통계를 남깁니다.

`from_segments(segs, syl2sjis)`는 역변환입니다. `c` 세그먼트는 `bytes.fromhex` 그대로 복원하고, `ko`가 채워진 `jp` 세그먼트는 `ko`를 `\n`으로 split해 각 부분을 글자 단위로 인코딩한 뒤 `0x0D 00`(줄바꿈)으로 join해 긴 줄을 분할합니다. `ko`가 비어 있으면 `jp`를 그대로 `shift_jis`로 인코딩합니다.

`scs_text.char_to_bytes(ch, syl2sjis)`가 단일 글자 인코딩 기준 구현입니다. `build_line`/`build_page`/`build_entry`는 줄을 `NEWLINE`으로, 페이지를 `PAGE_SEP`로 잇고 끝에 `END`를 붙이며 홀수면 0x00 패딩합니다.

### 2.3 한글 인코딩 — johab 직접 인코딩이 아닌 한자코드 재매핑 트릭

핵심: **한글은 johab으로 직접 인코딩하지 않습니다.** 대신 한글 음절을 미리 매핑된 한자 SJIS 코드로 치환하고, 그 한자 글리프 슬롯에 한글 글리프를 그려 둡니다. 게임이 화면에 한자 코드를 출력하면 슬롯에 그려진 한글이 보입니다.

`char_to_bytes`는 글자가 매핑사전(`syl2sjis`)에 있으면 SJIS 코드를 **상위바이트 우선**(`[(code>>8)&0xFF, code&0xFF]`)으로 반환하고, 공백/U+3000은 전각 공백(`0x8140`)으로, 그 외는 `shift_jis`로 인코딩합니다(반각이거나 KS X 1001 2,350자 범위 밖이면 `ValueError`). 모든 엔트리 길이는 짝수로 유지되어 포인터의 ÷2 정확성을 보장합니다.

---

## 3. 폰트 파이프라인 — Galmuri11 → CObj 슬롯 주입

목표: **한글을 게임의 한자 글리프 자원에 덮어쓰기.** 세 모듈이 협업합니다.

### 3.1 CObj 전각 폰트 코덱 (`tengai_cobj_font.py`)

대상은 `font12_GothicW3_bit.cobj`(파일 ID 9138, 고정 241,920 바이트, 7,560 글리프).

- 데이터 단위는 8×8 타일 = 8바이트(MSB-first, row-major).
- 각 바이트는 **인접 비트쌍을 교환**해 저장됩니다: `b' = ((b>>1)&0x55) | ((b<<1)&0xAA)` (자기역; 블릿이 그릴 때 되돌림).
- 타일맵 폭 `TILE_W=378`, 한 줄 글리프 수 `GLYPH_W=189`. 글리프 N은 2×2 타일 블록이며 `gx=N%189, gy=N//189`. 타일 오프셋은 `TL=(2gy)*378+2gx, TR=+1, BL=+378, BR=+379` — **아래 두 타일이 위와 378타일 떨어져 있는 것이 핵심**입니다(이를 놓치면 원문자 ①~⑳ 하단이 잘림).

`decode_font(raw)`는 비트쌍 복원 → unpackbits → 4타일 조합으로 `(N,16,16)`을 반환합니다. `encode_into(raw, n, glyph16)`는 16×16을 4사분면으로 packbits → 비트쌍 교환 → 해당 타일 오프셋에 in-place 기록(크기 불변). 동일 글리프 재기록 시 바이트 동일·체크무늬 왕복 일치가 검증되어 있습니다.

### 3.2 매핑 (`font_mapping.py`)

- `KANJI_START_SJIS = 0x889F`(亜), `KANJI_START_SLOT = 1418`(첫 비어있지 않은 슬롯), `PLACEHOLDER_SLOT = 1410`(두부 템플릿).
- `gen_valid_sjis(count)`는 lead `0x88–0x9F`+`0xE0–0xEF`, trail `0x40–0xFC`(0x7F 제외)에서 `0x889F` 이상이며 단일 CJK(U+4E00–U+9FFF)로 디코드되는 코드를 SJIS 순서로 수집합니다.
- `find_nonblank_slots`는 1418부터 전부-0이거나 두부 템플릿(슬롯 1410)과 동일한 빈칸을 건너뛰며 `count`개를 수집합니다(빈칸은 코드를 소비하지 않고 스킵).
- `build_mapping(glyphs, hangul)`이 `valid_sjis`와 `non_blank_slots`를 한글과 zip해 `syl2slot` / `syl2sjis` / `slot2syl`을 만듭니다.

앵커 검증: 亜=슬롯1418/0x889F, 円(0x897E)=1574, 園(0x8980)=1576(빈칸 1575 스킵), 蛙(0x8A5E)=1731, 救(0x8B7E)=1952.

### 3.3 글리프 렌더 (`galmuri_bdf.py`)

`Galmuri11.bdf`를 파싱합니다. `GLYPH_SIZE=16, BASELINE=11, LEFT=1`. 게임 한자 잉크가 16×16 셀의 좌상단 ~11×11을 차지하므로 CAP_HEIGHT 11의 Galmuri11을 baseline=11, left=1에 두면 정확히 겹칩니다.

`render_char(ch)`는 BDF의 `ENCODING/BBX w h xoff yoff/BITMAP`을 읽어 `out_row = baseline-(yo+h)+r`, `out_col = left+xo+c` 식으로 배치해 `(16,16)` uint8(0/1)을 반환합니다(비트 추출 MSB-first). `build_ko.insert_font`는 이 비트맵을 `encode_into`로 매핑된 슬롯에 무손실 기록하며, Galmuri에 없는 음절은 missing으로 카운트합니다.

---

## 4. ARM9 / 오버레이 텍스트 (`arm9_text.py`)

대사 외 텍스트(메뉴·시스템·전투·아이템·주문·지명·적名)는 ARM9 바이너리(`rom.arm9`, 1,180,920 바이트)와 오버레이에 SJIS 널 종료 문자열로 저장됩니다. 포인터가 이를 참조하므로 **바이트 길이 보존이 필수**입니다(한자/카나/기호 = 2B, 한글 1음절 = 2B, 전각 공백 0x8140).

`apply_entries(a9, entries{off,jp,ko,slot?}, syl2sjis)`:
1. `jp`를 `shift_jis`로 인코딩한 길이 `L`과 `a9[off:off+L]`가 일치하는지 **원문 검증**.
2. `slot`이 주어지면 `span=slot, budget=slot-2`(최소 2B 널 확보), 없으면 `span=L, budget=L`.
3. `ko`를 `char_to_bytes`로 인코딩(`encode_ko`), 예산 초과면 에러 기록, 아니면 in-place 기록 후 `[off+len(ko_b), off+span)`을 0x00 패딩.

`￥` 제어코드(`￥＞`, `￥右`, `￥キ`, `￥Ｚ１`, `￥全` 등)는 2바이트 SJIS로 라운드트립이 보존되므로 `ko`에 그대로 두면 유지됩니다. `verify_entries`는 치환 후 각 엔트리가 기대 한글로 디코드되는지 점검합니다. 오버레이는 비압축이라 `rom.files`에 직접 기록합니다.

---

## 5. 메뉴 그래픽 PNG 키트

화면에 '그림으로서의 글자'로 그려지는 메뉴는 텍스트 토큰 패치와 별개로 PNG 왕복(round-trip)으로 교체합니다. 대상 세 종:

- **mainmenu.obc** (LZ10, 8bpp) — 메인/필드/하단 라벨. 4B 플래그/팔레트 길이 + 192B(96색 BGR555 팔레트) + 4B 픽셀 길이 + 200B부터 8bpp 타일(64B/타일). 기존 워드 뷰는 앞 장식 4타일을 건너뛰어 456B부터 시작. 워드 = 8타일(가로4×세로2 = 32×16) 그리드.
- **command_icon (bs_obj_command_icon1~17.cobj)** (LZ10, 4bpp) — 전투 명령 아이콘. 헤더 없는 순수 256B = 8타일, 32×16. 검정(배경)·흰색(글자) 2색.
- **kiten (char00.chr/scrn00.scr/palt.pal)** (CMP) — 시작 선택 화면, 256×256.

### 5.1 저수준 I/O (`tools.py`)

헤더 오프셋 FAT@0x48 / FNT@0x40을 읽습니다. `read_file(rom, fid)`는 FAT 엔트리의 start/end로 슬라이스, `parse_fnt`는 0xF000 루트부터 재귀 walk하며 Shift-JIS 디렉터리 이름을 디코드해 `fid → 풀경로` dict를 만듭니다.

압축: `lz10_dec`는 0x10 매직 후 8비트 플래그·2바이트 백레퍼런스(길이=`(v>>12)+3`, 거리=`(v&0xFFF)+1`)를 해제합니다. `lz10_store`는 **백레퍼런스를 전혀 쓰지 않는 전부-리터럴 인코더**입니다 — BIOS `LZ77UnCompReadNormalWrite16bit`가 `disp<2` 매치에서 깨지는(초록 깨짐) 문제를 회피하기 위함이며, 파일이 약 +12.5% 커집니다.

`append_repoint(rom, fid, new, align=0x200)`은 모든 FAT end의 최댓값을 0x200 정렬한 위치(0xFF 패딩)에 데이터를 기록하고 `FAT[fid]`의 start/end 8바이트만 갱신합니다. 헤더 0x00~0x15D 무손상 → CRC 유지.

### 5.2 CMP 다단계 압축 코덱 (`cmp.py`)

kiten의 char/scrn/palt가 쓰는 자체 컨테이너입니다.

- CMP 헤더 = `"CMP"`(3B) + `ver`(1B, 해제 단계 수) + `f1`(u32 최종 크기) + `f2`(u32; 하위바이트=외부 타입, 상위 3B=그 단계 출력 크기).
- `cmp_decode`는 `f2` 타입별 외부 1단계 해제(`0x24`/`0x28` Huffman, `0x10` LZ10, `0x11` LZ11, `0x30` RLE) 후, 결과 레이어의 첫 바이트 타입으로 `len==f1`까지 최대 8회 반복 해제합니다(예: char00 ver2 = Huffman4→LZ10, scrn00 ver3 = Huffman4→LZ10→RLE).
- 재인코딩은 **RLE 단일 단계**(`cmp_encode_rle`)로 하며 `ver=1`이 필수입니다. 원본 ver 2/3을 남기면 추가 해제를 시도해 깨집니다.

### 5.3 추출 (`menu_extract.py`)

`bgr555`로 5비트→8비트 색 확장. `extract_mainmenu`는 LZ10 해제 후 96색 팔레트와 8bpp 타일을 워드 그리드로 배치하고, 녹색(0,248,0) 글자 인덱스를 흰색으로 치환해 화면과 일치시킵니다. `extract_commands`는 4bpp 타일을 합성 팔레트(0=검정, 5=흰색)로 디코드합니다. `extract_kiten`은 `parse_fnt`로 경로를 찾아 CMP 해제 후, 팔레트 뱅크 헤더(앞 4B)를 제거하고(안 빼면 색 2칸 밀림) char 서브헤더 뒤 4bpp 타일을 scrn 타일맵(u16: `ti&0x3FF, hflip>>10, vflip>>11, palbank>>12`)으로 256×256 인덱스에 합성합니다. 산출물은 PIL P모드 PNG입니다.

### 5.4 삽입 (`menu_insert.py`, `patch_all.py`)

`load_idx`는 P모드 PNG는 인덱스를 직접 쓰고, RGB는 팔레트와 유클리드 최근접 매칭으로 인덱스화합니다.

- `insert_mainmenu`: 원본 LZ10 해제 → 앞 456B 메타데이터+팔레트+장식 4타일 보존, PNG를 워드 그리드 역매핑으로 8bpp 타일 재구성, `lz10_store`로 재압축(round-trip assert) → `append_repoint`.
- `insert_command`: 8타일을 `v0|v1<<4` 4bpp 패킹, `lz10_store` → `append_repoint`.
- `insert_kiten`: 32×32 블록마다 우세 팔레트 뱅크를 추출, 4방향 플립으로 타일 디덥(타일 1024 초과 시 예외), 타일맵 엔트리 `ti|hf<<10|vf<<11|pl<<12` 구성, char를 원본 타일 수까지 0-타일 패딩해 크기 유지, `cmp_encode_rle(ver=1)`로 재압축(round-trip assert) → `append_repoint`.

`patch_all.py`는 `png/` 폴더를 `menu_insert.py`에 넘기는 얇은 래퍼이며, 폴더에 **존재하는 PNG만 선택적으로** 적용합니다.

세부 사양은 `menu/PATCH_DATA.md`에 정리되어 있습니다.

---

## 6. 지명 배너 포맷과 banner_tool

지명 배너는 게임이 **가장 넓은 행의 글자 수에 맞춰 프레임(테두리 판)을 자동 신축**합니다(가로 너비를 정하는 별도 코드 없음). 따라서 행 텍스트의 글자 폭만 바꾸면 됩니다.

- 배너 판별: `segs[0].c`의 hex 첫 바이트 == `0x16` 이고 길이 ≥ 6.
- 헤더 `16 00 [p1] 00 [p2] 00`: `p1` = 세로 레이아웃(5=후리가나행 있음 / 8=없음), `p2` = 8(박스 높이). 둘 다 가로폭과 무관.
- 행 구분 = 제어바이트 `0x0D`/`0x0C`. 폭 = 행 글자 수(전각 공백 U+3000 포함, 고정폭 1).

`banner_tool.py` 명령:
- `list [needle]` — 모든 배너 + p1/p2/프레임(=max 행폭) 출력, 이름 검색.
- `pad <idx> <target>` — 본문(마지막 행)의 알맹이를 좌(`pad//2`)/우 균등 전각 공백 패딩으로 목표 폭에 맞춤.
- `setrow <idx> <row> <text>` — 특정 행 첫 세그에 직접 지정.

대상 JSON 탐색 순서는 `dialogue/translation.json` → `translation.json` → `data/translation.json`. `save()`는 `.bak` 복사 후 `indent=1`로 저장하며, 수정 후 `patch.py` 재빌드가 필요합니다.

---

## 7. 번역 데이터 스키마

### 7.1 `translation.json` (대사)

3중 중첩: 최상위 `files[]` → 각 파일 `entries[]` → 각 엔트리 `segs[]`.
- 텍스트 세그: `jp` / `ko` 필드.
- 제어 세그: `c` 필드(원본 바이트의 hex 문자열).
- 파일 엔트리에는 `reserved`(scs 헤더 `u16[1]`)가 있을 수 있습니다.

`build_ko.patch_dialogue`는 번역(`ko` 비어있지 않음) 세그먼트가 하나라도 있는 파일만 대상으로, 엔트리를 `i` 기준 정렬 → `from_segments(e['segs'], syl2sjis)` → `rebuild`로 재조립해 `rom.files[file_id]`를 교체합니다.

### 7.2 `arm9_translation.json` (ARM9 텍스트)

파일 계층 없는 **평탄한 단일 `entries[]`** 배열. 각 엔트리는 `{off, jp, ko, slot?}`. `arm9_text.apply_entries`가 이를 ARM9 바이너리에 적용합니다.

### 7.3 `overlay_translation.json` (오버레이)

오버레이 텍스트 번역 데이터. `build_ko`가 오버레이 텍스트 치환에 사용합니다(통일 도구 `merge_unify*.py`는 이 파일을 참조하지 않으며 `translation.json`/`arm9_translation.json`만 다룹니다).

### 7.4 `지명사전.json` / `지명사전.txt` (187개)

지명 통일의 기준 근거. 텍스트 포맷은 `jp | ko | jp글자수/ko음절수 | 비고` 파이프 구분(`#` 주석). 핵심 변환 규칙: `峠`(国字)→재, `村`→촌, `の`→의, `神社`→신사, `区`→구, `町`→정, `寺`→사, `院`→원, `谷`→곡, `島`→도, `塚`→총. 가타카나는 음차, 전각 영문 `ＨａＨｉ`는 그대로 유지+촌. **음절수 ≤ 글자수**(배너 크기맞춤) 조건을 충족합니다. 일반명사 16개(高山·神社·外国·洞窟 등)는 지명이 아니므로 제외.

---

## 8. 지명 통일 워크플로 (`merge_unify.py`, `merge_unify_arm9.py`)

다중 에이전트 용어통일 워크플로가 산출한 결과 JSON을 원본 작업 단위와 좌표로 재매칭해 번역 데이터의 `ko` 필드에 안전 병합하는 후편집 단계입니다.

`merge_unify.py`:
- 결과 JSON에서 `r.get('result', r)['results']`를 읽어 `batches = {n: ko_list}`로 정리(빈 배치 제외).
- 각 배치 `n`마다 원본 작업파일 `unify_batches/u_%03d.json`을 로드. `ko_list`와 `jobs` 길이가 다르면 부분반영 위험으로 **배치 전체 스킵**(mismatch 카운트).
- 매칭 시 `job['loc'] = (fi, ei, si)`로 `d['files'][fi]['entries'][ei]['segs'][si]`에 접근. seg에 `jp` 키가 있고 새 `ko`가 str이며 기존과 다를 때만 덮어씀.
- 최초 1회 `translation.json.preunify.bak` 백업 후 `indent=1, ensure_ascii=False`로 저장.

`merge_unify_arm9.py`는 동일 로직의 arm9 전용 축약판입니다. 작업파일은 `unify_arm9/a_%03d.json`이고, 평탄한 구조라 `job['loc'][0]` 단일 인덱스로 `d['entries'][i]`에 직접 접근합니다. 백업은 `arm9_translation.json.preunify.bak`.

두 도구 모두 JSON만 인플레이스 갱신하므로, 병합 후 `patch.py`로 재빌드해야 게임에 반영됩니다.

---

## 9. 빌드 불변식 요약

- 출력 ROM 크기 = **134,217,728 바이트**(원본과 동일; 작으면 0xFF 패딩).
- ROM 헤더(0x00~0x15D)·CRC 무손상 — 모든 변경은 패딩 영역 추가 + FAT 8B 갱신.
- `.scs` 엔트리 개수·순서 불변(.scb 인덱스 정합), 본문만 교체.
- 모든 엔트리/문자열 길이 짝수·바이트 예산 보존(포인터·널 종료 안전).
- 폰트 파일 크기 고정(241,920 바이트), 슬롯 in-place 기록.
- CMP 재압축은 RLE `ver=1`, LZ10 재압축은 매치없음(VRAM 16비트 쓰기 안전).

---

## 10. 단일 마스터 + DEPLOY 파이프라인 (v2.9~)

### 10.1 텍스트 마스터 `translation/번역_마스터.json`

세 갈래로 흩어져 있던 번역 소스를 한 파일로 합친 것. 편집 지점은 **`ko` 필드뿐**이다.

| 섹션 | 원래 파일 | 주입 대상 | 방식 |
| --- | --- | --- | --- |
| `dialogue` | `translation.json` | `.scs` 대사 컨테이너 1,508개 | `from_segments` → `scs_repack.rebuild` 로 재조립 |
| `arm9` | `arm9_translation.json` | `arm9.bin` | 원문(SJIS) 매칭 후 바이트 보존 치환 |
| `overlay` | `overlay_translation.json` | 오버레이 fid 0 / 8 / 11 | 동일(`arm9_text.apply_entries`) |

`arm9`/`overlay`는 **원문 바이트가 그대로 있어야** 치환된다. 그래서 `DEPLOY.py`는 반드시
**깨끗한 일본판을 base** 로 잡는다(이미 한글화된 롬을 base 로 쓰면 매칭이 전부 실패한다).

### 10.2 그래픽 레이어 분리

픽셀 작업 결과물(37개 파일)은 텍스트로 표현할 수 없고 저장소에 원본 데이터를 둘 수도 없다.
`DEPLOY.py`는 `dist/`의 배포 패치를 사용자의 원본에 적용해 **참조 롬**을 만든 뒤, 거기서
해당 파일만 복사해 온다(`IMAGE_FIDS`).

| fid | 파일 | 내용 |
| --- | --- | --- |
| 2764 | `data/usd/fuw_bg.chr` | 지도 모드 상단 일본지도 + 지방명 |
| 2766 | `data/usd/mainmenu.obc` | 메인메뉴 라벨 전체 |
| 3940–3956 | `bs_obj_command_icon1~17` | 전투 명령 아이콘 |
| 3966–3969 | `bs_obj_name_p1~4` | 전투 스탯 이름판(卍丸/極楽/体/技) |
| 9138 | `font12_GothicW3_bit.cobj` | 한글 글꼴(한자 슬롯 주입본) |
| 9140, 9143 | `uno_all/kiten/bg00` | 시작 선택 화면 |
| 9161–9165 | `saveload/btn_obj/btn01~03` | 세이브·로드 버튼 |
| 9186–9200 | `saveload/mes_obj/mes01~08` | 세이브·로드 메시지 |

### 10.3 그래픽 포맷에서 반드시 지켜야 할 헤더 오프셋

그래픽 한글화 초기 버전(~v2.5)에서 **모든 한글 타일에 가로줄이 그어지는 현상**이 있었다.
원인은 압축 해제 결과의 앞부분을 타일 데이터로 착각한 것 —

- `fuw_bg.chr` : **8바이트 헤더 + 128색 BGR555 팔레트(256B) = 264바이트** 뒤부터 타일.
  8bpp, 32열 raster 배치. 264를 빼지 않으면 전 타일이 8바이트씩 밀려 찢어진다.
- 세이브/로드 `.chr` : **4바이트 크기 헤더** 뒤부터 타일(`len % 32 == 4` 로 식별).

검증은 에뮬레이터 세이브스테이트의 VRAM과 직접 대조하는 방법이 확실하다(자체 왕복
테스트는 같은 실수를 두 번 반복해도 통과한다).

### 10.4 그 밖의 그래픽 메모

- `mainmenu.obc` : 워드(32×16, 8타일)와 글리프16(16×16, TL/TR/BL/BR) 두 레이아웃이 섞여 있다.
  색 인덱스는 흰 글자 37/34(심/외곽), 어두운 글자 2/3(심/그림자).
- 12px 이하 작은 글자에는 **그림자·외곽선을 넣지 않는다**(자모 사이 1px 틈이 메워져 뭉갬).
- Galmuri 계열은 16/11/10/9px에서 선명하고 12~14px에서 흐려진다.

---

## 11. 대사 표시 규칙과 화면 단위 편집 (`narr_reflow.py`)

게임 대사창은 **한 화면 최대 3줄, 한 줄 18자(전각)**. `｜`(U+FF5C)는 화면 전환/멈춤 마커라
폭에 포함되지 않는다.

- `split_screens_pairs(segs)` → 화면 리스트(화면 = 줄 리스트, 줄 = `{jp, ko}`).
  화면 경계는 제어코드 0x12(버튼 대기)·0x10(화자)·0x0C(페이지), 화면 안 줄바꿈은 0x0D.
- `rebuild_segs(segs, korean_screens)` → 경계 제어코드를 보존한 채 화면별 한국어로 교체.
  `self_test()`가 "원문을 그대로 넣으면 바이트가 완전히 동일"함을 보장한다.
- 0x11 인라인 명령이 있는 엔트리는 화면 분할이 불안정해 자동 편집에서 제외한다.

### 왜 "한국어 줄수 ≤ 일본어 줄수"인가

번역이 원문보다 길어 한 화면이 3줄을 넘으면, 넘친 줄이 다음 화면으로 밀리고 **마지막
화면의 내용이 통째로 사라진다.** v3.0에서 이 유형(화면 밀림) 14건과 문장 누락 36건을
찾아 고쳤다. `tools/check_rules.py`가 이 조건을 검사한다.

---

## 12. 품질 검증 방법 (v3.0~v3.2)

규칙 검사만으로는 "밀려서 사라진 대사"를 잡지 못한다(밀린 결과물도 3줄/18자를 지키기
때문). 그래서 **원문 대조**를 별도로 돌렸다.

1. **후보 축소** — 마지막 화면이 미완결(조사·연결어미로 끝남)이거나, 한국어/일본어 글자수
   비가 낮은 엔트리를 추린다.
2. **대조 검토** — 화면 단위 `{jp, ko}` 묶음을 놓고 누락·밀림·오역·어색을 판정하고
   수정안을 낸다.
3. **기계 검증** — 수정안이 3줄/18자/줄수/슬롯/전각 규칙을 지키는지 전수 확인한 뒤 적용.

같은 방식을 오프닝 자막(오버레이 fid 8, 181조각)과 arm9/오버레이 텍스트에도 적용했다.
오프닝은 조각 배열 순서가 표시 순서와 달라 화면 밀림 개념이 없고 오역만 대상이다.

---

## 13. 갱신된 빌드 불변식

- 출력 롬은 ndspy가 재작성한 유효한 NDS 이미지(뒤쪽 0xFF 패딩 없음, v2.9~).
  v3.3 결과물 MD5 = `0ef919bd56597223171a07c4343ef77e`.
- `arm9`/`overlay` 주입은 **원문 SJIS 바이트 매칭 성공 시에만** 이뤄진다 → base 는 항상 원본.
- 한글 1자 = 2바이트. arm9/overlay 항목은 `slot - 2` 바이트 이하(널 종료 여유).
- 대사는 전각만 인코딩 가능(반각 `,` `.` `!` `?` `~` → `，` `．` `！` `？` `〜`).
- 폰트 파일 크기 고정(241,920 바이트), 슬롯 in-place.
