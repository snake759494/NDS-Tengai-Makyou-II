#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""patch_all.py — 메뉴 이미지(PNG) 일괄 삽입.

같은 폴더의 png/ 안에 있는 한글 메뉴 PNG들을 ROM에 써넣는다.
(메인/필드/하단 라벨, 전투 명령 아이콘, 시작 선택 화면)

PNG를 직접 수정하는 작업 흐름:
  1) python menu_extract.py 원본롬.nds png/   ← 일본어 원본을 PNG로 추출
  2) png/ 안의 그림들을 이미지 편집기로 한글로 수정
  3) python patch_all.py 입력롬.nds 출력롬.nds  ← 수정한 png/ 를 삽입

사용법:
    python patch_all.py 입력롬.nds 출력롬.nds
"""
import sys, os, subprocess

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit("[오류] 사용법: python patch_all.py 입력롬.nds 출력롬.nds")
    inp, out = sys.argv[1], sys.argv[2]
    here = os.path.dirname(os.path.abspath(__file__))
    png = os.path.join(here, "png")
    if not os.path.isdir(png):
        sys.exit(f"[오류] PNG 폴더가 없습니다: {png}\n  먼저 menu_extract.py로 PNG를 추출하세요.")
    py = sys.executable
    print("메뉴 이미지(PNG) 삽입 중...")
    subprocess.run([py, os.path.join(here, "menu_insert.py"), inp, png, out], check=True)

if __name__ == "__main__":
    main()
