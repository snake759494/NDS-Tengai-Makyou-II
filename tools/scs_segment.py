#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scs_segment.py — 제어코드를 보존하는 세그먼트 방식 대사 추출/재조립.

엔트리를 (번역 가능한 텍스트) 와 (그대로 보존할 제어 바이트) 세그먼트로 나눈다.
이렇게 하면 화자/초상(0x10)·인라인 명령(0x11)·줄바꿈·페이지 구분을 원본 그대로
유지한 채 텍스트만 한국어로 교체할 수 있다.

세그먼트:
  {"c": "10000200"}                         제어 바이트(그대로 보존)
  {"jp": "待ちかねたぞ", "ko": "", "b": ".."}  텍스트(jp=원문, ko=번역, b=원본바이트)

제어코드 길이:
  0x10 / 0x11  → 4바이트 (OP 00 PARAM 00)  ※ 화자/초상, 인라인 명령
  그 외 < 0x20 → 2바이트 (XX 00)            ※ 0D 줄바꿈, 0C 지움, 12 버튼대기, 00 NUL
텍스트:
  SJIS 2바이트(0x81-0x9F/0xE0-0xFC + 트레일), 반각 카나(0xA1-0xDF), 반각 ASCII
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scs_text import char_to_bytes

PARAM_OPS = {0x10, 0x11}        # 4바이트 제어(파라미터 동반)


def _is_sjis_lead(b):
    return (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC)


def to_segments(body: bytes, _stats=None):
    """엔트리 바이트 -> 세그먼트 리스트."""
    b = bytes(body)
    n = len(b)
    i = 0
    segs = []
    cur_text = []            # [(char, raw_bytes)]
    cur_raw = bytearray()

    def flush_text():
        if cur_text:
            jp = ''.join(c for c, _ in cur_text)
            segs.append({"jp": jp, "ko": ""})
            cur_text.clear()

    def flush_raw():
        if cur_raw:
            segs.append({"c": bytes(cur_raw).hex()})
            cur_raw.clear()

    while i < n:
        c = b[i]
        if c in PARAM_OPS:
            flush_text()
            if _stats is not None:           # 4바이트 구조 진단
                _stats['param'] += 1
                if i + 1 < n and b[i + 1] != 0:
                    _stats['p1_nonzero'] += 1
                if i + 3 < n and b[i + 3] != 0:
                    _stats['p3_nonzero'] += 1
            cur_raw += b[i:i + 4]
            i += 4
        elif c < 0x20:
            flush_text()
            cur_raw += b[i:i + 2]
            i += 2
        elif _is_sjis_lead(c) and i + 1 < n:
            flush_raw()
            pair = b[i:i + 2]
            try:
                ch = pair.decode('shift_jis')
            except UnicodeDecodeError:
                ch = '〓'
                if _stats is not None:
                    _stats['decode_err'] += 1
            cur_text.append((ch, pair))
            i += 2
        elif 0xA1 <= c <= 0xDF:              # 반각 카나
            flush_raw()
            cur_text.append((bytes([c]).decode('shift_jis', 'replace'), bytes([c])))
            i += 1
        elif 0x20 <= c <= 0x7E:              # 반각 ASCII
            flush_raw()
            cur_text.append((chr(c), bytes([c])))
            i += 1
        else:                                 # 미상 바이트 → 보존
            flush_text()
            cur_raw += b[i:i + 1]
            i += 1
    flush_text()
    flush_raw()
    return segs


def from_segments(segs, syl2sjis: dict) -> bytes:
    """세그먼트 -> 엔트리 바이트. ko가 있으면 한국어 인코딩, 없으면 원문(shift_jis).
    ko 안의 '\\n'(줄바꿈)은 게임 줄바꿈 코드 0x0D 00 으로 변환(긴 줄 분할용)."""
    out = bytearray()
    for s in segs:
        if "c" in s:
            out += bytes.fromhex(s["c"])
        elif "jp" in s:
            ko = s.get("ko") or ""
            if ko:
                parts = ko.split('\n')
                enc = [b''.join(char_to_bytes(ch, syl2sjis) for ch in p)
                       for p in parts]
                out += b'\x0d\x00'.join(enc)
            else:
                out += s["jp"].encode('shift_jis')
    return bytes(out)


def entry_text(segs) -> str:
    """세그먼트에서 사람이 읽을 원문만 이어붙임(제어코드는 기호로)."""
    parts = []
    for s in segs:
        if "jp" in s:
            parts.append(s["jp"])
        elif "c" in s:
            cb = bytes.fromhex(s["c"])
            j = 0
            while j < len(cb):
                op = cb[j]
                if op == 0x0D:
                    parts.append("\n"); j += 2
                elif op == 0x0C:
                    parts.append(" ⟪페이지⟫ "); j += 2
                elif op == 0x12:
                    parts.append("⟨대기⟩"); j += 2
                elif op in PARAM_OPS:
                    parts.append(f"⟨{op:02X}:{cb[j+2]:02X}⟩"); j += 4
                else:
                    j += 2
    return ''.join(parts)


# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # 자체검증: 제어코드 포함 합성 엔트리의 왕복(번역 없음) 일치
    sample = bytes.fromhex(
        "10000200" "91d282bf82a982cb82bd82bc" "11000a00"
        "814099c28adb8149" "1100320 0".replace(" ", "")
        + "0d00" "89b4976c82cd" "12000000"
    )
    segs = to_segments(sample)
    rebuilt = from_segments(segs, {})
    assert rebuilt == sample, f"\n원본:  {sample.hex()}\n재조립:{rebuilt.hex()}"
    # 텍스트 세그먼트가 제대로 잡혔는지
    jp_segs = [s["jp"] for s in segs if "jp" in s]
    assert jp_segs[0] == "待ちかねたぞ", jp_segs
    assert "卍丸" in jp_segs[1], jp_segs
    print("자체검증 통과: 세그먼트 왕복 일치, 텍스트 분리 정상")
    print("  텍스트 세그먼트:", jp_segs)
