#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""master_split_merge.py — 번역 마스터 ↔ 3개 원본 파일 상호 변환.

마스터(`translation/번역_마스터.json`)는 dialogue / arm9 / overlay 세 섹션을 한 파일에
합친 것이다. 예전 도구나 외부 편집기가 개별 파일을 요구할 때 쓴다.

  python tools/master_split_merge.py split          # 마스터 → translation/_split/*.json
  python tools/master_split_merge.py merge          # translation/_split/*.json → 마스터
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.join(os.path.dirname(HERE), 'translation')
MASTER = os.path.join(TR, '번역_마스터.json')
SPLIT = os.path.join(TR, '_split')
PARTS = {'dialogue': 'translation.json',
         'arm9': 'arm9_translation.json',
         'overlay': 'overlay_translation.json'}

README = ('천외마경II 卍MARU 한국어 패치 — 텍스트 번역 마스터. '
          '이 파일만 수정하고 `python DEPLOY.py --jp 원본.nds` 를 실행하면 패치가 다시 만들어집니다. '
          'dialogue=게임 내 대사(각 seg 의 "ko" 를 수정, "jp" 는 원문이라 건드리지 말 것), '
          'arm9=시스템/메뉴/지명 텍스트(entries[].ko), '
          'overlay=오프닝 자막·저장 UI·전투 커맨드(entries[].ko). '
          '규칙: 한 대사창 최대 3줄, 한 줄 최대 18자(전각), 반각 문자 불가(~ 는 〜). '
          '수정 후 `python tools/check_rules.py` 로 검사하세요. '
          '지도/메인메뉴/전투 이미지는 픽셀 그래픽이라 이 파일 대상이 아닙니다.')


def split():
    master = json.load(open(MASTER, encoding='utf-8'))
    os.makedirs(SPLIT, exist_ok=True)
    for key, fn in PARTS.items():
        p = os.path.join(SPLIT, fn)
        json.dump(master[key], open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('쓰기:', p, format(os.path.getsize(p), ','), 'B')


def merge():
    out = {'_README': README}
    for key, fn in PARTS.items():
        p = os.path.join(SPLIT, fn)
        if not os.path.exists(p):
            raise SystemExit('없음: %s (먼저 split 하세요)' % p)
        out[key] = json.load(open(p, encoding='utf-8'))
    json.dump(out, open(MASTER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('마스터 갱신:', MASTER, format(os.path.getsize(MASTER), ','), 'B')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'split':
        split()
    elif cmd == 'merge':
        merge()
    else:
        print(__doc__)
        sys.exit(1)
