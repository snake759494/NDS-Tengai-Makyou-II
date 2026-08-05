#!/usr/bin/env python3
"""
tengai_cobj_font.py
===================
천외마경II 卍MARU (NDS, ATMJ) 전각 폰트 코덱.
파일: string_work/grph/font12_GothicW3_bit.cobj  (fid 9138, 16x16, 1bpp, 7560 글리프, 241,920바이트)

게임의 폰트 블릿 루틴(ARM9, 0x020186xx)에서 역산한 실제 포맷:

 (1) 데이터는 8x8 '타일' 단위. 타일 1개 = 8바이트(MSB-first, row-major).
     각 바이트는 '인접 비트쌍 교환'으로 저장됨(블릿이 그릴 때 되돌림):
         b' = ((b>>1)&0x55) | ((b<<1)&0xAA)        # 자기역(self-inverse)

 (2) 타일들은 '폭 378타일'짜리 거대한 타일맵에 row-major로 배열.
     (블릿의 addcs r3,r3,#0xBD0 = 한 타일 줄 아래 = 378*8 = 3024바이트 점프)

 (3) 글리프 N(16x16)은 2x2 타일 블록. 글리프 격자는 가로 189자(=378/2):
         gx = N % 189 , gy = N // 189
         TL = tile[(2*gy  )*378 + 2*gx    ]
         TR = tile[(2*gy  )*378 + 2*gx + 1]
         BL = tile[(2*gy+1)*378 + 2*gx    ]   # TL 바로 아래 타일 (= +378)
         BR = tile[(2*gy+1)*378 + 2*gx + 1]

     => 아래 두 타일이 위 두 타일과 '연속'이 아니라 378타일 떨어져 있는 것이 핵심.
        (원문자 ①~⑳ 가 아래쪽이 대각선 아래 칸으로 잘려 보였던 버그를 이 발견으로 해결)

decode/encode 모두 검증됨: 디코드→인코드 왕복이 원본 바이트와 100% 일치.
"""
import numpy as np

TILE_W = 378              # 타일맵 폭(타일 수)
GLYPH_W = TILE_W // 2     # 한 줄당 글리프 수 = 189
GLYPH_SIZE = 16
FONT_BYTES = 241920       # 원본 파일 크기(반드시 유지)
NUM_GLYPHS = FONT_BYTES // 8 // 4   # 7560


def _swap_adjacent_bits(b: np.ndarray) -> np.ndarray:
    """인접 비트쌍 교환 (자기역)."""
    return (((b >> 1) & 0x55) | ((b << 1) & 0xAA)).astype(np.uint8)


def _tile_indices(n: int):
    """글리프 N의 (TL, TR, BL, BR) 타일 인덱스."""
    gx, gy = n % GLYPH_W, n // GLYPH_W
    bt = (2 * gy) * TILE_W + 2 * gx
    bb = (2 * gy + 1) * TILE_W + 2 * gx
    return bt, bt + 1, bb, bb + 1


def decode_font(raw: bytes) -> np.ndarray:
    """cobj 바이트 -> (N, 16, 16) uint8(0/1) 글리프 배열."""
    data = _swap_adjacent_bits(np.frombuffer(bytes(raw), np.uint8))
    nt = len(data) // 8
    tiles = np.unpackbits(data[: nt * 8].reshape(nt, 8), axis=1).reshape(nt, 8, 8)
    ng = nt // 4
    out = np.zeros((ng, GLYPH_SIZE, GLYPH_SIZE), np.uint8)
    for n in range(ng):
        tl, tr, bl, br = _tile_indices(n)
        if br >= nt:
            break
        out[n, :8, :8] = tiles[tl]
        out[n, :8, 8:] = tiles[tr]
        out[n, 8:, :8] = tiles[bl]
        out[n, 8:, 8:] = tiles[br]
    return out


def encode_into(raw: bytearray, n: int, glyph16: np.ndarray) -> None:
    """글리프 N(16x16, 0/1)을 raw(bytearray)의 올바른 타일 위치에 써넣음(한글 삽입용).

    decode_font 의 정확한 역연산. raw 는 in-place 로 수정된다(크기 불변).
    """
    g = (np.asarray(glyph16) > 0).astype(np.uint8)
    assert g.shape == (GLYPH_SIZE, GLYPH_SIZE), "글리프는 16x16 이어야 함"
    quads = {
        0: g[:8, :8], 1: g[:8, 8:],   # TL, TR
        2: g[8:, :8], 3: g[8:, 8:],   # BL, BR
    }
    tiles = _tile_indices(n)
    for q, ti in enumerate(tiles):
        plain = np.packbits(quads[q], axis=1).reshape(8)          # 8바이트(MSB-first)
        stored = _swap_adjacent_bits(plain)                        # 저장형(비트쌍 교환)
        off = ti * 8
        raw[off:off + 8] = bytes(stored.tolist())


def glyph_to_text(g: np.ndarray, on='#', off='.') -> str:
    """디버그용: 16x16 글리프를 아스키 아트로."""
    return '\n'.join(''.join(on if v else off for v in row) for row in g)


# ----------------------------------------------------------------------------
if __name__ == '__main__':
    # 합성 데이터로 디코드/인코드 왕복 무손실 자체검증(ROM 없이도 로직 검증).
    import os
    rng = np.random.default_rng(0)
    raw = bytearray(rng.integers(0, 256, FONT_BYTES, dtype=np.uint8).tobytes())
    glyphs = decode_font(raw)
    print(f"디코드: {glyphs.shape[0]} 글리프 (기대 {NUM_GLYPHS})")
    assert glyphs.shape[0] == NUM_GLYPHS

    # 임의 글리프를 다시 써넣고(원본 글리프 그대로) raw 가 보존되는지 확인
    raw2 = bytearray(raw)
    for n in (0, 1418, 1574, 1576, 3779, NUM_GLYPHS - 1):
        encode_into(raw2, n, glyphs[n])
    assert raw2 == raw, "동일 글리프 재기록 시 바이트가 달라짐(역연산 오류)"

    # 새 글리프(체크무늬)를 써넣고 디코드해서 일치하는지
    chk = np.indices((16, 16)).sum(0) % 2
    encode_into(raw2, 1418, chk.astype(np.uint8))
    assert np.array_equal(decode_font(raw2)[1418], chk), "인코드→디코드 불일치"
    assert len(raw2) == FONT_BYTES, "파일 크기가 바뀜"
    print("자체검증 통과: 디코드/인코드 역연산 일치, 크기 유지.")
