# v3.4 — 이미지 한글화 재작업 및 표시 오류 수정

일본어 이미지 위에 한글을 덧씌우던 방식을 정비하고, **일본판 원본에서 이미지 리소스 169개를 다시 구성**했습니다. 아래에 **변경 이미지·선택 상태·번호별 프레임 197개 전체**를 첨부했습니다. 미니맵 106개에 있는 시설 표지 324곳도 포함합니다.

## 적용 방법

- 대상: 무수정 일본판 Nintendo DS ROM, 게임 코드 **ATMJ**.
- v3.3 등 이미 패치된 ROM이 아니라 **깨끗한 원본**에 적용하세요.
- 배포 파일: `Tengai_Makyou_II_KR_v3.4.xdelta`. 게임 ROM과 세이브는 포함하지 않습니다.

```sh
xdelta3 -d -s "Tengai Makyou II - Manji Maru (Japan).nds" Tengai_Makyou_II_KR_v3.4.xdelta "Tengai_Makyou_II_KR_v3.4.nds"
```

원본 MD5: `87e7ce48da67253fc3d70210c6fa1563`
적용 결과 MD5: `04746b727245140c90527d717ecba762`
적용 결과 SHA-256: `c6dce49289c76bdcc891ac9904f29867ff8e7534da23e94e1bbb0f1911b12383`

## 상세 변경 사항

### 메뉴·하단 버튼

- 상태·도구·주문·무구·오의·지도·작전 등 메뉴 글자를 다시 렌더링했습니다.
- 청록색 그라데이션을 없애고 해당 메뉴 글자를 단색 흰색으로 바꿨습니다.
- 하단 `명령 / 도움`은 원본에서 두 글자 영역이 기존 32픽셀 추출 구분을 가로지르는 구조였습니다. 96×16 스트립 전체를 비운 뒤 각각의 실제 위치에 다시 넣어 칸 밖으로 나가던 문제를 수정했습니다.
- 캐릭터 이름, 체·기·금·후, 사용·구입·판매·보관·찾기·버림 영역도 원문이 차지하던 칸 전체를 지운 뒤 다시 작성했습니다.
- `mainmenu.obc`의 팔레트 시작 위치를 바로잡았습니다. 팔레트는 오프셋 4부터 192바이트이며, 픽셀은 200부터 시작합니다. 예전 456 기준은 앞 장식 타일 4개를 생략한 추출 좌표였고, 전체가 헤더나 팔레트가 아니었습니다.

### 나라 지도

- 17개 지명 칸의 중심과 위쪽 경계를 원본 이미지에서 다시 측정했습니다.
- 일부 지명의 가로 위치 1~3픽셀 오차와 행별 세로 위치 차이를 수정했습니다.
- 각 칸의 11×33 내부 영역을 깨끗한 원본 바탕으로 복원하고, 두 음절을 원래의 위·아래 글자 위치에 배치했습니다. 한 음절인 `경`은 가운데에 놓았습니다.
- 한글 외의 원문 픽셀이 내부에 남지 않는지 검사하고, 칸 밖 지도·연결선·테두리 픽셀은 원본과 동일하게 유지했습니다.

### 전투 이미지

- 전투 명령 아이콘 17종과 캐릭터 이름판 4종을 재작성했습니다.
- 이름판의 체·기 영역도 독립된 16×16 칸 단위로 다시 넣었습니다.
- 번역문이 정해진 폭·높이를 넘으면 자동으로 빌드를 중단하도록 했습니다.

### 시작·저장·불러오기

- `처음 / 계속` 선택 화면과 타이틀 데모 안의 별도 사본을 모두 갱신했습니다.
- 취소·결정·삭제 버튼, 예·아니오·계속·복사·삭제의 일반/선택 상태를 갱신했습니다.
- 읽기·저장 중, 불러오기 실패, 빈 기록 검사, 삭제·덮어쓰기 확인, 읽기·저장 오류 안내 이미지를 다시 만들었습니다.
- 삭제 확인창은 1번부터 8번까지의 모든 번호 프레임을 반영했습니다.
- 스프라이트 배치 정보를 기준으로 조립하고, 여러 조각에 걸친 원문 영역을 지우되 테두리는 유지했습니다.

