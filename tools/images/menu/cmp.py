"""CMP 다단계 압축 코덱 (天外魔境II 卍MARU / ATMJ).

구조: b"CMP" + ver(1B) + f1(u32, 최종 해제 크기) + f2(u32, 외부 DS헤더=타입+크기) + 압축데이터
- ver 바이트 = 압축 해제 '단계 수' (게임이 이 횟수만큼 BIOS 해제를 수행).
- 외부 타입은 f2 하위바이트: 0x24(Huffman4)/0x28(Huffman8)/0x30(RLE)/0x10(LZ10)/0x11(LZ11).
- 다단계 체인: 외부 해제 -> 결과 레이어의 헤더 타입으로 반복 해제 -> f1 크기 도달.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools, struct as st


def _bits(data, bs_off, msb=True):
    bits = []; i = bs_off
    while i + 4 <= len(data):
        w = st.unpack_from('<I', data, i)[0]; i += 4
        for b in (range(31, -1, -1) if msb else range(0, 32)):
            bits.append((w >> b) & 1)
    return bits


def huff_dec(data, tt, target, nbits, msb=True):
    tsz = data[tt]; bs_off = tt + (tsz + 1) * 2; bits = _bits(data, bs_off, msb)
    syms = []; pos = 1; bi = 0
    need = target if nbits == 8 else target * 2
    while bi < len(bits) and len(syms) < need:
        node = data[tt + pos]; nextp = (pos & ~1) + (node & 0x3F) * 2 + 2
        bit = bits[bi]; bi += 1
        if bit == 0: child = nextp; leaf = node & 0x80
        else: child = nextp + 1; leaf = node & 0x40
        if leaf: syms.append(data[tt + child] & ((1 << nbits) - 1)); pos = 1
        else: pos = child
    if nbits == 8: return bytes(syms[:target])
    out = bytearray()
    for k in range(0, len(syms) - (len(syms) % 2), 2):
        out.append(syms[k] | (syms[k + 1] << 4))
    return bytes(out)


def rle_dec(data):
    size = data[1] | (data[2] << 8) | (data[3] << 16); out = bytearray(); i = 4
    while len(out) < size and i < len(data):
        f = data[i]; i += 1
        if f & 0x80:
            n = (f & 0x7F) + 3
            if i < len(data): out.extend([data[i]] * n); i += 1
        else:
            n = (f & 0x7F) + 1; out.extend(data[i:i + n]); i += n
    return bytes(out)


def lz11_dec(data):
    size = data[1] | (data[2] << 8) | (data[3] << 16); out = bytearray(); i = 4
    while len(out) < size and i + 1 < len(data):
        fl = data[i]; i += 1
        for b in range(8):
            if len(out) >= size: break
            if fl & (0x80 >> b):
                ind = data[i] >> 4
                if ind == 0:
                    n = ((data[i] & 0xF) << 4 | (data[i + 1] >> 4)) + 0x11
                    ds = ((data[i + 1] & 0xF) << 8 | data[i + 2]) + 1; i += 3
                elif ind == 1:
                    n = ((data[i] & 0xF) << 12 | data[i + 1] << 4 | (data[i + 2] >> 4)) + 0x111
                    ds = ((data[i + 2] & 0xF) << 8 | data[i + 3]) + 1; i += 4
                else:
                    n = (data[i] >> 4) + 1
                    ds = ((data[i] & 0xF) << 8 | data[i + 1]) + 1; i += 2
                for _ in range(n): out.append(out[-ds])
            else:
                out.append(data[i]); i += 1
    return bytes(out)


def _layer_dec(layer):
    t = layer[0]
    if t == 0x10: return tools.lz10_dec(layer)
    if t == 0x11: return lz11_dec(layer)
    if t == 0x30: return rle_dec(layer)
    if t in (0x24, 0x28):
        return huff_dec(layer, 4, (layer[1] | layer[2] << 8 | layer[3] << 16), t & 0xF)
    return None


def cmp_decode(raw):
    """CMP 바이트열을 최종 데이터로 해제."""
    f1 = st.unpack_from('<I', raw, 4)[0]; f2 = st.unpack_from('<I', raw, 8)[0]
    typ = f2 & 0xFF; sz = f2 >> 8
    if typ in (0x24, 0x28): layer = huff_dec(raw, 12, sz, typ & 0xF)
    elif typ == 0x10: layer = tools.lz10_dec(raw[8:])
    elif typ == 0x11: layer = lz11_dec(raw[8:])
    elif typ == 0x30: layer = rle_dec(raw[8:])
    else: layer = raw[12:12 + f1]
    for _ in range(8):
        if not layer or len(layer) == f1: break
        nx = _layer_dec(layer)
        if nx is None: break
        layer = nx
    return layer


def rle_enc(data):
    """DS RLE(타입 0x30)로 인코딩. 4바이트 DS헤더 + 스트림 반환."""
    out = bytearray(); i = 0; n = len(data)
    while i < n:
        run = 1
        while i + run < n and data[i + run] == data[i] and run < 130: run += 1
        if run >= 3:
            out.append(0x80 | (run - 3)); out.append(data[i]); i += run
        else:
            s = i
            while i < n:
                r = 1
                while i + r < n and data[i + r] == data[i] and r < 3: r += 1
                if r >= 3: break
                i += 1
                if i - s >= 128: break
            out.append((i - s) - 1); out.extend(data[s:i])
    return bytes([0x30, n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF]) + bytes(out)


def cmp_encode_rle(decoded, ver=1):
    """최종 데이터를 단일 RLE CMP로 인코딩 (ver=1, 1단계 해제).
    게임의 char01/palt 파일과 동일한 구조라 안전."""
    return b'CMP' + bytes([ver]) + st.pack('<I', len(decoded)) + rle_enc(decoded)
