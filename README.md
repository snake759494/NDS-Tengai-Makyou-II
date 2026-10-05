<!-- English summary for GitHub discoverability -->
**Korean fan-translation patch for _Tengai Makyou II: Manji Maru_ (天外魔境II 卍MARU, Nintendo DS, game code ATMJ).** Full source: translation data, build tools, and font. No ROM included — bring your own clean Japanese dump.

# 천외마경II 卍MARU 한국어 패치

> 닌텐도 DS **천외마경II 卍MARU**(일본판, 게임코드 `ATMJ`)의 비공식 한국어 팬 번역.
> **대사·시스템·메뉴·전투 텍스트 + 메뉴/지도/전투 그래픽** 한글화.

- 코드/도구: **MIT** · 폰트: **Galmuri11 / Galmuri14** (SIL OFL 1.1)
- 비영리 팬 번역 — **이 저장소에는 게임 롬이 일절 포함되어 있지 않습니다.**
- 최신 버전: **v3.4** → [Releases](../../releases)
- 이전 저장소(`snake7594/NDS-Tengai-Makyou-II`)의 전체 이력(v1.0~v3.3)을 이어받은 새 공식 저장소입니다.

---

## 1. 그냥 한글로 플레이하고 싶다면

준비물: **깨끗한 일본판 원본 롬(ATMJ)** + xdelta 패처.

`dist/` 또는 [Releases](../../releases)에서 최신 `.xdelta`를 받아 원본 롬에 적용합니다.
2차 압축을 쓰지 않아 PC 패처와 안드로이드 **UniPatcher** 양쪽에서 그대로 동작합니다.

**PC (xdelta3)**

```bash
xdelta3 -d -s 원본_ATMJ.nds "dist/Tengai_Makyou_II_KR_v3.4.xdelta" 한글판.nds
```

**GUI 패처**(Delta Patcher, MultiPatch 등): 원본 롬과 `.xdelta`를 지정하고 Apply.

**안드로이드**: UniPatcher에서 `.xdelta`를 고르고 원본 롬을 지정.

결과 확인 — v3.4 결과물의 MD5는 `04746b727245140c90527d717ecba762` 입니다.

**v3.4:** 이미지 리소스 169개 재작업, 메뉴 흰색 글자·하단 버튼·나라 지도 정렬 수정, 미니맵 표지 324곳 교체. [상세 패치 내역과 변경 이미지 197개](docs/releases/v3.4/README.md).

> 원본 롬은 반드시 무수정 일본판이어야 합니다. 이미 다른 패치가 적용된 롬에는 실패합니다.

---

## 2. 번역을 직접 고치고 싶다면 (핵심)

**고칠 파일은 단 하나입니다:** [`translation/번역_마스터.json`](translation/번역_마스터.json)

```bash
python -m pip install ndspy pyxdelta        # 최초 1회
# translation/번역_마스터.json 편집 (UTF-8)
python tools/check_rules.py                 # 표시 규칙 검사 — "총 위반: 0" 이어야 함
python DEPLOY.py --jp 원본_ATMJ.nds          # 빌드 → build/ 에 롬 + xdelta 생성
```

`DEPLOY.py`가 그래픽·글꼴까지 입혀 완성된 롬과 배포용 패치를 만들고, 만든 패치를 원본에
되적용해 **역검증**까지 합니다.

### 마스터 파일 구조

```jsonc
{
  "dialogue": { "files": [ { "file_id": 4601, "path": "/script/b02/b02.scs",
                             "entries": [ { "i": 0, "segs": [
                               {"jp": "なるほど…", "ko": "과연…"},   // ← ko 만 고친다
                               {"c": "0d00"}                        // 제어코드(줄바꿈 등) — 손대지 말 것
                             ] } ] } ] },
  "arm9":    { "entries": [ {"off": 836424, "jp": "京都", "ko": "경도", "slot": 8} ] },
  "overlay": { "3": { "fileID": 8, "entries": [ {"off": 19936, "jp": "さあ", "ko": "자"} ] } }
}
```

