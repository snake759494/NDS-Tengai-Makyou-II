#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_rules.py — 번역 마스터가 게임 표시 제약을 지키는지 검사한다.

  python tools/check_rules.py

검사 항목
  1) 대사창 규칙 : 한 화면 최대 3줄, 한 줄 최대 18자(전각). 마커 ｜ 는 폭에서 제외.
  2) 화면 줄수   : 한국어 줄수 ≤ 같은 화면의 일본어 줄수 (넘치면 뒤 내용이 밀려 사라짐)
  3) 인코딩      : 반각 문자 금지(전각만 출력 가능), KS X 1001 밖 한글 음절 금지
  4) arm9/오버레이 : 번역이 슬롯 바이트 한도를 넘지 않는지 (한글 1자 = 2바이트)

종료 코드 0 = 이상 없음, 1 = 위반 있음.
"""
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import narr_reflow as nr  # noqa: E402

MASTER = os.path.join(os.path.dirname(HERE), 'translation', '번역_마스터.json')
KS = os.path.join(HERE, 'ks2350.txt')
MAX_LINE = nr.MAX_LINE                    # 18
MAX_LINES = nr.MAX_LINES_PER_SCREEN       # 3

ks = set(open(KS, encoding='utf-8').read().strip())

# 의도적으로 규칙을 벗어난 화면(오탐 방지용 예외 목록)
#   yol2/ypf4/yok0 : 엔딩 스탭롤 — 전각공백 대칭 중앙정렬이라 19자가 정상
#   sdt/waa0       : 사운드 테스트 곡목 코드표 — 원문 자체가 표 형식
KNOWN_OK = {
    ('yol2.scs', 0, 0), ('yol2.scs', 2, 0), ('yol2.scs', 4, 0), ('yol2.scs', 6, 0),
    ('ypf4.scs', 0, 0), ('ypf4.scs', 2, 0), ('ypf4.scs', 4, 0), ('ypf4.scs', 6, 0),
    ('yok0.scs', 1, 0), ('yok0.scs', 3, 0), ('yok0.scs', 5, 0), ('yok0.scs', 7, 0),
    ('sdt.scs', 4, 5), ('sdt.scs', 20, 3),
    ('waa0.scs', 1, 3), ('waa0.scs', 4, 0), ('waa0.scs', 4, 1),
}


def encodable(ch):
    if ch in ks or ch in (' ', '　'):
        return True
    try:
        return len(ch.encode('shift_jis')) == 2
    except UnicodeEncodeError:
        return False


def eff(line):
    """실제 표시 폭 — 화면 전환 마커 ｜ 는 자리를 차지하지 않는다."""
    return len(line.replace('｜', ''))


def has_inline11(segs):
    """0x11 인라인 명령이 있는 엔트리는 화면 분할이 불안정 → 검사 제외."""
    for s in segs:
        if 'c' in s:
            ops = bytes.fromhex(s['c'])
            for j in range(0, len(ops), 2):
                if ops[j] == 0x11:
                    return True
    return False


def main():
    master = json.load(open(MASTER, encoding='utf-8'))
    over_lines, over_width, bad_char, over_slot = [], [], {}, []
    n_known = [0]

    # ── 대사 ───────────────────────────────────────────────
    for f in master['dialogue']['files']:
        for e in f['entries']:
            segs = e['segs']
            if not any((s.get('ko') or '').strip() for s in segs if 'jp' in s):
                continue
            for s in segs:
                for ch in (s.get('ko') or ''):
                    if ch != '\n' and not encodable(ch):
                        bad_char[ch] = bad_char.get(ch, 0) + 1
            if has_inline11(segs):
                continue
            try:
                screens = nr.split_screens_pairs(segs)
            except Exception:
                continue
            name = f['path'].split('/')[-1]
            for si, sc in enumerate(screens):
                ko = '\n'.join((l['ko'] or '') for l in sc)
                jp = '\n'.join((l['jp'] or '') for l in sc)
                if not ko.strip():
                    continue
                if (name, e['i'], si) in KNOWN_OK:
                    n_known[0] += 1
                    continue
                lines = ko.split('\n')
                jp_lines = jp.count('\n') + 1
                if len(lines) > MAX_LINES or len(lines) > jp_lines:
                    over_lines.append((name, e['i'], si, len(lines), jp_lines, ko))
                for l in lines:
                    if eff(l) > MAX_LINE:
                        over_width.append((name, e['i'], si, eff(l), l))

    # ── arm9 / overlay 슬롯 ────────────────────────────────
    def check_slots(entries, tag):
        for e in entries:
            ko = e.get('ko') or ''
            if not ko.strip():
                continue
            for ch in ko:
                if not encodable(ch):
                    bad_char[ch] = bad_char.get(ch, 0) + 1
            slot = e.get('slot')
            limit = slot - 2 if slot else len(e['jp'].encode('shift_jis'))
            if len(ko) * 2 > limit:
                over_slot.append((tag, e['off'], e['jp'], ko, len(ko) * 2, limit))

    check_slots(master['arm9']['entries'], 'arm9')
    for oid, info in master['overlay'].items():
        check_slots(info['entries'], 'ovl%s' % oid)

    # ── 보고 ───────────────────────────────────────────────
    print('=== 대사창 줄수 위반(>3줄 또는 원문보다 많음): %d ===' % len(over_lines))
    for t in over_lines[:30]:
        print('  %s e%d s%d: %d줄(원문 %d줄)  %s' % (t[0], t[1], t[2], t[3], t[4], t[5].replace('\n', ' / ')))
    print('=== 한 줄 %d자 초과: %d ===' % (MAX_LINE, len(over_width)))
    for t in over_width[:30]:
        print('  %s e%d s%d: %d자  [%s]' % t[:5])
    print('=== 슬롯 바이트 초과: %d ===' % len(over_slot))
    for t in over_slot[:30]:
        print('  %s 0x%X %r → %r  %dB > %dB' % (t[0], t[1], t[2], t[3], t[4], t[5]))
    print('=== 의도적 예외(엔딩 크레딧 정렬·코드표): %d ===' % n_known[0])
    print('=== 출력 불가 문자(반각·글꼴 없음): %d종 ===' % len(bad_char))
    if bad_char:
        print('  ', dict(sorted(bad_char.items(), key=lambda x: -x[1])[:20]))
        print('   → 반각은 전각으로 바꾸세요: , → ，   . → ．   ! → ！   ? → ？   ~ → 〜')

    bad = len(over_lines) + len(over_width) + len(over_slot) + len(bad_char)
    print('\n총 위반:', bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