### 타이틀·엔딩·제작진

- 타이틀, 저장 화면의 작은 로고, 엔딩 로고에 `천외마경`을 넣었습니다. AI 편집으로 만든 로고를 원래 해상도·팔레트로 변환한 뒤 지정 영역에만 삽입했습니다.
- 원래 압축하지 않는 타일 배치 파일까지 LZ10으로 감싸던 재삽입 오류를 수정했습니다. **CMP / LZ10 / 무압축 형식을 파일별로 원본과 동일하게 유지**합니다. 이 오류가 수정 작업 중 타이틀 화면이 깨진 원인이었습니다.
- 타이틀 타일 재구성에는 뒤집기 비트를 새로 도입하지 않도록 했습니다.
- 오프닝 제작진 이미지 8화면을 번역했습니다. 두 화면이 글자 타일을 공유하는 경우 두 배치 파일을 함께 재구성했습니다.

### 미니맵

- 256×192 형식 미니맵 123개를 검사하고, 해당 표지가 있는 **106개 지도·324곳**을 교체했습니다.
- 반복되는 시설 표지는 `宿→숙`, `道→도`, `武→무`, `預→창`, `茶→차`, `雑→잡`으로 표시했습니다.
- 원본 글자 비트맵과 배경색을 함께 대조한 위치만 교체했습니다. 글자 영역을 먼저 지우고 원래 팔레트와 주변 테두리를 유지했습니다.
- 교체 후 해당 6종의 원문 표지 비트맵이 남아 있지 않은지 검사했습니다. 이 검사가 게임의 모든 일본어 이미지 부재를 보증하는 것은 아닙니다.

### 기존 번역 및 빌드

- 대사·시스템 텍스트·한글 폰트는 v3.3을 유지했습니다. 이번 버전은 이미지 표시 개선이 중심입니다.
- `DEPLOY.py`가 새로운 리소스 목록을 읽어 이미지 169개와 한글 폰트 1개, 총 170개 파일을 가져오도록 수정했습니다. 이전 37개 목록 때문에 재빌드 때 새 이미지가 빠지는 문제를 방지합니다.
- 원본 추출·장면 조사·이미지 재조립·전체 이미지 내보내기 도구와 리소스 목록을 소스에 포함했습니다.

## 검증 범위와 남은 사항

- 모든 수정 리소스의 압축 해제 길이를 원본과 대조하고, 저장한 ROM을 다시 읽어 삽입 데이터를 확인했습니다.
- 글자 폭·높이 검사 161건, 원래 타일 용량 검사, 타일맵 재구성 검사를 통과했습니다.
- 수정 대상 외 파일과 ARM9/ARM7 데이터가 v3.3 참조본과 동일한지 확인했습니다.
- `원본 + v3.4 xdelta` 결과와 시험 ROM이 바이트 단위로 동일합니다.
- `DEPLOY.py` 재빌드 결과도 같은 ROM과 바이트 단위로 동일합니다.
- **타이틀·메뉴·나라 지도는 사용자 게임 실행 확인을 받았습니다.**
- 전체 게임 플레이, 모든 전투·저장 오류 상황·엔딩 장면의 실행 검증은 완료하지 않았습니다. 일부 미분류 이미지와 메인메뉴 내장 버튼의 조립 구조 조사는 남아 있습니다. 이 릴리즈는 모든 일본어 이미지의 제거 완료를 의미하지 않습니다.
- 아래 이미지는 ROM에서 추출·조립한 검토용 이미지입니다. 전투 글자는 흰색 검토 팔레트로 표시했으며, 투명 영역·선택 효과·장면 합성 때문에 게임 화면과 배경색이 다를 수 있습니다.

## 첨부 파일

