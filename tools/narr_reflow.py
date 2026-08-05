#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""narr_reflow.py — 나레이션 대사 화면 단위 추출/재조립.

문제: 긴 나레이션이 줄바꿈(0x0D)·버튼대기(0x12)로 잘게 쪼개져 각 줄 조각이
독립 번역돼 어색하고 띄어쓰기/줄바꿈이 엉성하다.

해결: 한 엔트리를 '화면(screen)' 단위로 본다.
  - 화면 = 버튼대기(0x12)·화자(0x10)·인라인(0x11)·페이지(0x0C) 같은 '경계 제어' 사이의
    텍스트 묶음(화면 내부 줄바꿈 0x0D 는 '소프트', 재배치 가능).
  - 경계 제어코드는 **그대로 보존**하고, 화면 내부의 텍스트+줄바꿈만 한국어로 재생성.
  - from_segments 가 ko 안의 '\\n' 을 0x0D 00 으로 변환하므로, 화면 1개당 텍스트 세그
    1개(여러 줄은 '\\n')로 모으면 WAIT 구조를 그대로 유지한 채 재줄바꿈할 수 있다.

핵심 보장(자체검증): korean_screens == 원문 화면(줄을 '\\n'으로) 이면 재조립 바이트가
원본(일본어) 바이트와 '완전히 동일'(구조 무손실). self_test() 참고.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scs_segment import from_segments

PARAM = {0x10, 0x11}
HERE = os.path.dirname(os.path.abspath(__file__))

# ── 박스 제약 ────────────────────────────────────────────────
MAX_LINE = 18          # 한 줄 최대 전각 글자수(측정: 99%ile=18, 19~20 극소수)
MAX_LINES_PER_SCREEN = 3

# ── 인코딩 가능 문자 집합 ────────────────────────────────────
def load_ks(path=None):
    path = path or os.path.join(HERE, "ks2350.txt")
    txt = open(path, encoding="utf-8").read()
    return set(ch for ch in txt if not ch.isspace())

def is_encodable(ch, ks):
    if ch in ks:                      # 한글 음절(매핑됨)
        return True
    if ch in (' ', '　'):         # 공백 → 전각공백
        return True
    try:
        return len(ch.encode('shift_jis')) == 2   # 전각 기호/가나
    except UnicodeEncodeError:
        return False


# ── 제어코드 판별 ────────────────────────────────────────────
def _is_pure_newline(seg):
    return ("c" in seg) and seg["c"] == "0d00"

def _ops(hexs):
    cb = bytes.fromhex(hexs); j = 0; out = []
    while j < len(cb):
        op = cb[j]; out.append(op); j += 4 if op in PARAM else 2
    return out


# ── 화면 분할 ────────────────────────────────────────────────
def split_screens(segs):
    """엔트리 segs -> (screens, info).
    screens: 각 화면 = 줄 리스트(jp 문자열). 화면 내부 0x0D 로 줄 구분.
    info: has_inline11, has_speaker, decode_err.
    """
    screens = []
    lines = [""]
    open_ = False
    has11 = has10 = derr = False
    def flush():
        nonlocal lines, open_
        if open_:
            screens.append(lines)
        lines = [""]; open_ = False
    for s in segs:
        if "jp" in s:
            jp = s["jp"]
            if "〓" in jp:
                derr = True
            lines[-1] += jp
            open_ = True
        elif _is_pure_newline(s):
            if open_:
                lines.append("")     # 화면 내부 줄바꿈(소프트)
            # 화면 밖(선행) 0x0D 는 경계처럼 취급(아래 else 와 동일하게 보존은
            # rebuild 에서 처리). 여기 분할용 카운트엔 영향 없음.
        else:
            o = _ops(s["c"])
            if 0x11 in o: has11 = True
            if 0x10 in o: has10 = True
            flush()
    flush()
    return screens, {"has_inline11": has11, "has_speaker": has10, "decode_err": derr}


def screen_jp_joined(screen):
    """화면(줄 리스트) -> 의미 복원용 한 덩어리 일본어(줄을 이어붙임)."""
    return "".join(screen)


def split_screens_pairs(segs):
    """split_screens 와 동일 분할이되, 각 줄을 {'jp','ko'} 로(기존 번역 참조용).
    returns screens: 각 화면 = 줄 리스트, 줄 = {'jp':..., 'ko':...}.
    """
    screens = []
    lines = [{"jp": "", "ko": ""}]
    open_ = False
    def flush():
        nonlocal lines, open_
        if open_:
            screens.append(lines)
        lines = [{"jp": "", "ko": ""}]; open_ = False
    for s in segs:
        if "jp" in s:
            lines[-1]["jp"] += s["jp"]
            lines[-1]["ko"] += (s.get("ko") or "")
            open_ = True
        elif _is_pure_newline(s):
            if open_:
                lines.append({"jp": "", "ko": ""})
        else:
            flush()
    flush()
    return screens


# ── 대상 판별 ────────────────────────────────────────────────
def is_target(path, segs):
    """나레이션 재번역 대상인가."""
    if "/set/" in path:
        return False, None
    screens, info = split_screens(segs)
    if not screens:
        return False, None
    if info["has_inline11"] or info["decode_err"]:
        return False, info          # 인라인 명령/디코드오류 → 구조 위험, 제외
    jp_all = "".join(screen_jp_joined(s) for s in screens)
    nlines = sum(len(s) for s in screens)
    if len(jp_all) < 45 or nlines < 2:
        return False, info
    # 번호표/기호표 제외(숫자·기호·전각영숫자 위주)
    import re
    if re.fullmatch(r'[\dＡ-Ｚａ-ｚ０-９△▲　\s\[\]【】xXｘＸ×・，、。！？／。\-]+', jp_all):
        return False, info
    return True, info


