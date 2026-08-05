#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
menu_patch.py — 천외마경II 卍MARU (ATMJ) 메뉴 이미지 한글 패치

원본(또는 대사/폰트가 이미 패치된) NDS 롬에 메뉴 그래픽 한글을 입힌다.
폰트(font12_GothicW3) 슬롯이 아니라, 미리 렌더된 메뉴 타일 그래픽을
갈무리14로 다시 그려 덮어쓰는 방식이다(슈퍼로봇대전J 방식과 무관, 그래픽 직접 교체).

대상:
  1) mainmenu.obc (8bpp 타일, fid 자동 탐색)
       - 메인 메뉴: 状態/道具/巻物/武具/奥義
       - 필드 메뉴: 地図/モード/作戦
       - 하단 라벨: コマンド/ヘルプ  (사이 워드는 비움)
  2) bs_obj_command_icon1~17 (4bpp 타일) — 전투 명령 16개

쓰기 방식: 패치한 파일을 LZ10 무손실(전부-리터럴, VRAM 안전)로 재압축해
          롬의 0xFF 패딩 영역에 추가하고 FAT만 그 위치로 변경(헤더 무손상).

사용법:
    python menu_patch.py 입력롬.nds 출력롬.nds
  * 매번 '깨끗한' 원본(또는 대사 패치본)에 적용하세요. 같은 출력본에 반복
    적용하면 이전에 추가한 데이터가 버려진 채 쌓입니다(동작엔 무해).

