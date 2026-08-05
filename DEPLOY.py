#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPLOY.py — 천외마경II 卍MARU 한국어 패치 빌드 (단일 진입점).

`translation/번역_마스터.json` 하나만 고치고 이 스크립트를 실행하면
패치 ROM과 배포용 xdelta 패치가 다시 만들어집니다.

  python DEPLOY.py --jp 원본_ATMJ.nds
  python DEPLOY.py --jp 원본_ATMJ.nds --out build/KR.nds --patch build/KR.xdelta

동작
  1) 일본판 원본 ROM을 base 로 읽는다.
  2) **이미지·폰트 레이어**(지도/메인메뉴/전투/세이브로드 그래픽 + 한글 글꼴 37개 파일)를
     기존 배포 패치(dist/*.xdelta)를 원본에 적용해 만든 "참조 ROM"에서 가져온다.
     → 저장소에 게임 데이터를 두지 않고도 그래픽 한글화를 그대로 재현한다.
     (직접 만든 참조 ROM 이 있으면 --ref 로 지정)
  3) 마스터의 텍스트를 적용한다.
       dialogue → .scs 대사 컨테이너 재조립
       arm9     → arm9.bin 시스템/메뉴/지명 문자열 (원문 매칭 후 바이트 보존 치환)
       overlay  → 오프닝 자막·저장 UI·전투 커맨드
  4) ROM 저장 + (기본) 원본 대비 xdelta 패치 생성.

준비물:  python -m pip install ndspy pyxdelta
"""
import argparse
import glob
import hashlib
import io
import json
import os
import re
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, 'tools')
sys.path.insert(0, TOOLS)

import ndspy.rom                                   # noqa: E402
from tengai_cobj_font import decode_font           # noqa: E402
from font_mapping import build_mapping             # noqa: E402
from scs_repack import rebuild                     # noqa: E402
from scs_segment import from_segments              # noqa: E402
import arm9_text                                   # noqa: E402

MASTER = os.path.join(HERE, 'translation', '번역_마스터.json')
KS = os.path.join(TOOLS, 'ks2350.txt')
DIST = os.path.join(HERE, 'dist')
FONT_FID = 9138

# 그래픽·폰트 파일(텍스트가 아니라 픽셀이라 마스터 대상이 아님) — 참조 ROM 에서 복사
IMAGE_FIDS = [
    2764,                       # data/usd/fuw_bg.chr        지도 모드 상단 일본지도(지방명)
    2766,                       # data/usd/mainmenu.obc      메인메뉴 라벨
    *range(3940, 3957),         # bs_obj_command_icon1~17    전투 명령 아이콘
    3966, 3967, 3968, 3969,     # bs_obj_name_p1~4           전투 스탯 이름판
    9138,                       # font12_GothicW3_bit.cobj   한글 글꼴(한자 슬롯에 주입됨)
    9140, 9143,                 # uno_all/kiten/bg00         시작 선택 화면
    9161, 9163, 9165,           # saveload/btn_obj/btn01~03  세이브·로드 버튼
    9186, 9188, 9190, 9192,     # saveload/mes_obj/mes01~08  세이브·로드 메시지
    9194, 9196, 9198, 9200,
]


def newest_dist_patch():
    """dist/ 에서 버전이 가장 높은 xdelta 패치 경로."""
    cands = glob.glob(os.path.join(DIST, '*.xdelta'))
    if not cands:
        return None

    def ver(p):
        m = re.search(r'v(\d+)\.(\d+)', os.path.basename(p))
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    return max(cands, key=ver)


def make_reference(jp_path, ref_patch, workdir):
    """원본 ROM + 배포 패치 → 참조 ROM(이미지·폰트 레이어 공급원)."""
    import pyxdelta
    out = os.path.join(workdir, '_reference.nds')
    print('  참조 ROM 생성: %s' % os.path.basename(ref_patch))
    ok = pyxdelta.decode(jp_path, ref_patch, out)
    if not ok or not os.path.exists(out):
        raise SystemExit('xdelta 적용 실패 — 원본 ROM 이 깨끗한 일본판(ATMJ)인지 확인하세요.')
    return out


def clean_segs(segs):
    """게임 대사는 전각만 지원 → 반각 마침표 제거(사용자 띄어쓰기/전각공백은 유지)."""
    out = []
    for s in segs:
        s2 = dict(s)
        if s2.get('ko'):
            s2['ko'] = s2['ko'].replace('.', '')
        out.append(s2)
    return out


def deploy(jp_path, out_path, patch_path, ref_path=None, ref_patch=None):
    if not os.path.exists(jp_path):
        raise SystemExit('원본 ROM 을 찾을 수 없습니다: %s' % jp_path)
    print('마스터 로드:', MASTER)
    master = json.load(open(MASTER, encoding='utf-8'))

    print('원본(JP) 로드:', jp_path)
    rom = ndspy.rom.NintendoDSRom.fromFile(jp_path)

    with tempfile.TemporaryDirectory() as workdir:
        # 1) 이미지·폰트 레이어
        if ref_path is None:
            ref_patch = ref_patch or newest_dist_patch()
            if not ref_patch:
                raise SystemExit('dist/ 에 배포 패치가 없습니다. --ref 로 참조 ROM 을 지정하세요.')
            ref_path = make_reference(jp_path, ref_patch, workdir)
        print('이미지·폰트 레이어:', os.path.basename(ref_path))
        ref = ndspy.rom.NintendoDSRom.fromFile(ref_path)
        for fid in IMAGE_FIDS:
            rom.files[fid] = bytes(ref.files[fid])
        print('  복사한 그래픽/폰트 파일:', len(IMAGE_FIDS))
        del ref

        # 2) 한글 매핑(한자 SJIS 슬롯 재매핑)
        hangul = list(open(KS, encoding='utf-8').read().strip())
        hset = set(hangul)
        mapping = build_mapping(decode_font(rom.files[FONT_FID]), hangul)

        missing = set()
        for f in master['dialogue']['files']:
            for e in f['entries']:
                for s in e['segs']:
                    for ch in (s.get('ko') or ''):
                        if '가' <= ch <= '힣' and ch not in hset:
                            missing.add(ch)
        if missing:
            print('  !! 글꼴에 없는 음절(KS X 1001 밖):', ''.join(sorted(missing)))

        # 3-a) 대사
        n_dlg = 0
        for f in master['dialogue']['files']:
            if not any((s.get('ko') or '').strip()
                       for e in f['entries'] for s in e['segs'] if 'jp' in s):
                continue
            bodies = [from_segments(clean_segs(e['segs']), mapping.syl2sjis)
                      for e in sorted(f['entries'], key=lambda x: x['i'])]
            rom.files[f['file_id']] = rebuild(f.get('reserved', 0), bodies)
            n_dlg += 1
        print('  대사 파일 재조립:', n_dlg)

        # 3-b) arm9
        a9 = bytearray(rom.arm9)
        applied, errs = arm9_text.apply_entries(a9, master['arm9']['entries'], mapping.syl2sjis)
        rom.arm9 = bytes(a9)
        print('  arm9 텍스트:', applied, '적용' + (', 오류 %d' % len(errs) if errs else ''))
        for off, msg in errs[:8]:
            print('    !', hex(off), msg)

        # 3-c) overlay
        for oid, info in master['overlay'].items():
            fid = info['fileID']
            ov = bytearray(rom.files[fid])
            a2, e2 = arm9_text.apply_entries(ov, info['entries'], mapping.syl2sjis)
            rom.files[fid] = bytes(ov)
            print('  오버레이 ovl%s(fid%d):' % (oid, fid), a2,
                  '적용' + (', 오류 %d' % len(e2) if e2 else ''))
            for off, msg in e2[:5]:
                print('    !', hex(off), msg)

        # 4) 저장
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or '.', exist_ok=True)
        rom.saveToFile(out_path)

    md5 = hashlib.md5(open(out_path, 'rb').read()).hexdigest()
    print('저장: %s (%s B, md5 %s)' % (out_path, format(os.path.getsize(out_path), ','), md5))

    if patch_path:
        import pyxdelta
        pyxdelta.run(jp_path, out_path, patch_path)
        print('패치: %s (%s B)' % (patch_path, format(os.path.getsize(patch_path), ',')))
        # 역검증: 원본 + 패치 == 방금 만든 ROM
        with tempfile.TemporaryDirectory() as wd:
            rt = os.path.join(wd, '_verify.nds')
            if pyxdelta.decode(jp_path, patch_path, rt) and os.path.exists(rt):
                same = hashlib.md5(open(rt, 'rb').read()).hexdigest() == md5
                print('패치 역검증:', 'OK' if same else '!! 불일치')


def main():
    ap = argparse.ArgumentParser(description='천외마경II 卍MARU 한국어 패치 빌드')
    ap.add_argument('--jp', required=True, help='깨끗한 일본판 원본 ROM (ATMJ)')
    ap.add_argument('--out', default=os.path.join(HERE, 'build', 'Tengai_Makyou_II_KR.nds'),
                    help='출력 ROM 경로')
    ap.add_argument('--patch', default=os.path.join(HERE, 'build', 'Tengai_Makyou_II_KR.xdelta'),
                    help='생성할 xdelta 패치 경로 (--no-patch 로 생략)')
    ap.add_argument('--no-patch', action='store_true', help='xdelta 패치를 만들지 않음')
    ap.add_argument('--ref', default=None,
                    help='이미지·폰트를 가져올 참조 ROM (미지정 시 dist 패치로 자동 생성)')
    ap.add_argument('--ref-patch', default=None,
                    help='참조 ROM 을 만들 때 쓸 배포 패치 (기본: dist 의 최신 버전)')
    a = ap.parse_args()
    deploy(a.jp, a.out, None if a.no_patch else a.patch, a.ref, a.ref_patch)


if __name__ == '__main__':
    main()
