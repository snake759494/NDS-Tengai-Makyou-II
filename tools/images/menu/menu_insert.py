#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""menu_insert.py — 수정한 메뉴 PNG를 ROM에 다시 삽입.

menu_extract.py로 뽑아 한글로 편집한 PNG들을 ROM에 써넣는다.
폴더 안에 있는 PNG만 적용하므로 일부만 편집해도 된다.

사용법:  python menu_insert.py 입력롬.nds PNG폴더/ 출력롬.nds
대상:    mainmenu.png / command_NN.png / kiten.png
"""
import sys, os, struct as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import tools, cmp

def bgr555(b):
    out=[]
    for i in range(0,len(b)-1,2):
        c=b[i]|(b[i+1]<<8); r=c&0x1F; g=(c>>5)&0x1F; bl=(c>>10)&0x1F
        out.append((r<<3,g<<3,bl<<3))   # melonDS와 동일한 단순 5→8비트 확장
    return out

def strip_pal_header(pdec):
    """.pal 앞 4바이트 뱅크수 헤더(NN 00 00 00)가 있으면 제거 (추출과 동일 정렬)."""
    if len(pdec)>=4 and pdec[1:4]==b'\x00\x00\x00' and 4+pdec[0]*32==len(pdec):
        return pdec[4:]
    return pdec

def synth_pal(n=16):
    base=[(0,0,0),(80,80,80),(160,40,40),(40,160,40),(40,40,160),(255,255,255),
          (200,200,40),(200,40,200),(40,200,200),(255,150,40),(150,40,255),(40,255,150),
          (120,120,200),(200,120,120),(120,200,120),(220,220,220)]
    return base[:n]

def load_idx(path, pal):
    """PNG를 팔레트 인덱스 2D 배열로. P모드는 인덱스 직접, RGB는 최근접 매칭."""
    im=Image.open(path)
    if im.mode=='P':
        return np.array(im,dtype=np.uint8)
    arr=np.array(im.convert('RGB'),dtype=int); h,w,_=arr.shape
    pa=np.array(pal,dtype=int)
    flat=arr.reshape(-1,3)
    d=((flat[:,None,:]-pa[None,:,:])**2).sum(2)
    return d.argmin(1).reshape(h,w).astype(np.uint8)

def pack_tile4(b):
    o=bytearray()
    for y in range(8):
        for x in range(0,8,2):
            o.append((int(b[y,x])&0xF)|((int(b[y,x+1])&0xF)<<4))
    return bytes(o)

def insert_mainmenu(rom,n2f,png,COLS=8):
    fid=n2f['mainmenu.obc']
    dec=bytearray(tools.lz10_dec(tools.read_file(rom,fid)[0]))
    header=bytes(dec[:456]); pal=bgr555(dec[8:456])
    idx=load_idx(png,pal); td=bytearray(len(dec)-456); nw=(len(dec)-456)//64//8
    for w in range(nw):
        wr,wc=divmod(w,COLS)
        for t in range(8):
            tr,tc=divmod(t,4)
            for y in range(8):
                for x in range(8):
                    td[(w*8+t)*64+y*8+x]=int(idx[wr*16+tr*8+y, wc*32+tc*8+x])
    new=header+bytes(td); comp=tools.lz10_store(new)
    assert tools.lz10_dec(comp)==new
    tools.append_repoint(rom,fid,comp); return True

def insert_command(rom,n2f,png,n):
    nm=f"bs_obj_command_icon{n}.cobj"
    if nm not in n2f: return False
    pal=synth_pal(); idx=load_idx(png,pal)
    tiles=[bytearray(32) for _ in range(8)]
    for t in range(8):
        tr,tc=divmod(t,4)
        for y in range(8):
            for x in range(0,8,2):
                v0=int(idx[tr*8+y, tc*8+x])&0xF; v1=int(idx[tr*8+y, tc*8+x+1])&0xF
                tiles[t][y*4+x//2]=v0|(v1<<4)
    new=b"".join(tiles); comp=tools.lz10_store(new)
    tools.append_repoint(rom,n2f[nm],comp); return True

def insert_kiten(rom,png):
    paths=tools.parse_fnt(bytes(rom))
    fc=[f for f,p in paths.items() if p.endswith('kiten/bg00/char00.chr')][0]
    fs=[f for f,p in paths.items() if p.endswith('kiten/bg00/scrn00.scr')][0]
    fp=[f for f,p in paths.items() if p.endswith('kiten/bg00/palt.pal')][0]
    cdec=cmp.cmp_decode(tools.read_file(rom,fc)[0]); orig_tiles=(len(cdec)-4)//32
    sdec=cmp.cmp_decode(tools.read_file(rom,fs)[0])
    praw=tools.read_file(rom,fp)[0]; pdec=cmp.cmp_decode(praw) if praw[:3]==b'CMP' else praw
    pdec=strip_pal_header(pdec)
    pal=bgr555(pdec)
    while len(pal)<256: pal.append((255,0,255))
    idx=load_idx(png,pal)
    # 뱅크 보존 retile
    tiles=[]; look={}; tm=[]
    for r in range(32):
        for c in range(32):
            blk=idx[r*8:r*8+8,c*8:c*8+8]
            pl=int(np.bincount((blk//16).flatten().astype(int)).argmax())
            sub=(blk.astype(int)-pl*16).clip(0,15).astype(np.uint8)
            found=None
            for hf,vf in [(0,0),(1,0),(0,1),(1,1)]:
                v=sub
                if hf: v=v[:,::-1]
                if vf: v=v[::-1]
                k=pack_tile4(v)
                if k in look: found=(look[k],hf,vf); break
            if found is None:
                k=pack_tile4(sub); ti=len(tiles); tiles.append(k); look[k]=ti; found=(ti,0,0)
            ti,hf,vf=found; tm.append(ti|(hf<<10)|(vf<<11)|(pl<<12))
    if len(tiles)>1024: raise RuntimeError("kiten 타일 수 초과")
    while len(tiles)<orig_tiles: tiles.append(bytes(32))
    char_new=st.pack('<I',len(tiles)*32)+b''.join(tiles)
    scrn_new=sdec[:4]+b''.join(st.pack('<H',e) for e in tm)
    cc=cmp.cmp_encode_rle(char_new,ver=1); sc=cmp.cmp_encode_rle(scrn_new,ver=1)
    assert cmp.cmp_decode(cc)==char_new and cmp.cmp_decode(sc)==scrn_new
    tools.append_repoint(rom,fc,cc); tools.append_repoint(rom,fs,sc); return True

def main():
    if len(sys.argv)<4:
        print(__doc__); sys.exit("사용법: python menu_insert.py 입력롬.nds PNG폴더/ 출력롬.nds")
    rom=bytearray(open(sys.argv[1],'rb').read()); d=sys.argv[2]; out=sys.argv[3]
    n2f={p.rsplit('/',1)[-1]:f for f,p in tools.parse_fnt(rom).items()}
    done=[]
    if os.path.exists(os.path.join(d,'mainmenu.png')):
        insert_mainmenu(rom,n2f,os.path.join(d,'mainmenu.png')); done.append('mainmenu')
    nc=0
    for n in range(1,18):
        p=os.path.join(d,f'command_{n:02d}.png')
        if os.path.exists(p) and insert_command(rom,n2f,p,n): nc+=1
    if nc: done.append(f'command×{nc}')
    if os.path.exists(os.path.join(d,'kiten.png')):
        insert_kiten(rom,os.path.join(d,'kiten.png')); done.append('kiten')
    open(out,'wb').write(rom)
    print(f"삽입 완료: {', '.join(done) if done else '(PNG 없음)'} -> {out} ({len(rom):,}B)")

if __name__=='__main__': main()