| 파일 | 내용 |
|---|---|
| `Tengai_Makyou_II_KR_v3.4.xdelta` | 원본 일본판에 적용하는 패치 |
| `tm2-kr-v3.4-all-images.zip` | PNG 197개, 전체 이미지 목록, 오프라인 열람용 index.html, 분류별 모음 7장 |
| `verification.json` | 리소스별 경로·압축 형식·글자 검사·지도 교체 위치·검증 결과 |
| `SHA256SUMS.txt` | 배포 첨부 파일의 SHA-256 |
| `release-notes-v3.4.md` | 이 상세 릴리즈 노트 |
| `01-menus.png` ~ `07-minimaps.png` | 분류별 전체 이미지 모음 |

## 변경 이미지 전체

각 분류를 펼치면 개별 PNG를 전부 볼 수 있습니다. 선택 상태와 1~8번 삭제 확인창은 별도 프레임으로 첨부했습니다.

<details>
<summary>메뉴 — 28개</summary>

**하단 명령 / 도움** · 96×16 · FID 2766

![하단 명령 / 도움](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/footer.png)

**닫기** · 32×16 · FID 2766

![닫기](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_51.png)

**판매** · 32×16 · FID 2766

![판매](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_52.png)

**목록** · 32×16 · FID 2766

![목록](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_53.png)

**상태** · 32×16 · FID 2766

![상태](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_54.png)

**도구** · 32×16 · FID 2766

![도구](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_55.png)

**주문** · 32×16 · FID 2766

![주문](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_56.png)

**무구** · 32×16 · FID 2766

![무구](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_57.png)

**오의** · 32×16 · FID 2766

![오의](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_58.png)

**포격** · 32×16 · FID 2766

![포격](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_60.png)

**순이** · 32×16 · FID 2766

![순이](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_61.png)

**지도** · 32×16 · FID 2766

![지도](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_62.png)

**모드** · 32×16 · FID 2766

![모드](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_63.png)

**작전** · 32×16 · FID 2766

![작전](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_64.png)

**만지** · 32×16 · FID 2766

![만지](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_65.png)

**카부키** · 32×16 · FID 2766

![카부키](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_66.png)

**극락** · 32×16 · FID 2766

![극락](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_67.png)

**키누** · 32×16 · FID 2766

![키누](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_68.png)

**체** · 16×16 · FID 2766

![체](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_552.png)

**기** · 16×16 · FID 2766

![기](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_556.png)

**금** · 16×16 · FID 2766

![금](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_560.png)

**후** · 16×16 · FID 2766

![후](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_564.png)

**사용** · 48×16 · FID 2766

![사용](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_648.png)

**구입** · 48×16 · FID 2766

![구입](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_660.png)

**판매** · 48×16 · FID 2766

![판매](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_672.png)

**보관** · 48×16 · FID 2766

![보관](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_684.png)

**찾기** · 48×16 · FID 2766

![찾기](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_696.png)

**버림** · 48×16 · FID 2766

![버림](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/menu_708.png)

</details>

<details>
<summary>전투 — 21개</summary>

**공격** · 32×16 · FID 3940

![공격](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_01.png)

**검법** · 32×16 · FID 3949

![검법](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_02.png)

**돌파** · 32×16 · FID 3950

![돌파](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_03.png)

**주문** · 32×16 · FID 3951

![주문](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_04.png)

**자세** · 32×16 · FID 3952

![자세](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_05.png)

**작전** · 32×16 · FID 3953

![작전](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_06.png)

**무구** · 32×16 · FID 3954

![무구](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_07.png)

**도구** · 32×16 · FID 3955

![도구](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_08.png)

**?** · 32×16 · FID 3956

![?](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_09.png)

**비술** · 32×16 · FID 3941

![비술](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_10.png)

**체술** · 32×16 · FID 3942

![체술](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_11.png)

**귀도** · 32×16 · FID 3943

![귀도](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_12.png)

**포격** · 32×16 · FID 3944

![포격](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_13.png)

**공격** · 32×16 · FID 3945

![공격](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_14.png)

**화염** · 32×16 · FID 3946

![화염](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_15.png)

