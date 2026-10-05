# 이미지 재작업 도구 (v3.4)

배포 이미지와 상세 변경 내역은 [v3.4 릴리즈 노트](../../docs/releases/v3.4/README.md)를 참조합니다.

## 일반 재빌드

저장소 루트에서 `python DEPLOY.py --jp 원본.nds`를 실행하면 최신 dist 패치에서 이미지·폰트 170개 파일을 가져오고 번역 마스터를 적용합니다. v3.4 공개 전 결과 MD5 `04746b727245140c90527d717ecba762`와 바이트 동일함을 확인했습니다.

## 원본부터 이미지 재구성

```sh
python -m pip install ndspy numpy Pillow pyxdelta
python tools/images/audit_graphics.py 원본.nds build/original-images
python tools/images/rebuild_graphics.py --jp 원본.nds --reference v3.3참조.nds --outdir build/image-rebuild
python tools/images/export_review_gallery.py build/image-rebuild/Tengai_Makyou_II_KR_image_rework.nds build/image-rebuild/verification.json build/image-gallery
```

참조 ROM은 깨끗한 일본판에 저장소의 v3.3 xdelta를 적용해 준비합니다. 이미지 재구성 도구는 그 참조본의 대사·폰트·실행 코드를 유지하고 지정 리소스만 교체합니다. 원본 SHA-256은 `f52b0c585eaf2cf8d08336db3bce8291255ca48d532f6504e003cc75ab9cfc24`로 고정합니다.

- `rebuilt_resources.json`: 배포 빌드가 보존해야 하는 이미지 리소스 169개.
- `rebuild_graphics.py`: 원본 영역 삭제, 한글 렌더링, 타일·맵 재구성, 형식 보존, 재읽기 검증.
- `minimap_signs.py`: 원본 시설 표지 6종의 비트맵 대조 및 교체.
- `audit_graphics.py`: 파일 목록과 저장 UI의 스프라이트 조립 결과 추출.
- `audit_scenes.py`: 장면 타일맵 조사용 추정 추출기. 자동 추정 결과는 시각 확인이 필요하며, 그 결과 자체가 패치 대상이나 검증 완료를 뜻하지 않습니다.
- `export_review_gallery.py`: 실제 수정 ROM에서 모든 대상 리소스를 다시 읽어 PNG·목록·갤러리·ZIP을 만듭니다. 검토 시트의 한글 라벨에 Windows `malgun.ttf`를 사용합니다.

원본 파일의 CMP/LZ10/무압축 구분과 해제 후 길이를 유지해야 합니다. 무압축 `.cscr`을 LZ10으로 감싸면 오프라인 디코더에서 복원되어도 게임에서는 깨집니다. 타일 용량을 초과하거나 글자가 영역에 들어가지 않으면 축소·잘라내기로 숨기지 않고 실패하도록 했습니다.

나라 지도는 칸 중심/위쪽 경계를 기준으로 글자 영역을 정의합니다. 하단 명령·도움은 기존 32픽셀 추출 단위와 실제 라벨 경계가 다르므로 하나의 스트립에서 배치한 뒤 나눕니다. 저장 UI는 `.ani`의 스프라이트 구성과 모든 번호·선택 프레임을 함께 확인해야 합니다.

## 로고 자산 제작

`assets/*_ko_generated.png`는 ImageGen의 **기존 이미지 편집 모드**로 만든 중간 자산입니다. 빌드 시 원래 크기로 변환하고 원본 팔레트에 양자화한 뒤 지정된 로고 영역만 가져옵니다. 나머지 그림은 일본판 원본에서 유지합니다.

- `title_ko_generated.png`: 원본 타이틀의 중앙 `天外魔境`만 `천외마경`으로 바꾸고 짙은 파랑 글자, 밝은 가장자리, 로마 숫자 II와 영문·저작권 표기를 유지하도록 지시.
- `save_logo_ko_generated.png`: 저장 화면 오른쪽 아래의 작은 제목만 같은 한글로 바꾸고 청록·파랑 및 크림색 외곽선, 배경 삽화와 II를 유지하도록 지시.
- `ending_logo_ko_generated.png`: 엔딩 타일 시트 왼쪽 위 96×48 로고만 한글로 바꾸고 파란 픽셀 글자와 II, 그 밖의 효과 그림을 유지하도록 지시.

이미지 추출·재조립 검증과 게임 실행 검증은 별개입니다. v3.4에서 사용자 실행 확인을 받은 범위는 타이틀·메뉴·나라 지도이며, 전체 플레이·모든 장면 검증은 완료하지 않았습니다.
