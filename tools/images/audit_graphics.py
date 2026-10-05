"""Extract original graphics and OAM-assembled save/load frames without editing pixels."""
from pathlib import Path
import sys, json, hashlib, struct, argparse
import numpy as np
from PIL import Image
import ndspy.rom
sys.path.insert(0, str(Path(__file__).parent / 'menu'))
import tools, cmp, menu_extract as ex

def decode(b):
    return cmp.cmp_decode(b) if b[:3] == b'CMP' else tools.lz10_dec(b) if b[:1] == b'\x10' else b

def tiles4(b):
    a = np.frombuffer(b, np.uint8)
    out = np.empty(len(a)*2, np.uint8)
    out[::2] = a & 15; out[1::2] = a >> 4
    return out.reshape(-1,8,8)

SIZES = [[(8,8),(16,16),(32,32),(64,64)],[(16,8),(32,8),(32,16),(64,32)],[(8,16),(8,32),(16,32),(32,64)]]

def obj_frames(ani, tiles):
    count = struct.unpack_from('<H',ani,8)[0]
    offsets = struct.unpack_from('<'+'I'*count,ani,20)
    frames=[]
    for off in offsets:
        n,w,h=struct.unpack_from('<3H',ani,off)
        records=[]
        for i in range(n):
            a0,a1,ti,extra=struct.unpack_from('<4H',ani,off+6+i*8)
            sw,sh=SIZES[a0>>14][a1>>14]
            x=a1&511; y=a0&255
            if x>=256: x-=512
            if y>=128: y-=256
            records.append(dict(x=x,y=y,w=sw,h=sh,tile=ti,extra=extra,hflip=bool(a1&4096),vflip=bool(a1&8192)))
        x0=min(0,min(r['x'] for r in records)); y0=min(0,min(r['y'] for r in records))
        width=max(w,max(r['x']+r['w'] for r in records))-x0
        height=max(h,max(r['y']+r['h'] for r in records))-y0
        canvas=np.zeros((height,width),np.uint8)
        for r in reversed(records):
            t=tiles[r['tile']:r['tile']+r['w']*r['h']//64]
            assert len(t)==r['w']*r['h']//64
            a=t.reshape(r['h']//8,r['w']//8,8,8).transpose(0,2,1,3).reshape(r['h'],r['w'])
            if r['hflip']: a=a[:,::-1]
            if r['vflip']: a=a[::-1]
            x,y=r['x']-x0,r['y']-y0
            dst=canvas[y:y+r['h'],x:x+r['w']]; dst[a!=0]=a[a!=0]
        frames.append((canvas,records))
    return frames

def run(rom_path,out):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    raw=Path(rom_path).read_bytes(); rom=ndspy.rom.NintendoDSRom(raw)
    paths=tools.parse_fnt(raw); inv={v:k for k,v in paths.items()}
    inventory=[]
    for fid,p in paths.items():
        b=rom.files[fid]
        inventory.append(dict(fid=fid,path=p,size=len(b),sha256=hashlib.sha256(b).hexdigest()))
    (out/'inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    for fid,p in paths.items():
        if '/saveload/' in p and p.endswith('.ani') and '/cur06.' not in p:
            cp=p[:-4]+'.chr'
            if cp not in inv: continue
            folder=p.rsplit('/',1)[0]; stem=Path(p).stem
            pals=[q for q in inv if q.startswith(folder+'/') and q.endswith('.pal')]
            pp=cp[:-4]+'.pal'
            pp=pp if pp in inv else next(q for q in pals if 'com.pal' in q)
            pal=ex.bgr555(ex.strip_pal_header(decode(rom.files[inv[pp]])))
            frames=obj_frames(decode(b:=rom.files[fid]),tiles4(decode(rom.files[inv[cp]])[4:]))
            for i,(a,recs) in enumerate(frames):
                name=f'{inv[cp]}_{stem}_frame{i}'
                ex.save_p(a,pal,str(out/(name+'.png')))
                (out/(name+'.json')).write_text(json.dumps(recs,indent=2),encoding='utf-8')
        if 'bs_obj_name_p' in p:
            t=tiles4(decode(rom.files[fid]))
            a=t.reshape(-1,4,8,8).transpose(0,2,1,3).reshape(-1,32)
            ex.save_p(a,[(v*48,v*48,v*48) for v in range(6)],str(out/f'{fid}_name.png'))
    print('Extracted inventory and assembled frames:',out)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('rom'); ap.add_argument('out'); a=ap.parse_args(); run(a.rom,a.out)
