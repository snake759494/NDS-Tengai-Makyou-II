"""Heuristic scene-gallery extraction; mapping choices require visual review."""
from pathlib import Path
import argparse, json, os, struct
import numpy as np
import ndspy.rom
from PIL import Image, ImageDraw
import audit_graphics as ag
from rebuild_graphics import render_bg

def run(rom_path, output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    raw=Path(rom_path).read_bytes();rom=ndspy.rom.NintendoDSRom(raw)
    paths=ag.tools.parse_fnt(raw);inv={p:f for f,p in paths.items()};records=[]
    for fid,path in paths.items():
        if fid<11700 or not path.endswith('.cscr'):continue
        folder=path.rsplit('/',1)[0]
        options=[(f,p) for f,p in paths.items() if p.startswith(folder+'/') and p.endswith('.cobj')]
        if not options:continue
        cf,cp=max(options,key=lambda q:len(os.path.commonprefix([path[:-5],q[1][:-5]])))
        pp=cp[:-5]+'.cplt'
        if pp not in inv:continue
        cd=ag.decode(rom.files[cf]);sd=ag.decode(rom.files[fid]);pd=ag.decode(rom.files[inv[pp]])
        if len(sd)!=2048:continue
        entries=np.frombuffer(sd,'<u2')
        bpp=8 if len(pd)>=512 and (entries>>12).max()==0 and (entries&1023).max()<len(cd)//64 else 4
        try:
            a=render_bg(cd,sd,bpp)
            ag.ex.save_p(a,ag.ex.bgr555(pd),str(out/f'{fid}.png'))
            records.append(dict(screen=fid,char=cf,path=path,bpp=bpp))
        except (ValueError,IndexError,AssertionError) as e:
            records.append(dict(screen=fid,char=cf,path=path,error=str(e)))
    valid=[r for r in records if 'error' not in r]
    for page in range((len(valid)+23)//24):
        canvas=Image.new('RGB',(768,704),(60,60,60));draw=ImageDraw.Draw(canvas)
        for n,r in enumerate(valid[page*24:page*24+24]):
            im=Image.open(out/f'{r["screen"]}.png').convert('RGB').resize((128,128),Image.Resampling.NEAREST)
            x=n%6*128;y=n//6*176;canvas.paste(im,(x,y+32))
            draw.text((x,y),f'{r["screen"]}/{r["char"]} {r["bpp"]}b')
            draw.text((x,y+14),Path(r['path']).stem[:20])
        canvas.save(out/f'contact{page}.png')
    (out/'mapping.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print('Scene maps:',len(valid),'failed:',len(records)-len(valid))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('rom');ap.add_argument('out');args=ap.parse_args();run(args.rom,args.out)