| 섹션 | 내용 | 고치는 곳 |
| --- | --- | --- |
| `dialogue` | 게임 내 대사 전체(2,272 파일 / 12,043 엔트리) | 각 `segs[].ko` |
| `arm9` | 시스템·메뉴·상태창·지명·기술명 (2,941개) | `entries[].ko` |
| `overlay` | 오프닝 자막(181), 전투 커맨드·예/아니오(80), 저장 UI(24) | `entries[].ko` |

`jp`(원문), `c`(제어코드), `off`/`slot`은 **절대 바꾸지 마세요.** 빌드 시 원문 대조와 구조
복원에 쓰이며, 어긋나면 그 항목이 적용되지 않습니다.

### 반드시 지켜야 하는 제약

| 규칙 | 내용 | 어기면 |
| --- | --- | --- |
| **한 대사창 3줄** | `\n` 2개까지 | 표시가 깨지거나 프리징 |
| **한 줄 18자** | 전각 기준. `｜`(U+FF5C)는 폭에서 제외 | 글자가 창 밖으로 잘림 |
| **원문 줄수 이하** | 한 화면의 한국어 줄수 ≤ 일본어 줄수 | 내용이 밀려 **마지막 대사가 통째로 사라짐** |
| **전각 문자만** | 반각 `,` `.` `!` `?` `~` 금지 → `，` `．` `！` `？` `〜` | 빌드 시 인코딩 오류 |
| **KS X 1001 한글** | 완성형 2,350자 범위 | 글꼴에 글리프가 없어 깨짐 |
| **슬롯 바이트**(arm9/overlay) | 한글 1자 = 2바이트, `slot - 2` 이하 | 그 항목만 조용히 미적용 |

`python tools/check_rules.py`가 위 항목을 전부 검사합니다. **총 위반 0**이면 안전합니다.
(엔딩 스탭롤 중앙정렬 등 의도적 예외 21건은 따로 집계됩니다.)

### 참고: `｜` 마커

대사 원문의 `｜`는 **화면 전환/멈춤 지점**입니다. 폭 계산에는 안 들어가지만 위치가 바뀌면
대사 호흡이 달라지니 원문과 같은 자리에 두세요.

### 표기 기준

- 캐릭터: 卍丸=**만지마루**(좁은 칸은 만지/만), 極楽=**극락**(극락타로), 絹=**키누**(1자는 키), カブキ=**카부키**
- 지명: **한자독음**(한자 1자 = 한글 1음절) — 京都=경도, ~村=~촌, ~峠=~재. [`translation/지명사전.json`](translation/지명사전.json) 참조

---

## 3. 빌드가 어떻게 동작하나 (게임 데이터 없이 재현되는 이유)

패치 롬은 **텍스트 레이어 + 그래픽 레이어**로 이루어집니다.

- **텍스트**는 이 저장소의 마스터에서 매번 새로 만듭니다.
- **그래픽**(지도 지방명, 메인메뉴, 전투 아이콘/스탯판, 세이브·로드 버튼, 한글 글꼴 등
  37개 파일)은 픽셀 작업 결과물이라 텍스트로 표현할 수 없습니다. 대신 `DEPLOY.py`가
  **`dist/`의 배포 패치를 사용자의 원본 롬에 적용해 "참조 롬"을 만들고, 거기서 그 37개
  파일만 가져옵니다.** 저작권 있는 게임 데이터를 저장소에 두지 않으면서 그래픽까지
  똑같이 재현하는 방법입니다.

```
원본 ATMJ.nds ──┬─(dist 패치 적용)─→ 참조 롬 ──(그래픽·글꼴 37파일)──┐
                │                                                  ├─→ 한글판.nds
                └──────────────(base)──────→ 텍스트 레이어 적용 ────┘
                                              ↑ translation/번역_마스터.json
```

옵션:

```bash
python DEPLOY.py --jp 원본.nds --ref 직접만든_참조.nds          # 참조 롬 직접 지정
python DEPLOY.py --jp 원본.nds --ref-patch dist/…v3.0.xdelta   # 특정 버전 그래픽 사용
python DEPLOY.py --jp 원본.nds --no-patch                      # 롬만 만들고 xdelta 생략
```

> 그래픽 자체를 새로 고치려면 `tools/images/`의 추출·삽입 키트를 쓰고
> ([ARCHITECTURE.md](ARCHITECTURE.md) 5·6장), 결과 롬을 `--ref`로 넘기면 됩니다.

