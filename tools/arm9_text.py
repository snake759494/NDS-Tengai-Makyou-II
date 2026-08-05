#!/usr/bin/env python3
"""
arm9_text.py  —  ARM9 바이너리 내 SJIS 문자열(메뉴/시스템/아이템/적/지명) 한글 치환
=================================================================================
천외마경II는 메뉴·시스템 메시지·카테고리·상점·지명·아이템·주문·적名을 ARM9
바이너리(rom.arm9, 1,180,920바이트)에 **SJIS 문자열**로 저장한다. 대사처럼
한글 SJIS 코드로 치환 가능하다.

[핵심 규칙 — 검증됨]
  - 문자열은 **널 종료**(slot 안에 0x00 종료 + 패딩)이며 포인터로 참조된다.
    → 길이를 늘리면 뒤 문자열/포인터가 깨진다. **바이트 길이 보존 필수.**
  - 치환: 원문 jp의 SJIS 바이트(길이 L)를 확인 → ko를 SJIS로 인코딩(≤L) →
    부족분은 0x00 으로 패딩하여 정확히 L바이트만 덮어쓴다(원본 종료/뒤 데이터 보존).
  - 각 한자/카나/기호 = 2바이트, 한글 1음절 = 2바이트(font_mapping syl2sjis),
    전각공백 = 0x8140. → N글자 일본어(2N바이트)는 ≤N 한글로.
  - ￥제어코드(￥＞ ￥右 ￥キ ￥Ｚ１ ￥全 ￥０ ￥／ ￥ｋ ￥＠ 등)는 모두 2바이트
    SJIS 문자이며 shift_jis 라운드트립이 확인됨 → ko 안에 그대로 두면 보존된다.

[사용]
    a9 = bytearray(rom.arm9)
    applied, errors = apply_entries(a9, entries, syl2sjis)   # entries: {off,jp,ko}
    rom.arm9 = bytes(a9)
"""
try:
    from scs_text import char_to_bytes
except ImportError:
    from .scs_text import char_to_bytes


def encode_ko(ko: str, syl2sjis: dict) -> bytes:
    return b''.join(char_to_bytes(c, syl2sjis) for c in ko)


def apply_entries(a9: bytearray, entries, syl2sjis):
    """entries: iterable of dict{off:int, jp:str, ko:str, slot?:int}.
    바이트 길이 보존하며 in-place 치환. (applied, errors) 반환.
    slot 이 주어지면 그 슬롯 크기(다음 문자열까지 여유)까지 한글 허용 →
    한글 ≤ slot-2 바이트, 나머지는 0x00 패딩(원본 패딩도 널이라 안전).
    slot 이 없으면 원문 길이 L 까지만 허용(보수적)."""
    applied = 0
    errors = []
    for e in entries:
        off = e['off']; jp = e['jp']; ko = e.get('ko') or ''
        if not ko.strip():
            continue
        try:
            jp_b = jp.encode('shift_jis')
        except Exception as ex:
            errors.append((off, f"jp 인코딩불가: {ex}")); continue
        L = len(jp_b)
        cur = bytes(a9[off:off + L])
        if cur != jp_b:
            errors.append((off, f"원문 불일치 (기대 {jp!r}, 실제 {cur.decode('shift_jis','replace')!r})"))
            continue
        slot = e.get('slot')
        # 쓰기 영역 = [off, off+span). span 안을 한글+널패딩으로 채움
        if slot:
            span = slot
            budget = slot - 2          # 최소 2바이트(널) 남김
        else:
            span = L
            budget = L
        try:
            ko_b = encode_ko(ko, syl2sjis)
        except ValueError as ex:
            errors.append((off, f"ko 인코딩불가: {ex}")); continue
        if len(ko_b) > budget:
            errors.append((off, f"너무 김: ko {len(ko_b)//2}글자({len(ko_b)}B) > 예산 {budget}B (슬롯 {slot or L}B)")); continue
        a9[off:off + len(ko_b)] = ko_b
        for k in range(off + len(ko_b), off + span):
            a9[k] = 0
        applied += 1
    return applied, errors


def verify_entries(a9: bytes, entries, syl2sjis):
    """치환 후 각 엔트리가 기대 한글로 디코드되는지 점검. 불일치 목록 반환."""
    bad = []
    for e in entries:
        off = e['off']; ko = e.get('ko') or ''
        if not ko.strip():
            continue
        L = len(encode_ko(ko, syl2sjis))
        got = bytes(a9[off:off + L]).decode('shift_jis', 'replace')
        if got != ko:
            bad.append((off, ko, got))
    return bad