필요 패키지: Python 3.8+, numpy, pillow, 그리고 같은 폴더의 Galmuri14.ttf
"""
import sys
import numpy as np
from PIL import Image, ImageFont, ImageDraw
import tools

# ============================================================
# 번역 설정 — 원하는 단어로 자유롭게 수정하세요 (2글자 권장)
# ============================================================
# mainmenu.obc 안의 '워드 인덱스' -> 한글. (워드 1개 = 32x16 = 두 글자칸)
MAIN_MENU = {54: "상태", 55: "도구", 56: "주문", 57: "무구", 58: "오의"}  # 状態/道具/巻物/武具/奥義
FIELD_MENU = {62: "지도", 63: "모드", 64: "작전"}                          # 地図/モード/作戦
LABELS = {48: "명령", 50: "도움"}   # コマンド -> 명령, ヘルプ -> 도움
BLANK_WORDS = [49]                  # コマンド/ヘルプ 사이 잔여 칸 비우기
# 전투 명령: command_icon 번호 -> 한글. (icon9 '??' 는 그대로 두므로 제외)
BATTLE = {
    1: "공격", 2: "검법", 3: "돌파", 4: "주문", 5: "자세", 6: "작전",
    7: "무구", 8: "도구", 10: "비술", 11: "체술", 12: "귀도", 13: "포격",
    14: "공격", 15: "화염", 16: "어뢰", 17: "열탄",
}
# 원어 참고:
#  戦う공격 剣法검법 突破돌파 巻物주문 構え자세 作戦작전 武具무구 道具도구
#  秘芸비술 体術체술 鬼道귀도 砲撃포격 攻撃공격 火炎화염 魚雷어뢰 熱弾열탄

FONT_PATH = "Galmuri14.ttf"
FONT_SIZE = 14
THRESHOLD = 100          # 글리프 이진화 임계값
MENU_IDX = 37            # mainmenu.obc(8bpp) 글자 팔레트 인덱스(흰색)
BATTLE_IDX = 5           # command_icon(4bpp) 글자 팔레트 인덱스(흰색)
OBC_HEADER = 456         # mainmenu.obc: 8바이트 헤더 + 448바이트 팔레트 = 456

# ============================================================
_font = None
def font():
    global _font
    if _font is None:
        _font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    return _font


def render_centered(ch):
    """한 글자를 16x16 칸 가운데에 배치(글자별 중앙정렬). 메인/필드 메뉴용."""
    img = Image.new("L", (16, 16), 0)
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), ch, font=font())
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((16 - tw) // 2 - bb[0], (16 - th) // 2 - bb[1]), ch, fill=255, font=font())
    return (np.array(img) > THRESHOLD).astype(np.uint8)


def _ink(ch):
    """글자 잉크만 크롭한 비트맵."""
    im = Image.new("L", (24, 24), 0)
    d = ImageDraw.Draw(im)
    bb = d.textbbox((0, 0), ch, font=font())
    d.text((-bb[0] + 4, -bb[1] + 4), ch, fill=255, font=font())
    a = (np.array(im) > THRESHOLD).astype(np.uint8)
    ys = np.where(a.any(1))[0]
    xs = np.where(a.any(0))[0]
    if len(ys) == 0:
        return np.zeros((1, 1), np.uint8)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def fit_word(chars, gap=None):
    """여러 글자를 32x16 안에 '바짝 붙여' 가운데 배치. 라벨/전투 명령용."""
    inks = [_ink(c) for c in chars]
    n = len(chars)
    if gap is None:
        gap = 2 if n <= 2 else 1
    tw = sum(g.shape[1] for g in inks) + gap * (n - 1)
    sx = max(0, (32 - tw) // 2)
    out = np.zeros((16, 32), np.uint8)
    x = sx
    for g in inks:
        h, w = g.shape
        y0 = (16 - h) // 2
        out[y0:y0 + h, x:x + w] = g
        x += w + gap
    return out


def word_centered_pair(two):
    """두 글자를 각 16px 칸 가운데에(메인/필드 메뉴 스타일). 32x16 반환."""
    g = np.zeros((16, 32), np.uint8)
    g[:, :16] = render_centered(two[0])
    g[:, 16:] = render_centered(two[1])
    return g


# ---------- mainmenu.obc (8bpp) ----------
def patch_mainmenu(dec):
    """dec(=압축 해제된 mainmenu.obc, bytearray)에 한글을 그려 넣는다."""
    def put(word_idx, bitmap16x32):
        T0 = word_idx * 8
        for y in range(16):
            for x in range(32):
                tcol = x // 8
                trow = y // 8
                tidx = T0 + trow * 4 + tcol
                off = OBC_HEADER + tidx * 64 + (y % 8) * 8 + (x % 8)
                dec[off] = MENU_IDX if bitmap16x32[y, x] else 0

    for wi, ko in MAIN_MENU.items():
        put(wi, word_centered_pair(ko))
    for wi, ko in FIELD_MENU.items():
        put(wi, word_centered_pair(ko))
    for wi, ko in LABELS.items():
        put(wi, fit_word(ko))
    for wi in BLANK_WORDS:
        put(wi, np.zeros((16, 32), np.uint8))


# ---------- command_icon (4bpp, 헤더 없음, 8타일) ----------
def _set4(tile, x, y, v):
    bi = y * 4 + x // 2
    if x % 2 == 0:
        tile[bi] = (tile[bi] & 0xF0) | v
    else:
        tile[bi] = (tile[bi] & 0x0F) | (v << 4)


def make_command_icon(two):
    """전투 명령 한 개(32x16, 4bpp, 8타일 256바이트)를 한글로 새로 만든다."""
    big = fit_word(two)
    tiles = [bytearray(32) for _ in range(8)]
    for y in range(16):
        for x in range(32):
            tcol = x // 8
            trow = y // 8
            _set4(tiles[trow * 4 + tcol], x % 8, y % 8, BATTLE_IDX if big[y, x] else 0)
    return b"".join(tiles)


def main():
    if len(sys.argv) >= 3:
        rom_in, rom_out = sys.argv[1], sys.argv[2]
    else:
        print(__doc__)
        sys.exit("\n[오류] 사용법: python menu_patch.py 입력롬.nds 출력롬.nds")

    rom = bytearray(open(rom_in, "rb").read())
    paths = tools.parse_fnt(rom)
    name2fid = {p.rsplit("/", 1)[-1]: f for f, p in paths.items()}

    # 1) mainmenu.obc
    if "mainmenu.obc" not in name2fid:
        sys.exit("[오류] mainmenu.obc 를 찾지 못했습니다. ATMJ 원본 롬이 맞는지 확인하세요.")
    fid_mm = name2fid["mainmenu.obc"]
    dec = bytearray(tools.lz10_dec(tools.read_file(rom, fid_mm)[0]))
    patch_mainmenu(dec)
    comp = tools.lz10_store(bytes(dec))
    assert tools.lz10_dec(comp) == bytes(dec), "재압축 검증 실패"
    tools.append_repoint(rom, fid_mm, comp)
    print(f"[OK] mainmenu.obc 패치 (메인/필드/라벨)")

    # 2) 전투 명령 command_icon
    patched = 0
    for n, ko in BATTLE.items():
        nm = f"bs_obj_command_icon{n}.cobj"
        if nm not in name2fid:
            print(f"  [건너뜀] {nm} 없음")
            continue
        comp = tools.lz10_store(make_command_icon(ko))
        tools.append_repoint(rom, name2fid[nm], comp)
        patched += 1
    print(f"[OK] 전투 명령 {patched}개 패치")

    open(rom_out, "wb").write(rom)
    print(f"[완료] -> {rom_out}  ({len(rom):,} 바이트)")


if __name__ == "__main__":
    main()
