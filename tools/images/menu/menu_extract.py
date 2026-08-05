#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""menu_extract.py — 천외마경II 卍MARU (ATMJ) 메뉴 이미지를 PNG로 추출.

ROM의 메뉴 그래픽(일본어 원본)을 편집 가능한 PNG로 뽑아낸다.
이 PNG들을 이미지 편집기로 한글로 고친 뒤 menu_insert.py로 다시 삽입한다.

사용법:  python menu_extract.py 입력롬.nds 출력폴더/
산출물:
  mainmenu.png        메인/필드/하단/아이콘 등 96워드 그리드 (8bpp, 256x192)
  command_NN.png      전투 명령 아이콘 1~17 (각 32x16)
  kiten.png           시작 선택 화면 (256x256)
  _palette_mainmenu.png / _palette_command.png  팔레트 참고용 색상표
"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import tools, cmp

def bgr555(b):
    out=[]
    for i in range(0,len(b)-1,2):
        c=b[i]|(b[i+1]<<8)
        r=c&0x1F; g=(c>>5)&0x1F; bl=(c>>10)&0x1F
        out.append((r<<3,g<<3,bl<<3))   # melonDS와 동일한 단순 5→8비트 확장
    return out

def strip_pal_header(pdec):
    """.pal 앞 4바이트 뱅크수 헤더(NN 00 00 00, NN×16색)가 있으면 제거.
    이걸 빼지 않으면 색이 2칸씩 밀려 화면과 다른 색으로 추출된다."""
    if len(pdec)>=4 and pdec[1:4]==b'\x00\x00\x00' and 4+pdec[0]*32==len(pdec):
        return pdec[4:]
    return pdec

def save_p(arr, pal, path):
    im=Image.fromarray(arr.astype(np.uint8),'P')
    flat=[]
    for c in pal: flat+=list(c)
    while len(flat)<768: flat+=[255,0,255]   # 남는 칸은 마젠타(미사용 표시)
    im.putpalette(flat[:768]); im.save(path)

def synth_pal(n=16):
    # 16색 합성 팔레트: 0=검정(배경), 5=흰색(글자), 나머지는 구분되는 색
    base=[(0,0,0),(80,80,80),(160,40,40),(40,160,40),(40,40,160),(255,255,255),
          (200,200,40),(200,40,200),(40,200,200),(255,150,40),(150,40,255),(40,255,150),
          (120,120,200),(200,120,120),(120,200,120),(220,220,220)]
    return base[:n]

def extract_mainmenu(rom,n2f,outdir,COLS=8):
    dec=tools.lz10_dec(tools.read_file(rom,n2f['mainmenu.obc'])[0])
    pal=bgr555(dec[8:456])
    # 메뉴 글자 본체 인덱스(idx36~)는 내장(맵용) 팔레트엔 녹색으로 들어 있으나,
    # 게임이 메뉴를 그릴 땐 청록->흰 그라데이션(idx32~35)을 잇는 '흰색'이다.
    # 이 인덱스들은 글자에만 쓰이므로(맵 그래픽 무관) 화면과 같게 흰색으로 표시.
    if len(pal)>36 and min(pal[35])>=200:
        i=36
        while i<len(pal) and pal[i]==(0,248,0):
            pal[i]=(248,248,248); i+=1
    td=dec[456:]; nt=len(td)//64; nw=nt//8
    rows=(nw+COLS-1)//COLS
    img=np.zeros((rows*16,COLS*32),np.uint8)
    for w in range(nw):
        wr,wc=divmod(w,COLS)
        for t in range(8):
            tr,tc=divmod(t,4); tile=td[(w*8+t)*64:(w*8+t)*64+64]
            for y in range(8):
                for x in range(8):
                    img[wr*16+tr*8+y, wc*32+tc*8+x]=tile[y*8+x]
    save_p(img,pal,os.path.join(outdir,'mainmenu.png'))
    # 팔레트 참고표
    sw=np.zeros((16*8,16*8),np.uint8)
    for i in range(min(len(pal),256)):
        r,c=divmod(i,16); sw[r*8:r*8+8,c*8:c*8+8]=i
    save_p(sw,pal,os.path.join(outdir,'_palette_mainmenu.png'))
    print(f"  mainmenu.png  ({COLS*32}x{rows*16}, {nw}워드, 팔레트 {len(pal)}색)")

