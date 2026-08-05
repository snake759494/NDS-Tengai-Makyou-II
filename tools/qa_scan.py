#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qa_scan.py — 번역 품질 점검 후보를 뽑는다(원문 대조가 필요한 곳 찾기).

  python tools/qa_scan.py                 # 요약 + 상위 사례
  python tools/qa_scan.py --out cand.json # 후보 전체를 JSON 으로 저장

규칙 검사(`check_rules.py`)로는 못 잡는 유형을 찾기 위한 도구다. 번역이 원문보다 길어
내용이 밀려 사라진 경우, 결과물 자체는 3줄/18자를 지키므로 규칙 검사를 통과한다.

찾는 것
  untranslated : 원문은 있는데 번역이 비어 있음
  truncated    : 엔트리 마지막 화면이 조사·연결어미로 끝나 문장이 잘린 듯함
  short        : 화면 글자수 비(한국어/일본어)가 낮아 내용 누락이 의심됨

여기서 나온 목록은 "의심 후보"일 뿐이다. 한국어가 원문보다 짧은 것 자체는 정상인 경우가
많으므로, 실제 판정은 원문과 나란히 놓고 사람이(또는 번역 검토 도구가) 확인해야 한다.
"""
import argparse
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import narr_reflow as nr  # noqa: E402

MASTER = os.path.join(os.path.dirname(HERE), 'translation', '번역_마스터.json')

# 문장이 끝나지 않은 채 잘린 듯한 꼬리(조사·관형형·연결어미)
DANGLING = re.compile(
    r'(을|를|이|가|은|는|의|에|와|과|도|로|으로|에서|에게|한테|께|부터|까지|보다|처럼|'
    r'라고|하고|며|면서|서|어서|아서|려고|거나|든지|지만|는데|은데|ㄴ데)$')
# 정상 종결로 볼 만한 꼬리
TERMINAL = re.compile(
    r'(다|요|까|네|지|야|라|오|소|군|대|자|나|래|어|아|워|줘|봐|해|마|니|세|렴|죠)$')
END_PUNC = tuple('！？…。．!?」』）)♀♂〜ー・♪')


def strip_marks(s):
    return (s or '').replace('｜', '').replace('　', ' ').strip()


def clen(s):
    return len(strip_marks(s).replace(' ', ''))


def has_inline11(segs):
    for s in segs:
        if 'c' in s:
            ops = bytes.fromhex(s['c'])
            for j in range(0, len(ops), 2):
                if ops[j] == 0x11:
                    return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None, help='후보 전체를 저장할 JSON 경로')
    ap.add_argument('--ratio', type=float, default=0.62,
                    help='내용부족 판정 기준 (한국어/일본어 글자수 비, 기본 0.62)')
    a = ap.parse_args()

    master = json.load(open(MASTER, encoding='utf-8'))
    cands = []
    n_entry = 0
    # 대사가 아니라 목록·표인 파일(아이템명·지명·워프표·사운드테스트)은 문장 규칙이 다르다
    SKIP_FILES = {'chimei.scs', 'warp_seg.scs', 'sdt.scs'}
    for f in master['dialogue']['files']:
        name = f['path'].split('/')[-1]
        if name in SKIP_FILES or '/set/' in f['path']:
            continue
        for e in f['entries']:
            segs = e['segs']
            jp_any = any((s.get('jp') or '').strip() for s in segs)
            ko_any = any((s.get('ko') or '').strip() for s in segs if 'jp' in s)
            if not jp_any:
                continue
            if not ko_any:
                cands.append({'file': name, 'i': e['i'], 'kind': 'untranslated',
                              'jp': ''.join(s.get('jp') or '' for s in segs)[:60], 'ko': ''})
                continue
            n_entry += 1
            if has_inline11(segs):
                continue
            try:
                screens = nr.split_screens_pairs(segs)
            except Exception:
                continue
            if not screens:
                continue

            jp_len = sum(clen('\n'.join((l['jp'] or '') for l in sc)) for sc in screens)
            ko_len = sum(clen('\n'.join((l['ko'] or '') for l in sc)) for sc in screens)

            # 마지막 화면이 미완결로 끝나는가
            last = screens[-1]
            ko_last = strip_marks('\n'.join((l['ko'] or '') for l in last))
            jp_last = strip_marks('\n'.join((l['jp'] or '') for l in last))
            if ko_last and jp_last and jp_len >= 8:
                tail = ko_last.split(' ')[-1].rstrip(''.join(END_PUNC))
                if (tail and DANGLING.search(tail) and not TERMINAL.search(ko_last)
                        and not ko_last.endswith(END_PUNC)):
                    cands.append({'file': name, 'i': e['i'], 'kind': 'truncated',
                                  'jp': jp_last, 'ko': ko_last})
                    continue
            if jp_len >= 8 and ko_len / max(1, jp_len) < a.ratio:
                cands.append({'file': name, 'i': e['i'], 'kind': 'short',
                              'ratio': round(ko_len / max(1, jp_len), 2),
                              'jp': jp_last, 'ko': ko_last})

    from collections import Counter
    kinds = Counter(c['kind'] for c in cands)
    print('검사한 번역 엔트리: %d' % n_entry)
    print('점검 후보: %d  %s' % (len(cands), dict(kinds)))
    for kind in ('untranslated', 'truncated', 'short'):
        sample = [c for c in cands if c['kind'] == kind][:5]
        if not sample:
            continue
        print('\n=== %s (상위 %d) ===' % (kind, len(sample)))
        for c in sample:
            print('  %s e%s' % (c['file'], c['i']))
            print('     JP: %s' % c['jp'].replace('\n', ' / ')[:70])
            print('     KO: %s' % c['ko'].replace('\n', ' / ')[:70])
    if a.out:
        json.dump(cands, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('\n저장:', a.out)


if __name__ == '__main__':
    main()