# ── 재조립(구조 보존) ────────────────────────────────────────
def rebuild_segs(orig_segs, korean_screens):
    """orig_segs 의 경계 제어를 보존하고, 화면별 텍스트를 korean_screens 로 교체.
    korean_screens: 화면당 문자열(여러 줄은 '\\n'). 길이 == 화면 수 여야 함.
    """
    out = []
    si = 0
    lines = [""]
    open_ = False
    def flush():
        nonlocal lines, open_, si
        if open_:
            jp = "\n".join(lines)
            ko = korean_screens[si] if si < len(korean_screens) else ""
            out.append({"jp": jp, "ko": ko})
            si += 1
        lines = [""]; open_ = False
    for s in orig_segs:
        if "jp" in s:
            lines[-1] += s["jp"]; open_ = True
        elif _is_pure_newline(s):
            if open_:
                lines.append("")
            else:
                out.append(s)        # 화면 밖 선행 줄바꿈 보존
        else:
            flush()
            out.append(s)            # 경계 제어 그대로 보존
    flush()
    if si != len(korean_screens):
        raise ValueError(f"화면 수 불일치: segs={si} vs korean={len(korean_screens)}")
    return out


# ── 검증 ────────────────────────────────────────────────────
def validate_korean(korean_screens, ks):
    issues = []
    for i, sc in enumerate(korean_screens):
        ls = sc.split("\n")
        if len(ls) > MAX_LINES_PER_SCREEN:
            issues.append(f"화면{i}: {len(ls)}줄(>{MAX_LINES_PER_SCREEN})")
        for j, ln in enumerate(ls):
            if not ln.strip():
                issues.append(f"화면{i} 줄{j}: 빈 줄")
            if len(ln) > MAX_LINE:
                issues.append(f"화면{i} 줄{j}: {len(ln)}자(>{MAX_LINE}) [{ln}]")
            for ch in ln:
                if not is_encodable(ch, ks):
                    issues.append(f"화면{i} 줄{j}: 인코딩불가 {ch!r}")
    return issues


def greedy_wrap(text, limit=MAX_LINE):
    """공백 기준 그리디 줄바꿈(코드 폴백). 단어가 limit 초과면 강제분할."""
    words = text.split(" ")
    lines = []; cur = ""
    for wd in words:
        while len(wd) > limit:
            if cur:
                lines.append(cur); cur = ""
            lines.append(wd[:limit]); wd = wd[limit:]
        cand = wd if not cur else cur + " " + wd
        if len(cand) <= limit:
            cur = cand
        else:
            if cur: lines.append(cur)
            cur = wd
    if cur: lines.append(cur)
    return lines


# ── 자체검증: 구조 무손실 ────────────────────────────────────
def _entry_jp_bytes(orig_segs):
    """원본 일본어 바이트(ko 무시): from_segments 가 ko 없으면 jp(shift_jis) 출력."""
    jp_only = []
    for s in orig_segs:
        if "jp" in s:
            jp_only.append({"jp": s["jp"], "ko": ""})
        else:
            jp_only.append(s)
    return from_segments(jp_only, {})

def _rebuilt_jp_bytes(orig_segs):
    """korean_screens = 원문 화면(줄을 '\\n')으로 재조립 후 바이트."""
    screens, _ = split_screens(orig_segs)
    kor = ["\n".join(sc) for sc in screens]
    new = rebuild_segs(orig_segs, kor)
    return from_segments(new, {})

def self_test(jpath=None, sample=400):
    jpath = jpath or os.path.join(HERE, "translation.json")
    d = json.load(open(jpath, encoding="utf-8"))
    ks = load_ks()
    n_target = 0; n_test = 0; mism = []; skipped_info = {"inline11":0,"decode":0}
    for f in d["files"]:
        for ei, e in enumerate(f["entries"]):
            ok, info = is_target(f["path"], e["segs"])
            if info and info.get("has_inline11"): skipped_info["inline11"] += 1
            if info and info.get("decode_err"): skipped_info["decode"] += 1
            if not ok:
                continue
            n_target += 1
            if n_test < sample:
                try:
                    a = _entry_jp_bytes(e["segs"])
                    b = _rebuilt_jp_bytes(e["segs"])
                    n_test += 1
                    if a != b:
                        mism.append((f["path"], ei, a.hex()[:60], b.hex()[:60]))
                except Exception as ex:
                    mism.append((f["path"], ei, "EXC", str(ex)))
    print(f"대상 엔트리: {n_target}")
    print(f"구조 라운드트립 검사: {n_test}개")
    print(f"  불일치: {len(mism)}")
    for m in mism[:8]:
        print("   ", m)
    print(f"제외(inline11): {skipped_info['inline11']}  제외(decode): {skipped_info['decode']}")
    return len(mism) == 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["selftest"])
    ap.add_argument("--sample", type=int, default=400)
    a = ap.parse_args()
    if a.cmd == "selftest":
        ok = self_test(sample=a.sample)
        print("OK" if ok else "FAIL")
        sys.exit(0 if ok else 1)