---

## 4. 저장소 구성

```
DEPLOY.py                  빌드 진입점 (이것만 실행하면 됨)
translation/
  번역_마스터.json           ← 번역 원본. 여기만 고치면 된다
  지명사전.json / .txt        지명 한자독음 통일 사전(187개)
tools/
  check_rules.py           표시 규칙·인코딩·슬롯 검사기
  master_split_merge.py    마스터 ↔ 개별 파일 변환
  scs_segment.py           .scs 대사 본문 인코딩/디코딩
  scs_repack.py            .scs 컨테이너 재조립
  scs_text.py              SJIS 문자 ↔ 바이트
  narr_reflow.py           화면 분할·재조립, 줄바꿈 규칙(18자/3줄)
  arm9_text.py             arm9·오버레이 바이트 보존 치환
  font_mapping.py          한글 ↔ 한자 슬롯 매핑
  tengai_cobj_font.py      CObj 전각 폰트 코덱
  galmuri_bdf.py           Galmuri11 비트맵 글리프 렌더
  ks2350.txt               KS X 1001 완성형 2,350자
  Galmuri11.bdf            한글 글꼴 원본
  images/                  그래픽 추출·삽입 키트(메뉴·메인메뉴·지명 배너)
dist/                      배포용 xdelta 패치 (버전별)
ARCHITECTURE.md            내부 포맷·파이프라인 상세
```

---

## 5. 현재 상태

| 영역 | 상태 |
| --- | --- |
| 본문 대사 | 약 97% 한글화 + 전수 원문 대조 QA(v3.0) |
| 오프닝 나레이션 | 한글화 + 원문 대조 교정(v3.1) |
| 시스템/메뉴/전투/저장 텍스트 | 한글화 + 원문 대조 교정(v3.2) |
| 그래픽 | 메인메뉴·지도 지방명·전투 아이콘/스탯판·세이브로드·시작화면 |

미포함: 서브로케이션 세부 지명(`chimei.scs`)은 커스텀 글리프가 필요해 제외했습니다.
게임 진행에는 영향이 없습니다.

### 버전 요약

| 버전 | 내용 |
| --- | --- |
| v3.3 | 지방 선택 UI 지명을 한국한자음으로 통일 |
| v3.2 | 전투/시스템/메뉴(arm9·overlay) 원문 대조 QA — 약 170건 |
| v3.1 | 오프닝 나레이션 오역 교정 |
| v3.0 | 대사 품질 QA 73건(누락·화면밀림·오역) |
| v2.9 | 대사 줄바꿈·행폭 규칙 전면 정비(3줄/18자) |
| v2.4~2.8 | 그래픽 가로줄 근본 수정, 메인메뉴·전투 화면 한글화, 가독성 개선 |
| v1.x | 초기 한글패치, 지명 통일, 아이템·스탯 레이블, 오버플로우 수정 |

---

## 6. 문제 해결

| 증상 | 원인 / 해결 |
| --- | --- |
| 패치 적용 실패 | 원본이 무수정 일본판(ATMJ)이 아님 |
| `ModuleNotFoundError: ndspy` | `python -m pip install ndspy pyxdelta` |
| 빌드 중 `전각 2바이트가 아님` | 반각 문자가 섞임 → `tools/check_rules.py`가 알려주는 문자를 전각으로 교체 |
| `너무 김: … > 예산 N B` | arm9/overlay 슬롯 초과 → 번역을 더 짧게 |
| 대사 마지막 줄이 사라짐 | 한국어 줄수가 원문보다 많음 → 줄 합치기 |
| 글자가 네모/깨짐 | KS X 1001 밖 음절 사용 |

---

## 7. 라이선스·크레딧

- 원작 © Red Company(レッド) / Hudson Soft / Sting. 이 저장소는 원작 데이터를 포함하지
  않으며, 비영리 팬 번역 목적의 도구와 번역문만 담고 있습니다.
- 코드/도구: MIT ([LICENSE](LICENSE))
- 글꼴: Galmuri11 · Galmuri14 — SIL OFL 1.1 ([tools/Galmuri-OFL-LICENSE.txt](tools/Galmuri-OFL-LICENSE.txt))
