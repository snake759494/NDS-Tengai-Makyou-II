#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""banner_tool.py — 천외마경II 지명 배너 프레임 너비 확인/조절 도구

지명 배너의 프레임(테두리 판)은 게임이 **가장 넓은 행의 글자 수**에 맞춰
자동으로 늘립니다. 가로 너비를 정하는 별도 코드는 없습니다.
( 배너 헤더 `16 00 [p1] 00 [p2] 00` 의 p1=세로레이아웃(5=후리가나행 있음/8=없음),
  p2=8=박스 높이. 둘 다 가로 너비와 무관. )

따라서 프레임을 넓히거나 좁히려면 **행 텍스트의 글자 폭**을 바꾸면 됩니다.
전각 공백 `　`(U+3000) 한 칸 = 한 글자 폭.

사용법:
  # 1) 모든 지명 배너와 현재 프레임 너비 보기
  python banner_tool.py list                       # 전체
  python banner_tool.py list 아키바                  # 이름으로 검색

  # 2) 특정 배너의 본문 행을 원하는 너비로 (전각 공백을 좌우 균등 패딩)
  python banner_tool.py pad <인덱스> <목표너비>       # 예: pad 12 10

  # 3) 특정 배너의 한 행 텍스트를 직접 지정(직접 　 패딩 포함 가능)
  python banner_tool.py setrow <인덱스> <행번호> "텍스트"

  * <인덱스>는 list 가 보여주는 맨 앞 번호.
  * 수정 시 translation.json 을 자동 백업(.bak)하고 갱신합니다.
  * 수정 후 통합 패키지(patch.py)로 다시 빌드하면 반영됩니다.

기본 대상: ./dialogue/translation.json (없으면 ./translation.json, ./data/translation.json)
"""
import sys, os, json, shutil

CANDS = ["dialogue/translation.json", "translation.json", "data/translation.json"]


def find_json():
    here = os.path.dirname(os.path.abspath(__file__))
    for c in CANDS:
        p = os.path.join(here, c)
        if os.path.exists(p):
            return p
    for c in CANDS:
        if os.path.exists(c):
            return os.path.abspath(c)
    sys.exit("[오류] translation.json 을 찾을 수 없습니다.")


def is_banner(e):
    return (e.get("segs") and "c" in e["segs"][0]
            and bytes.fromhex(e["segs"][0]["c"])[0] == 0x16
            and len(bytes.fromhex(e["segs"][0]["c"])) >= 6)


def hdr(e):
    b = bytes.fromhex(e["segs"][0]["c"])
    return b[2] | (b[3] << 8), b[4] | (b[5] << 8)


def split_rows(e):
    """행(row) 단위로 (텍스트세그 인덱스 리스트) 반환. 0x0D/0x0C 가 행 구분."""
    rows = [[]]
    for i, s in enumerate(e["segs"]):
        if "c" in s:
            if bytes.fromhex(s["c"])[0] in (0x0d, 0x0c):
                rows.append([])
        elif "jp" in s:
            rows[-1].append(i)
    return [r for r in rows if r]


def row_text(e, row, field="ko"):
    return "".join(e["segs"][i].get(field, "") for i in row)


def width(txt):
    # 전각 공백 포함, 글자 1개 = 폭 1 (게임 폰트가 고정폭)
    return len(txt)


def collect(doc):
    out = []
    for f in doc["files"]:
        for e in f["entries"]:
            if is_banner(e):
                out.append((f["path"], e))
    return out


def cmd_list(doc, needle=None):
    items = collect(doc)
    idx = 0
    for path, e in items:
        rows = split_rows(e)
        kos = [row_text(e, r, "ko") for r in rows]
        jps = [row_text(e, r, "jp") for r in rows]
        if not kos:
            idx += 1
            continue
        if needle and needle not in "".join(kos) and needle not in "".join(jps):
            idx += 1
            continue
        p1, p2 = hdr(e)
        frame = max((width(k) for k in kos), default=0)
        print(f"[{idx:3d}] {path.split('/')[-1]:14s} e{e['i']:<3d} p1={p1} p2={p2}  프레임={frame}자")
        for ri, (k, j) in enumerate(zip(kos, jps)):
            tag = "후리가나" if (len(rows) >= 2 and ri == 0) else "본문    "
            print(f"        행{ri} {tag} 폭{width(k):2d}  ko「{k}」  (jp「{j}」)")
        idx += 1


def save(doc, jpath):
    shutil.copy(jpath, jpath + ".bak")
    json.dump(doc, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  → 저장 완료 (백업: {os.path.basename(jpath)}.bak)")
    print("    이제 patch.py 로 다시 빌드하면 반영됩니다.")


def get_banner(doc, index):
    items = collect(doc)
    if index < 0 or index >= len(items):
        sys.exit(f"[오류] 인덱스 범위 초과 (0~{len(items)-1}). 먼저 list 로 확인하세요.")
    return items[index]


def cmd_pad(doc, jpath, index, target):
    path, e = get_banner(doc, index)
    rows = split_rows(e)
    main = rows[-1]                      # 본문 행
    cur = row_text(e, main, "ko")
    content = cur.replace("\u3000", "")  # 기존 전각공백 제거한 알맹이
    if width(content) > target:
        sys.exit(f"[오류] 목표 너비 {target} < 본문 글자수 {width(content)}. 더 크게 잡으세요.")
    pad = target - width(content)
    left = pad // 2
    right = pad - left
    new = "\u3000" * left + content + "\u3000" * right
    # 본문 행의 첫 텍스트 세그에 전체를 넣고 나머지 세그는 비움
    first = main[0]
    e["segs"][first]["ko"] = new
    for i in main[1:]:
        e["segs"][i]["ko"] = ""
    print(f"[{index}] {path.split('/')[-1]} e{e['i']} 본문 행 → 너비 {target} 로 패딩")
    print(f"    ko「{new}」  (전각공백 좌{left}/우{right})")
    save(doc, jpath)


def cmd_setrow(doc, jpath, index, rownum, text):
    path, e = get_banner(doc, index)
    rows = split_rows(e)
    if rownum < 0 or rownum >= len(rows):
        sys.exit(f"[오류] 행 번호 범위 초과 (0~{len(rows)-1}).")
    row = rows[rownum]
    e["segs"][row[0]]["ko"] = text
    for i in row[1:]:
        e["segs"][i]["ko"] = ""
    print(f"[{index}] {path.split('/')[-1]} e{e['i']} 행{rownum} → ko「{text}」 (폭 {width(text)})")
    save(doc, jpath)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    jpath = find_json()
    doc = json.load(open(jpath, encoding="utf-8"))
    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list(doc, sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "pad":
        cmd_pad(doc, jpath, int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "setrow":
        cmd_setrow(doc, jpath, int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
    else:
        print(__doc__)
        sys.exit(f"[오류] 알 수 없는 명령: {cmd}")


if __name__ == "__main__":
    main()