**어뢰** · 32×16 · FID 3947

![어뢰](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_16.png)

**열탄** · 32×16 · FID 3948

![열탄](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/command_17.png)

**만지 / 체 / 기** · 32×32 · FID 3966

![만지 / 체 / 기](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/name_3966.png)

**카부키 / 체 / 기** · 32×32 · FID 3967

![카부키 / 체 / 기](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/name_3967.png)

**극락 / 체 / 기** · 32×32 · FID 3968

![극락 / 체 / 기](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/name_3968.png)

**키누 / 체 / 기** · 32×32 · FID 3969

![키누 / 체 / 기](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/name_3969.png)

</details>

<details>
<summary>주요 화면 — 6개</summary>

**나라 지도** · 256×192 · FID 2764

![나라 지도](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/provinces.png)

**타이틀** · 256×256 · FID 12602, 12604

![타이틀](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/title.png)

**처음 / 계속** · 256×256 · FID 9140, 9143

![처음 / 계속](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/kiten.png)

**타이틀 데모의 처음 / 계속** · 256×256 · FID 12629, 12631

![타이틀 데모의 처음 / 계속](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/kiten_demo.png)

**저장 화면 배경 로고** · 256×256 · FID 9202, 9204

![저장 화면 배경 로고](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_logo.png)

**엔딩 로고 / 효과 타일** · 256×256 · FID 4592

![엔딩 로고 / 효과 타일](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/ending.png)

</details>

<details>
<summary>제작진 — 8개</summary>

**기획·감수** · 256×256 · FID 11715, 11717

![기획·감수](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/staff_11717.png)

**음악** · 256×256 · FID 11724, 11726

![음악](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/staff_11726.png)

**원화** · 256×256 · FID 11732, 11734

![원화](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/staff_11734.png)

**원작 제작진** · 256×256 · FID 11740, 11742

![원작 제작진](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/staff_11742.png)

**원작·음악** · 256×256 · FID 11752, 11754

![원작·음악](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/staff_11754.png)

**성우 1** · 256×256 · FID 11763, 11765

![성우 1](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/staff_11765.png)

**성우 2** · 256×256 · FID 11771, 11773

![성우 2](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/staff_11773.png)

**특별 출연** · 256×256 · FID 11771, 11774

![특별 출연](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/staff_11774.png)

</details>

<details>
<summary>저장·불러오기 — 28개</summary>

**취소** · 64×18 · FID 9161

![취소](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9161_0.png)

**결정** · 64×32 · FID 9163

![결정](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9163_0.png)

**삭제** · 64×32 · FID 9165

![삭제](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9165_0.png)

**예 (1/2)** · 40×16 · FID 9168

![예 (1/2)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9168_0.png)

**예 (2/2)** · 40×16 · FID 9168

![예 (2/2)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9168_1.png)

**아니오 (1/2)** · 40×16 · FID 9170

![아니오 (1/2)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9170_0.png)

**아니오 (2/2)** · 40×16 · FID 9170

![아니오 (2/2)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9170_1.png)

**계속 (1/2)** · 40×16 · FID 9172

![계속 (1/2)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9172_0.png)

**계속 (2/2)** · 40×16 · FID 9172

![계속 (2/2)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9172_1.png)

**복사 (1/2)** · 40×16 · FID 9174

![복사 (1/2)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9174_0.png)

**복사 (2/2)** · 40×16 · FID 9174

![복사 (2/2)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9174_1.png)

**삭제 (1/2)** · 40×16 · FID 9176

![삭제 (1/2)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9176_0.png)

**삭제 (2/2)** · 40×16 · FID 9176

![삭제 (2/2)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9176_1.png)

**파일 읽는 중** · 192×80 · FID 9186

![파일 읽는 중](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9186_0.png)

**불러오기 실패** · 192×80 · FID 9188

![불러오기 실패](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9188_0.png)

**기록이 비어 있지 않음** · 192×80 · FID 9190

![기록이 비어 있지 않음](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9190_0.png)

**기록 삭제 확인 (1/8)** · 192×80 · FID 9192

