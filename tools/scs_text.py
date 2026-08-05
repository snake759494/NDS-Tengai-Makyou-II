#!/usr/bin/env python3
"""
scs_text.py  —  대사 엔트리 바이트 빌더
=======================================
번역 텍스트(페이지/줄)를 .scs 엔트리 바이트로 만든다.

[제어 코드] 모두 'XX 00' (XX < 0x20) 형태라 SJIS 리드바이트와 충돌하지 않음.
    0D 00  줄바꿈(newline)
    0C 00  화면 지움(clear, 대기 없음)
    12 00  메시지 끝 = 버튼 입력 대기(button wait)

[페이지 구분 시퀀스 — ★ 검증됨]
    page1 + (12 00 0D 00 0C 00) + page2 + ... + 마지막엔 (12 00 00 00)
    즉 페이지 사이 = '버튼 대기 -> 줄바꿈 -> 화면 지움'.
    주의: 'bare 0C 00' 만 쓰면 대기 없이 다음 페이지로 넘어간다.

[문자 -> 바이트]
    한글 음절 -> 매핑된 한자 SJIS 코드(상위바이트 먼저). 게임은 그 한자 슬롯에
      그려둔 한글 글리프를 출력한다.
    전각 공백 -> 0x8140, 그 외 전각 기호/가나 -> shift_jis 인코딩 그대로.
"""

NEWLINE = b'\x0d\x00'
CLEAR = b'\x0c\x00'
BTN_WAIT = b'\x12\x00'
PAGE_SEP = BTN_WAIT + NEWLINE + CLEAR      # 12 00 0D 00 0C 00
END = BTN_WAIT + b'\x00\x00'               # 12 00 00 00
FULLWIDTH_SPACE = b'\x81\x40'


def char_to_bytes(ch: str, syl2sjis: dict) -> bytes:
    """한 글자 -> 2바이트(전각). 한글은 매핑 사전, 그 외는 shift_jis."""
    if ch in syl2sjis:
        code = syl2sjis[ch]
        return bytes([(code >> 8) & 0xFF, code & 0xFF])
    if ch in (' ', '\u3000'):
        return FULLWIDTH_SPACE
    try:
        enc = ch.encode('shift_jis')
    except UnicodeEncodeError:
        raise ValueError(f"인코딩 불가 문자 {ch!r}: KS X 1001(2350) 밖이거나 SJIS 미지원")
    if len(enc) != 2:
        raise ValueError(f"전각 2바이트가 아님: {ch!r} -> {enc!r} (반각 문자는 사용 불가)")
    return enc


def build_line(line: str, syl2sjis: dict) -> bytes:
    return b''.join(char_to_bytes(c, syl2sjis) for c in line)


def build_page(lines, syl2sjis: dict) -> bytes:
    """한 페이지(여러 줄) -> 줄들을 0D 00 으로 연결."""
    return NEWLINE.join(build_line(l, syl2sjis) for l in lines)


def build_entry(pages, syl2sjis: dict) -> bytes:
    """페이지들(각각 줄 리스트) -> 완성된 엔트리 바이트.

    pages: [["줄1","줄2"], ["다음페이지 줄1", ...], ...]
    반환: 페이지 사이 버튼대기 + 마지막 12 00 00 00 종료 포함.
    """
    if not pages:
        return END
    chunks = [build_page(pg, syl2sjis) for pg in pages]
    out = bytearray()
    for i, c in enumerate(chunks):
        out += c
        out += PAGE_SEP if i < len(chunks) - 1 else END
    if len(out) % 2:          # 안전: 짝수 정렬(리패커도 보정하지만 미리)
        out += b'\x00'
    return bytes(out)


# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # '가'=亜(0x889F) 가정한 더미 매핑으로 빌더 자체검증.
    m = {'가': 0x889F, '나': 0x88A0, '다': 0x88A1}
    e = build_entry([['가나', '다'], ['가']], m)
    expected = (b'\x88\x9f\x88\xa0' + NEWLINE + b'\x88\xa1'          # page1: 가나 \n 다
                + PAGE_SEP
                + b'\x88\x9f'                                          # page2: 가
                + END)
    assert e == expected, (e, expected)
    # 전각 공백/기호
    assert char_to_bytes(' ', m) == FULLWIDTH_SPACE
    assert char_to_bytes('！', m) == '！'.encode('shift_jis')
    print("자체검증 통과: 페이지 구분/종료/전각 처리 정상.")
