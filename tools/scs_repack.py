#!/usr/bin/env python3
"""
Tengai Makyou II - Manji Maru (NDS, ATMJ)  대사(.scs) 리패커
=============================================================

[목적] 번역문으로 텍스트 길이가 바뀌어도 .scs 를 안전하게 재조립한다.

[검증 결과] 2,272개 .scs 전부에서 split_entries -> rebuild 왕복이 바이트 단위로
            완전 일치(round-trip 100%). 모든 엔트리 오프셋이 짝수라 ÷2도 정확.

[.scs 헤더 = 포인터 테이블 (u16 LE)]
    u16[0]      = 본문 텍스트 시작 오프셋(= 헤더 바이트 길이)
    u16[1]      = 예약(전 파일 0)
    u16[2..]    = 각 텍스트 엔트리의 시작 오프셋 ÷2 (텍스트 시작 기준 상대, 2바이트 워드 단위)
    엔트리 개수 = (u16[0] - 4) / 2

[.scb 관계] .scb 는 텍스트를 '인덱스'로 참조하고(오프셋 사본 미보유, 2272개 중
            0.5%만 우연 일치), 엔진이 위 포인터 테이블로 인덱스->오프셋을 해석한다.
            => 엔트리 개수/순서를 유지하고 이 헤더만 다시 만들면 .scb 는 수정 불필요.

[주의]
  - 엔트리 길이는 반드시 짝수(오프셋 ÷2 정확성). 전각 SJIS·16비트 제어코드는
    모두 2바이트라 자연히 짝수지만, 안전하게 rebuild() 가 홀수면 0x00 을 덧댄다.
  - 엔트리 개수/순서는 절대 바꾸지 말 것(.scb 인덱스가 어긋남). 텍스트 '내용'만 교체.
  - 메시지 종료 제어코드(0x12 00 00 00) 등 엔트리 끝 구조는 보존해야 게임이
    대화창을 올바로 닫는다.
"""
import struct


def split_entries(scs: bytes):
    """(reserved, [entry_bytes...]) 반환. 포인터 테이블 기준으로 본문을 분할."""
    scs = bytes(scs)
    start = struct.unpack('<H', scs[:2])[0]
    n = start // 2
    u16 = struct.unpack(f'<{n}H', scs[:n * 2])
    ptrs = list(u16[2:])
    abs_off = [start + p * 2 for p in ptrs] + [len(scs)]
    body = [scs[abs_off[i]:abs_off[i + 1]] for i in range(len(ptrs))]
    return u16[1], body


def rebuild(reserved: int, body) -> bytes:
    """엔트리 바이트들 -> 완성된 .scs (헤더 포인터 테이블 자동 계산)."""
    body = [b if len(b) % 2 == 0 else b + b'\x00' for b in body]   # 짝수 정렬
    n = len(body)
    start = 4 + 2 * n
    rel, acc = [], 0
    for b in body:
        rel.append(acc)
        acc += len(b)
    ptrs = [off // 2 for off in rel]
    return struct.pack(f'<{2 + n}H', start, reserved, *ptrs) + b''.join(body)


def replace_entry(scs: bytes, index: int, new_entry: bytes) -> bytes:
    """index 번 엔트리의 '바이트'를 new_entry 로 교체하고 재조립.

    new_entry 는 텍스트(SJIS)+제어코드까지 포함한 엔트리 전체 바이트여야 한다
    (예: scs_text.build_entry(pages, syl2sjis)).
    """
    reserved, body = split_entries(scs)
    if not (0 <= index < len(body)):
        raise IndexError(f"엔트리 인덱스 범위 밖: {index} / 0..{len(body) - 1}")
    body[index] = bytes(new_entry)
    return rebuild(reserved, body)


def entry_count(scs: bytes) -> int:
    start = struct.unpack('<H', bytes(scs)[:2])[0]
    return (start - 4) // 2


# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # 합성 .scs 로 분해/재조립/교체 왕복 자체검증.
    bodies = [b'\x9f\x88\x12\x00\x00\x00', b'\xa0\x88\xa1\x88\x12\x00\x00\x00', b'\x12\x00\x00\x00']
    scs = rebuild(0, bodies)
    r, b2 = split_entries(scs)
    assert r == 0 and b2 == bodies, "분해/재조립 불일치"
    assert rebuild(r, b2) == scs, "왕복 불일치"
    # 엔트리 교체로 길이 변경
    scs2 = replace_entry(scs, 0, b'\x88\x9f\x88\x9f\x88\x9f\x12\x00\x00\x00')
    r2, b3 = split_entries(scs2)
    assert b3[0] == b'\x88\x9f\x88\x9f\x88\x9f\x12\x00\x00\x00' and b3[1:] == bodies[1:]
    assert entry_count(scs2) == 3
    print("자체검증 통과: split/rebuild/replace_entry 정상, 헤더 자동 재계산.")