![기록 삭제 확인 (1/8)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9192_0.png)

**기록 삭제 확인 (2/8)** · 192×80 · FID 9192

![기록 삭제 확인 (2/8)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9192_1.png)

**기록 삭제 확인 (3/8)** · 192×80 · FID 9192

![기록 삭제 확인 (3/8)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9192_2.png)

**기록 삭제 확인 (4/8)** · 192×80 · FID 9192

![기록 삭제 확인 (4/8)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9192_3.png)

**기록 삭제 확인 (5/8)** · 192×80 · FID 9192

![기록 삭제 확인 (5/8)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9192_4.png)

**기록 삭제 확인 (6/8)** · 192×80 · FID 9192

![기록 삭제 확인 (6/8)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9192_5.png)

**기록 삭제 확인 (7/8)** · 192×80 · FID 9192

![기록 삭제 확인 (7/8)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9192_6.png)

**기록 삭제 확인 (8/8)** · 192×80 · FID 9192

![기록 삭제 확인 (8/8)](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9192_7.png)

**덮어쓰기 확인** · 192×80 · FID 9194

![덮어쓰기 확인](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9194_0.png)

**저장 중** · 192×80 · FID 9196

![저장 중](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9196_0.png)

**읽기 오류** · 192×80 · FID 9198

![읽기 오류](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9198_0.png)

**저장 오류** · 192×80 · FID 9200

![저장 오류](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/save_9200_0.png)

</details>

<details>
<summary>미니맵 — 106개</summary>

**waa0 · 1곳** · 256×192 · FID 2796

![waa0 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2796.png)

**wab0 · 6곳** · 256×192 · FID 2797

![wab0 · 6곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2797.png)

**wab2 · 6곳** · 256×192 · FID 2799

![wab2 · 6곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2799.png)

**wac0 · 1곳** · 256×192 · FID 2800

![wac0 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2800.png)

**wai0 · 1곳** · 256×192 · FID 2804

![wai0 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2804.png)

**waq0 · 2곳** · 256×192 · FID 2805

![waq0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2805.png)

**wba0 · 7곳** · 256×192 · FID 2806

![wba0 · 7곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2806.png)

**wbb0 · 3곳** · 256×192 · FID 2807

![wbb0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2807.png)

**wbe0 · 1곳** · 256×192 · FID 2808

![wbe0 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2808.png)

**wbe1 · 1곳** · 256×192 · FID 2809

![wbe1 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2809.png)

**wbg0 · 4곳** · 256×192 · FID 2810

![wbg0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2810.png)

**wca0 · 1곳** · 256×192 · FID 2811

![wca0 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2811.png)

**wcb0 · 4곳** · 256×192 · FID 2812

![wcb0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2812.png)

**wcb1 · 4곳** · 256×192 · FID 2813

![wcb1 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2813.png)

**wcd0 · 2곳** · 256×192 · FID 2814

![wcd0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2814.png)

**wce0 · 5곳** · 256×192 · FID 2815

![wce0 · 5곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2815.png)

**wcq0 · 2곳** · 256×192 · FID 2818

![wcq0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2818.png)

**wcq1 · 2곳** · 256×192 · FID 2819

![wcq1 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2819.png)

**wcr0 · 2곳** · 256×192 · FID 2820

![wcr0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2820.png)

**wda0 · 3곳** · 256×192 · FID 2821

![wda0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2821.png)

**wdb0 · 3곳** · 256×192 · FID 2822

![wdb0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2822.png)

**wde0 · 3곳** · 256×192 · FID 2823

![wde0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2823.png)

**wdf0 · 4곳** · 256×192 · FID 2824

![wdf0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2824.png)

**wdi0 · 5곳** · 256×192 · FID 2825

![wdi0 · 5곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2825.png)

**wdj0 · 4곳** · 256×192 · FID 2826

![wdj0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2826.png)

**wdj0a · 4곳** · 256×192 · FID 2827

![wdj0a · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2827.png)