def extract_commands(rom,n2f,outdir):
    pal=synth_pal()
    got=0
    for n in range(1,18):
        nm=f"bs_obj_command_icon{n}.cobj"
        if nm not in n2f: continue
        dec=tools.lz10_dec(tools.read_file(rom,n2f[nm])[0])
        img=np.zeros((16,32),np.uint8)
        for t in range(8):
            tr,tc=divmod(t,4)
            for j in range(32):
                b=dec[t*32+j]; y=j//4; xx=(j%4)*2
                img[tr*8+y, tc*8+xx]=b&0xF
                img[tr*8+y, tc*8+xx+1]=b>>4
        save_p(img,pal,os.path.join(outdir,f'command_{n:02d}.png'))
        got+=1
    save_p(np.array([[i for i in range(16)]]*8,np.uint8),pal,os.path.join(outdir,'_palette_command.png'))
    print(f"  command_01~ ({got}개, 32x16, 합성16색: 0=배경 5=글자)")

def _render_indexed(cdec, sdec):
    """char(타일)+scrn(타일맵)을 256x256 인덱스 이미지로. 뱅크(pl) 반영."""
    td=cdec[4:]; nt=len(td)//32
    tiles=np.zeros((nt,8,8),np.uint8)
    for k in range(nt):
        for j in range(32):
            b=td[k*32+j]
            tiles[k,j//4,(j%4)*2]=b&0xF
            tiles[k,j//4,(j%4)*2+1]=b>>4
    tm=sdec[4:]; ne=len(tm)//2
    idx=np.zeros((256,256),np.uint8)
    for i in range(ne):
        e=tm[i*2]|(tm[i*2+1]<<8)
        ti=e&0x3FF; hf=(e>>10)&1; vf=(e>>11)&1; pl=(e>>12)&0xF
        r,c=divmod(i,32)
        if ti<nt:
            t=tiles[ti].copy()
            if hf: t=t[:,::-1]
            if vf: t=t[::-1]
            idx[r*8:r*8+8,c*8:c*8+8]=t+pl*16
    return idx

def extract_kiten(rom,n2f,outdir):
    paths=tools.parse_fnt(bytes(rom))
    fc=[f for f,p in paths.items() if p.endswith('kiten/bg00/char00.chr')][0]
    fs=[f for f,p in paths.items() if p.endswith('kiten/bg00/scrn00.scr')][0]
    fp=[f for f,p in paths.items() if p.endswith('kiten/bg00/palt.pal')][0]
    cdec=cmp.cmp_decode(tools.read_file(rom,fc)[0])
    sdec=cmp.cmp_decode(tools.read_file(rom,fs)[0])
    praw=tools.read_file(rom,fp)[0]
    pdec=cmp.cmp_decode(praw) if praw[:3]==b'CMP' else praw
    pdec=strip_pal_header(pdec)
    pal=bgr555(pdec)
    while len(pal)<256: pal.append((255,0,255))
    idx=_render_indexed(cdec,sdec)
    save_p(idx,pal,os.path.join(outdir,'kiten.png'))
    print(f"  kiten.png     (256x256, 팔레트 {len(pdec)//2}색)")

def main():
    if len(sys.argv)<3:
        print(__doc__); sys.exit("사용법: python menu_extract.py 입력롬.nds 출력폴더/")
    rom=bytearray(open(sys.argv[1],'rb').read())
    outdir=sys.argv[2]; os.makedirs(outdir,exist_ok=True)
    n2f={p.rsplit('/',1)[-1]:f for f,p in tools.parse_fnt(rom).items()}
    print("메뉴 이미지 추출:")
    extract_mainmenu(rom,n2f,outdir)
    extract_commands(rom,n2f,outdir)
    extract_kiten(rom,n2f,outdir)
    print(f"완료 -> {outdir}")

if __name__=='__main__': main()
