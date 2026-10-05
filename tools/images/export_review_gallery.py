"""Export every rebuilt image from the ROM, including all save OAM frames."""
from pathlib import Path
import argparse, json, math, html, shutil, zipfile, hashlib
import numpy as np
import ndspy.rom
from PIL import Image, ImageDraw, ImageFont
import audit_graphics as ag
from rebuild_graphics import tile_image, render_bg

def export(rom_path, report_path, output):
    out=Path(output);assets=out/'images';assets.mkdir(parents=True,exist_ok=True)
    raw=Path(rom_path).read_bytes();rom=ndspy.rom.NintendoDSRom(raw)
    paths=ag.tools.parse_fnt(raw);inv={p:f for f,p in paths.items()}
    report=json.loads(Path(report_path).read_text(encoding='utf-8'));records=[];covered=set()
    def add(key,label,group,a,pal,fids,transparent=None,light=False):
        pal=list(pal)+[(255,0,255)]*(256-len(pal))
        rgb=np.asarray(pal,np.uint8)[a];rgba=np.concatenate([rgb,np.full((*a.shape,1),255,np.uint8)],axis=2)
        if transparent is not None:rgba[a==transparent,3]=0
        im=Image.fromarray(rgba);im.save(assets/(key+'.png'),optimize=True)
        records.append(dict(key=key,label=label,group=group,file='images/'+key+'.png',fids=fids,width=im.width,height=im.height,light=light))
        covered.update(fids)
    d=ag.decode(rom.files[2766]);t=np.frombuffer(d[456:],np.uint8).reshape(-1,8,8);pal=ag.ex.bgr555(d[4:196])
    footer=np.concatenate([tile_image(t[w*8:w*8+8],32) for w in range(48,51)],axis=1)
    add('footer','하단 명령 / 도움','메뉴',footer,pal,[2766],0)
    words={51:'닫기',52:'판매',53:'목록',54:'상태',55:'도구',56:'주문',57:'무구',58:'오의',60:'포격',61:'순이',62:'지도',63:'모드',64:'작전',65:'만지',66:'카부키',67:'극락',68:'키누'}
    for w,label in words.items():add(f'menu_{w}',label,'메뉴',tile_image(t[w*8:w*8+8],32),pal,[2766],0,w>=65)
    for start,label in [(552,'체'),(556,'기'),(560,'금'),(564,'후')]:add(f'menu_{start}',label,'메뉴',tile_image(t[start:start+4],16),pal,[2766],0,True)
    for start,label in [(648,'사용'),(660,'구입'),(672,'판매'),(684,'보관'),(696,'찾기'),(708,'버림')]:
        a=np.concatenate([tile_image(t[i:i+4],16) for i in range(start,start+12,4)],axis=1)
        add(f'menu_{start}',label,'메뉴',a,pal,[2766],0,True)
    bp=[(0,0,0)]*16;bp[5]=(248,248,248)
    commands=['공격','검법','돌파','주문','자세','작전','무구','도구','?','비술','체술','귀도','포격','공격','화염','어뢰','열탄']
    for n,label in enumerate(commands,1):
        f=inv[f'/iv_battle/grph/obj/files/bs_obj_command_icon{n}.cobj']
        add(f'command_{n:02}',label,'전투',tile_image(ag.tiles4(ag.decode(rom.files[f])),32),bp,[f],0)
    for f,label in zip(range(3966,3970),['만지','카부키','극락','키누']):
        tiles=ag.tiles4(ag.decode(rom.files[f]))
        a=np.concatenate([tile_image(tiles[:8],32),np.concatenate([tile_image(tiles[8:12],16),tile_image(tiles[12:16],16)],axis=1)],axis=0)
        add(f'name_{f}',label+' / 체 / 기','전투',a,bp,[f],0)
    f=2764;d=ag.decode(rom.files[f]);a=tile_image(np.frombuffer(d[264:],np.uint8).reshape(-1,8,8),256)
    add('provinces','나라 지도','주요 화면',a,ag.ex.bgr555(d[4:260]),[f])
    for cf,sf,pf,label,key,header,bpp in [(12602,12604,12603,'타이틀','title',False,8),(9140,9143,9142,'처음 / 계속','kiten',True,4),(12629,12631,12630,'타이틀 데모의 처음 / 계속','kiten_demo',False,4),(9202,9204,9203,'저장 화면 배경 로고','save_logo',True,4)]:
        c=ag.decode(rom.files[cf]);s=ag.decode(rom.files[sf]);p=ag.decode(rom.files[pf])
        a=ag.ex._render_indexed(c,s) if header else render_bg(c,s,bpp)
        if header:p=ag.ex.strip_pal_header(p)
        add(key,label,'주요 화면',a,ag.ex.bgr555(p),[cf,sf],0 if key in ('kiten','kiten_demo') else None)
    add('ending','엔딩 로고 / 효과 타일','주요 화면',tile_image(ag.tiles4(ag.decode(rom.files[4592])),256),ag.ex.bgr555(ag.decode(rom.files[4593])),[4592])
    labels=['기획·감수','음악','원화','원작 제작진','원작·음악','성우 1','성우 2','특별 출연']
    for (cf,sf),label in zip([(11715,11717),(11724,11726),(11732,11734),(11740,11742),(11752,11754),(11763,11765),(11771,11773),(11771,11774)],labels):
        a=render_bg(ag.decode(rom.files[cf]),ag.decode(rom.files[sf]))
        add(f'staff_{sf}',label,'제작진',a,ag.ex.bgr555(ag.decode(rom.files[cf+1])),[cf,sf],0)
    save_labels={9161:'취소',9163:'결정',9165:'삭제',9168:'예',9170:'아니오',9172:'계속',9174:'복사',9176:'삭제',9186:'파일 읽는 중',9188:'불러오기 실패',9190:'기록이 비어 있지 않음',9192:'기록 삭제 확인',9194:'덮어쓰기 확인',9196:'저장 중',9198:'읽기 오류',9200:'저장 오류'}
    for f,label in save_labels.items():
        cp=paths[f];folder=cp.rsplit('/',1)[0];pp=cp[:-4]+'.pal'
        if pp not in inv:pp=next(p for p in inv if p.startswith(folder+'/') and p.endswith('com.pal'))
        pal=ag.ex.bgr555(ag.ex.strip_pal_header(ag.decode(rom.files[inv[pp]])))
        frames=ag.obj_frames(ag.decode(rom.files[f-1]),ag.tiles4(ag.decode(rom.files[f])[4:]))
        for n,(a,_) in enumerate(frames):add(f'save_{f}_{n}',label+(f' ({n+1}/{len(frames)})' if len(frames)>1 else ''),'저장·불러오기',a,pal,[f],0)
    for f in sorted(map(int,report['minimap_signs'])):
        d=ag.decode(rom.files[f]);n=int.from_bytes(d[:2],'little');a=tile_image(np.frombuffer(d[8+n:],np.uint8).reshape(-1,8,8),256)
        add(f'map_{f}',Path(paths[f]).stem+f' · {len(report["minimap_signs"][str(f)])}곳','미니맵',a,ag.ex.bgr555(d[4:4+n]),[f])
    missing=set(map(int,report['files']))-covered
    assert not missing,('Missing modified resources',missing)
    (out/'manifest.json').write_text(json.dumps(dict(rom=Path(rom_path).name,rom_sha256=hashlib.sha256(raw).hexdigest(),covered_resources=len(covered),image_count=len(records),images=records),ensure_ascii=False,indent=2),encoding='utf-8')
    font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',16)
    def sheet(name,items,cols,cw,ch,scale=1):
        canvas=Image.new('RGB',(cols*cw,math.ceil(len(items)/cols)*ch),(30,34,41));draw=ImageDraw.Draw(canvas)
        for n,r in enumerate(items):
            x=n%cols*cw;y=n//cols*ch
            draw.text((x+8,y+5),r['label'],font=font,fill=(235,238,242))
            im=Image.open(out/r['file']);factor=min(scale,(cw-16)/im.width,(ch-36)/im.height)
            im=im.resize((round(im.width*factor),round(im.height*factor)),Image.Resampling.NEAREST)
            px=x+(cw-im.width)//2;py=y+30+(ch-36-im.height)//2
            if r['light']:draw.rectangle((px-2,py-2,px+im.width+2,py+im.height+2),fill=(244,233,208))
            canvas.paste(im,(px,py),im)
        canvas.save(out/(name+'.png'),optimize=True)
    sheet('01-menus',[r for r in records if r['group'] in ('메뉴','전투')],5,200,100,3)
    sheet('02-screens',[r for r in records if r['group']=='주요 화면'],3,272,292)
    sheet('03-save',[r for r in records if r['group']=='저장·불러오기'],3,272,130,2)
    sheet('04-staff',[r for r in records if r['group']=='제작진'],4,272,292)
    maps=[r for r in records if r['group']=='미니맵']
    for n in range(3):sheet(f'0{5+n}-minimaps',maps[n*36:(n+1)*36],6,272,224)
    body=[]
    for group in dict.fromkeys(r['group'] for r in records):
        body.append('<h2>'+group+'</h2><div class="grid">')
        for r in records:
            if r['group']!=group:continue
            body.append(f'<figure><a href="{r["file"]}" target="_blank"><img loading="lazy" class="{"light" if r["light"] else ""}" src="{r["file"]}" alt="{html.escape(r["label"])}"></a><figcaption>{html.escape(r["label"])}<small>{r["width"]}×{r["height"]} · FID {", ".join(map(str,r["fids"]))}</small></figcaption></figure>')
        body.append('</div>')
    page='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>TM2 수정 이미지 전체 모음</title><style>body{margin:24px;background:#171b22;color:#f0f2f5;font:16px system-ui}h2{margin-top:36px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(272px,1fr));gap:14px}figure{margin:0;padding:12px;background:#252b35;display:flex;flex-direction:column;align-items:center;justify-content:space-between}img{image-rendering:pixelated;max-width:100%;min-width:128px;object-fit:contain}.light{background:#f4e9d0}small{display:block;color:#bdc5d0;font-size:12px}figcaption{margin-top:12px}a{color:inherit}button{padding:8px}</style><h1>TM2 수정 이미지 전체 모음</h1>'''
    page+=f'<p>수정 ROM 재추출 · 리소스 {len(covered)}개 · 이미지/프레임 {len(records)}개 · 미니맵 {len(maps)}개. 이미지를 누르면 원본 크기로 열립니다.</p><p>메뉴·타이틀·지도는 사용자 실행 확인. 나머지는 추출 이미지이며 모든 장면의 실행 확인을 뜻하지 않습니다. 전투 글자는 가독성 확인용 흰색 팔레트로 표시했습니다.</p>'
    (out/'index.html').write_text(page+''.join(body)+'</html>',encoding='utf-8')
    with zipfile.ZipFile(out.parent/'TM2_수정이미지_전체.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in out.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(out))
    print('Exported',len(records),'images covering',len(covered),'resources:',out)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('rom');ap.add_argument('report');ap.add_argument('out');a=ap.parse_args();export(a.rom,a.report,a.out)