**wdp0 · 3곳** · 256×192 · FID 2828

![wdp0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2828.png)

**wee0 · 8곳** · 256×192 · FID 2830

![wee0 · 8곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2830.png)

**weh0 · 2곳** · 256×192 · FID 2833

![weh0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2833.png)

**wei0 · 2곳** · 256×192 · FID 2834

![wei0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2834.png)

**weo0 · 2곳** · 256×192 · FID 2835

![weo0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2835.png)

**wep0 · 2곳** · 256×192 · FID 2836

![wep0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2836.png)

**weq0 · 1곳** · 256×192 · FID 2837

![weq0 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2837.png)

**wer0 · 2곳** · 256×192 · FID 2838

![wer0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2838.png)

**wfa0 · 4곳** · 256×192 · FID 2839

![wfa0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2839.png)

**wfa0a · 4곳** · 256×192 · FID 2840

![wfa0a · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2840.png)

**wfj0 · 2곳** · 256×192 · FID 2841

![wfj0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2841.png)

**wfk0 · 2곳** · 256×192 · FID 2842

![wfk0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2842.png)

**wfl0 · 2곳** · 256×192 · FID 2843

![wfl0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2843.png)

**wfp0 · 2곳** · 256×192 · FID 2844

![wfp0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2844.png)

**wfq0 · 2곳** · 256×192 · FID 2845

![wfq0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2845.png)

**wfs0 · 6곳** · 256×192 · FID 2847

![wfs0 · 6곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2847.png)

**wft0 · 2곳** · 256×192 · FID 2848

![wft0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2848.png)

**wfu0 · 2곳** · 256×192 · FID 2849

![wfu0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2849.png)

**wga0 · 3곳** · 256×192 · FID 2850

![wga0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2850.png)

**wgb0 · 2곳** · 256×192 · FID 2852

![wgb0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2852.png)

**wgd0 · 4곳** · 256×192 · FID 2853

![wgd0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2853.png)

**wgn0 · 6곳** · 256×192 · FID 2854

![wgn0 · 6곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2854.png)

**wgq0 · 2곳** · 256×192 · FID 2855

![wgq0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2855.png)

**wgs0 · 6곳** · 256×192 · FID 2856

![wgs0 · 6곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2856.png)

**wgs0a · 6곳** · 256×192 · FID 2857

![wgs0a · 6곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2857.png)

**wgt0 · 2곳** · 256×192 · FID 2858

![wgt0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2858.png)

**whb0 · 4곳** · 256×192 · FID 2859

![whb0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2859.png)

**whc0 · 1곳** · 256×192 · FID 2860

![whc0 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2860.png)

**whn0 · 6곳** · 256×192 · FID 2861

![whn0 · 6곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2861.png)

**whn0a · 6곳** · 256×192 · FID 2862

![whn0a · 6곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2862.png)

**xia0 · 4곳** · 256×192 · FID 2865

![xia0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2865.png)

**xib0 · 2곳** · 256×192 · FID 2866

![xib0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2866.png)

**xie0 · 1곳** · 256×192 · FID 2867

![xie0 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2867.png)

**xjb0 · 4곳** · 256×192 · FID 2868

![xjb0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2868.png)

**xjb1a · 4곳** · 256×192 · FID 2870

![xjb1a · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2870.png)

**xjb2 · 4곳** · 256×192 · FID 2871

![xjb2 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2871.png)

**xjc0 · 4곳** · 256×192 · FID 2872

![xjc0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2872.png)

**xjc1a · 4곳** · 256×192 · FID 2874

![xjc1a · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2874.png)

**xjc2 · 4곳** · 256×192 · FID 2875

![xjc2 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2875.png)

**xjd0 · 2곳** · 256×192 · FID 2876

![xjd0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2876.png)

**xji0 · 1곳** · 256×192 · FID 2877

![xji0 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2877.png)

**xjs0 · 2곳** · 256×192 · FID 2878

![xjs0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2878.png)

**xju0 · 2곳** · 256×192 · FID 2879

![xju0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2879.png)

