#!/usr/bin/env python3
"""
font_mapping.py  —  SJIS 한자 ↔ 글리프 슬롯 ↔ 한글 매핑
========================================================
슈퍼로봇대전J 방식의 핵심. 한글 음절을 '한자 글리프 슬롯'에 덮어 그리고,
대사에는 그 한자의 SJIS 코드를 넣어 화면에 한글이 나오게 한다.

[검증된 규칙]
  - 폰트 글리프는 **SJIS 코드 순서**로 배열됨(JIS 구·점 밀집순 아님).
  - 亜(SJIS 0x889F) = 글리프 **슬롯 1418**(=non_blank_slots[0]).
  - 중간중간 **빈칸(두부 placeholder)** 이 불규칙하게 끼어 있고(예: 슬롯 1575,
    1764, 1953 …), 두부 템플릿은 슬롯 1410. 빈칸은 코드를 소비하지 않는
    '여분'(Model A)이므로 **건너뛴다**:
        non_blank_slots[k]  ↔  valid_sjis_codes[k]
  - 앵커 확인: 亜=1418, 円(0x897E)=1574, 園(0x8980)=1576(빈칸 1575 스킵),
    蛙(0x8A5E)=1731, 救(0x8B7E)=1952. 랭크 0/300/.../2349 전부 일치.

[사용]
    glyphs = decode_font(raw)                       # tengai_cobj_font
    hangul = list(open('ks2350.txt').read().strip())
    m = build_mapping(glyphs, hangul)
    m.syl2slot['가']  -> 1418   (이 슬롯에 '가' 글리프를 그린다)
    m.syl2sjis['가']  -> 0x889F (대사에 이 SJIS 코드를 넣는다)
"""
from dataclasses import dataclass, field
import numpy as np

KANJI_START_SJIS = 0x889F     # 亜
KANJI_START_SLOT = 1418       # non_blank_slots[0]
PLACEHOLDER_SLOT = 1410       # 두부 템플릿


def gen_valid_sjis(count: int, start: int = KANJI_START_SJIS):
    """0x889F(亜)부터 SJIS 코드 순서로 '유효한 한자' 코드 count 개."""
    out = []
    for lead in list(range(0x88, 0xA0)) + list(range(0xE0, 0xF0)):
        for trail in range(0x40, 0xFD):
            if trail == 0x7F:                       # SJIS 트레일 0x7F 없음
                continue
            code = (lead << 8) | trail
            if code < start:
                continue
            try:
                ch = bytes([lead, trail]).decode('shift_jis')
            except UnicodeDecodeError:
                continue
            if len(ch) == 1 and '\u4E00' <= ch <= '\u9FFF':
                out.append(code)
                if len(out) >= count:
                    return out
    return out


def _is_blank(glyph: np.ndarray, placeholder: np.ndarray | None) -> bool:
    if int(glyph.sum()) == 0:
        return True
    if placeholder is not None and np.array_equal(glyph, placeholder):
        return True
    return False


def find_nonblank_slots(glyphs: np.ndarray, count: int,
                        start_slot: int = KANJI_START_SLOT,
                        placeholder_slot: int = PLACEHOLDER_SLOT):
    """start_slot 부터 빈칸(전부 0 또는 두부 템플릿)을 건너뛰며 비어있지 않은
    한자 슬롯을 count 개 모은다."""
    placeholder = glyphs[placeholder_slot] if 0 <= placeholder_slot < len(glyphs) else None
    slots, s = [], start_slot
    while len(slots) < count and s < len(glyphs):
        if not _is_blank(glyphs[s], placeholder):
            slots.append(s)
        s += 1
    if len(slots) < count:
        raise RuntimeError(f"비어있지 않은 슬롯이 부족: {len(slots)} < {count}")
    return slots


@dataclass
class Mapping:
    hangul: list
    nonblank_slots: list
    valid_sjis: list
    syl2slot: dict = field(default_factory=dict)
    syl2sjis: dict = field(default_factory=dict)
    slot2syl: dict = field(default_factory=dict)


def build_mapping(glyphs: np.ndarray, hangul: list) -> Mapping:
    """디코드된 글리프 + 한글 2350자 -> 매핑 객체."""
    n = len(hangul)
    valid = gen_valid_sjis(n)
    slots = find_nonblank_slots(glyphs, n)
    if not (len(valid) == len(slots) == n):
        raise RuntimeError("길이 불일치(한글/슬롯/SJIS)")
    m = Mapping(hangul, slots, valid)
    m.syl2slot = {h: s for h, s in zip(hangul, slots)}
    m.syl2sjis = {h: c for h, c in zip(hangul, valid)}
    m.slot2syl = {s: h for h, s in zip(hangul, slots)}
    # 앵커 점검(슬롯 정보가 있을 때만)
    assert slots[0] == KANJI_START_SLOT, f"슬롯[0]={slots[0]} (1418 기대)"
    assert valid[0] == KANJI_START_SJIS
    return m


def to_jsonable(m: Mapping) -> dict:
    """mapping.json 으로 저장 가능한 형태."""
    return {
        'kanji_start_sjis': KANJI_START_SJIS,
        'kanji_start_slot': KANJI_START_SLOT,
        'count': len(m.hangul),
        'syl2sjis': {h: m.syl2sjis[h] for h in m.hangul},
        'syl2slot': {h: m.syl2slot[h] for h in m.hangul},
    }


# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # 폰트 없이 가능한 부분(SJIS 코드열) 자체검증
    codes = gen_valid_sjis(2350)
    assert len(codes) == 2350 and codes[0] == 0x889F
    i = codes.index(0x897E)                       # 円
    assert codes[i + 1] == 0x8980                 # 다음이 園 (0x897F 스킵)
    for c in (0x889F, 0x897E, 0x8980, 0x8A5E, 0x8B7E):
        assert c in codes
    print("자체검증 통과: SJIS 코드열(亜·円·園·蛙·救) 일치, 円→園 연속.")
    print("  (non_blank_slots 검증은 실제 ROM 폰트에서 build_mapping 실행 시 수행)")
