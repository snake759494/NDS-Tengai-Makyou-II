#!/usr/bin/env python3
"""
galmuri_bdf.py  —  갈무리 BDF 파서 + 16x16 렌더러 (대사용)
==========================================================
대사 글리프(16x16 1bpp)는 갈무리11 비트맵 폰트로 그린다(픽셀 단위로 또렷).

[정렬] 천외마경II 한자 잉크는 16x16 셀 안에서 좌상단 기준 약 11x11(행 0~10).
       갈무리11(CAP_HEIGHT 11)을 **baseline=11, left=1** 로 두면 정확히 겹친다.

[BDF] 글리프마다 'BBX w h xoff yoff' + h행 16진 비트맵(행당 ceil(w/8) 바이트,
      MSB-first). 원점(origin)은 baseline, y는 위쪽이 +.
      배치식: out_row = baseline - (yoff + h) + r ,  out_col = left + xoff + c
"""
import numpy as np

GLYPH_SIZE = 16
BASELINE = 11
LEFT = 1


class GalmuriBDF:
    def __init__(self, path: str):
        self.glyphs = {}          # codepoint -> (w, h, xoff, yoff, [row_int...], nbits)
        self._parse(path)

    def _parse(self, path):
        cp = None
        bbx = None
        rows = None
        reading = False
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.startswith('ENCODING'):
                    cp = int(line.split()[1])
                elif line.startswith('BBX'):
                    _, w, h, xo, yo = line.split()
                    bbx = (int(w), int(h), int(xo), int(yo))
                elif line.startswith('BITMAP'):
                    reading = True
                    rows = []
                elif line.startswith('ENDCHAR'):
                    if cp is not None and bbx is not None:
                        w, h, xo, yo = bbx
                        nbits = ((w + 7) // 8) * 8 if w > 0 else 0
                        self.glyphs[cp] = (w, h, xo, yo, rows or [], nbits)
                    cp = bbx = rows = None
                    reading = False
                elif reading:
                    s = line.strip()
                    if s:
                        rows.append(int(s, 16))

    def render_char(self, ch: str, size=GLYPH_SIZE, baseline=BASELINE, left=LEFT) -> np.ndarray:
        """문자 -> (16,16) uint8(0/1)."""
        out = np.zeros((size, size), np.uint8)
        g = self.glyphs.get(ord(ch))
        if g is None:
            return out
        w, h, xo, yo, rows, nbits = g
        if w == 0 or h == 0 or nbits == 0:
            return out
        for r in range(min(h, len(rows))):
            oy = baseline - (yo + h) + r
            if not (0 <= oy < size):
                continue
            bits = rows[r]
            for c in range(w):
                if (bits >> (nbits - 1 - c)) & 1:
                    ox = left + xo + c
                    if 0 <= ox < size:
                        out[oy, ox] = 1
        return out

    def has(self, ch: str) -> bool:
        g = self.glyphs.get(ord(ch))
        return g is not None and g[0] > 0 and g[1] > 0


# ----------------------------------------------------------------------------
if __name__ == '__main__':
    import sys, os
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), '..', 'fonts', 'Galmuri11.bdf')
    bdf = GalmuriBDF(path)
    print("글리프 수:", len(bdf.glyphs))
    g = bdf.render_char('가')
    print("'가' 픽셀 수:", int(g.sum()))
    # 상단 행(FC40 첫 11비트 = 1111110 0010 -> 7픽셀, cols 1..11에 위치)
    print("상단행:", ''.join('#' if v else '.' for v in g[0]))
    assert g.sum() > 0 and bdf.has('힣') and bdf.has('한')
    # 아스키 아트
    print('\n'.join(''.join('#' if v else '.' for v in row) for row in g))
    print("자체검증 통과: BDF 파싱/렌더 정상.")