**xkb0 · 3곳** · 256×192 · FID 2880

![xkb0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2880.png)

**xkb1a · 3곳** · 256×192 · FID 2882

![xkb1a · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2882.png)

**xkc0 · 4곳** · 256×192 · FID 2883

![xkc0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2883.png)

**xkc1a · 4곳** · 256×192 · FID 2885

![xkc1a · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2885.png)

**xkh0 · 3곳** · 256×192 · FID 2886

![xkh0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2886.png)

**xkp0 · 2곳** · 256×192 · FID 2887

![xkp0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2887.png)

**xkq0 · 2곳** · 256×192 · FID 2888

![xkq0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2888.png)

**xkr0 · 2곳** · 256×192 · FID 2889

![xkr0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2889.png)

**xla0 · 2곳** · 256×192 · FID 2890

![xla0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2890.png)

**xlc0 · 3곳** · 256×192 · FID 2891

![xlc0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2891.png)

**xle0 · 3곳** · 256×192 · FID 2892

![xle0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2892.png)

**xlf0 · 2곳** · 256×192 · FID 2893

![xlf0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2893.png)

**xlh0 · 3곳** · 256×192 · FID 2894

![xlh0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2894.png)

**xlp0 · 2곳** · 256×192 · FID 2895

![xlp0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2895.png)

**xmf0 · 4곳** · 256×192 · FID 2896

![xmf0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2896.png)

**xmr0 · 2곳** · 256×192 · FID 2899

![xmr0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2899.png)

**xms0 · 2곳** · 256×192 · FID 2900

![xms0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2900.png)

**xmy0 · 2곳** · 256×192 · FID 2901

![xmy0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2901.png)

**yna0 · 4곳** · 256×192 · FID 2902

![yna0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2902.png)

**ynb0 · 2곳** · 256×192 · FID 2903

![ynb0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2903.png)

**ync0 · 6곳** · 256×192 · FID 2904

![ync0 · 6곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2904.png)

**ynr0 · 2곳** · 256×192 · FID 2907

![ynr0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2907.png)

**yns0 · 2곳** · 256×192 · FID 2908

![yns0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2908.png)

**ynu0 · 5곳** · 256×192 · FID 2909

![ynu0 · 5곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2909.png)

**yoa0 · 2곳** · 256×192 · FID 2910

![yoa0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2910.png)

**yob0 · 4곳** · 256×192 · FID 2911

![yob0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2911.png)

**yoc0 · 1곳** · 256×192 · FID 2912

![yoc0 · 1곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2912.png)

**yoo0 · 2곳** · 256×192 · FID 2913

![yoo0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2913.png)

**yop0 · 2곳** · 256×192 · FID 2914

![yop0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2914.png)

**yoy0 · 2곳** · 256×192 · FID 2915

![yoy0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2915.png)

**ypa0 · 3곳** · 256×192 · FID 2916

![ypa0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2916.png)

**ypc0 · 4곳** · 256×192 · FID 2918

![ypc0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2918.png)

**ypc1a · 4곳** · 256×192 · FID 2920

![ypc1a · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2920.png)

**ypd0 · 3곳** · 256×192 · FID 2921

![ypd0 · 3곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2921.png)

**yqa0 · 5곳** · 256×192 · FID 2922

![yqa0 · 5곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2922.png)

**yqb0 · 4곳** · 256×192 · FID 2923

![yqb0 · 4곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2923.png)

**yql0 · 2곳** · 256×192 · FID 2924

![yql0 · 2곳](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/images/map_2924.png)

</details>

## 한눈에 보는 전체 모음

![01-menus](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/01-menus.png)

![02-screens](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/02-screens.png)

![03-save](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/03-save.png)

![04-staff](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/04-staff.png)

![05-minimaps](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/05-minimaps.png)

![06-minimaps](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/06-minimaps.png)

![07-minimaps](https://raw.githubusercontent.com/snake759494/NDS-Tengai-Makyou-II/v3.4/docs/releases/v3.4/07-minimaps.png)
