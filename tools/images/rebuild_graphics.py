"""Rebuild localized NDS tile resources from pristine Japanese assets.

All glyphs are compiled from the bundled BDF; no old translated pixels are used.
Every text allocation is fully cleared and every rendered glyph must fit.
"""
from pathlib import Path
import argparse, hashlib, json, struct, sys
import numpy as np
import ndspy.rom
from PIL import Image
import audit_graphics as ag
import minimap_signs
sys.path.insert(0,str(Path(__file__).parents[1]))
from galmuri_bdf import GalmuriBDF

FONT=GalmuriBDF(str(Path(__file__).parents[1]/'Galmuri11.bdf'))
CHECKS=[]

def text_mask(text,width,height,gap=1):
    glyphs=[]
    for ch in text:
        if ch==' ':
            glyphs.append(np.zeros((11,5),np.uint8)); continue
        if not FONT.has(ch): raise ValueError(f'Missing glyph: {ch!r}')
        g=FONT.render_char(ch); ys,xs=np.where(g)
        glyphs.append(g[:11,xs.min():xs.max()+1])
    tw=sum(g.shape[1] for g in glyphs)+max(0,len(glyphs)-1)*gap
    if tw>width or 11>height: raise ValueError(f'Text does not fit: {text!r}: {tw}x11 > {width}x{height}')
    out=np.zeros((height,width),np.uint8); x=(width-tw)//2; y=(height-11)//2
    for g in glyphs:
        out[y:y+11,x:x+g.shape[1]]=g; x+=g.shape[1]+gap
    CHECKS.append(dict(text=text,ink_width=tw,allocation=[width,height],gap=gap,pixels=int(out.sum())))
    return out

def tile_image(t,w):
    return t.reshape(-1,w//8,8,8).transpose(0,2,1,3).reshape(-1,w).copy()

def image_tiles(a):
    h,w=a.shape
    assert h%8==0 and w%8==0
    return a.reshape(h//8,8,w//8,8).transpose(0,2,1,3).reshape(-1,8,8)

def pack4(t):
    a=np.asarray(t,np.uint8).reshape(-1)
    assert a.max()<=15
    return (a[::2]|(a[1::2]<<4)).tobytes()

def render_bg(char,screen,bpp=4):
    if bpp==4:return ag.ex._render_indexed(bytes(4)+char,bytes(4)+screen)
    tiles=np.frombuffer(char,np.uint8).reshape(-1,8,8)
    out=np.zeros((256,256),np.uint8)
    for i,(entry,) in enumerate(struct.iter_unpack('<H',screen)):
        tile=tiles[entry&1023]
        if entry&1024:tile=tile[:,::-1]
        if entry&2048:tile=tile[::-1]
        y,x=divmod(i,32);out[y*8:y*8+8,x*8:x*8+8]=tile
    return out

def repack_bg(a,capacity,bpp=4,allow_flips=True):
    packed=[];lookup={};entries=[]
    for tile in image_tiles(a):
        bank=0
        if bpp==4:
            banks=np.unique(tile//16)
            assert len(banks)==1,('mixed palette bank',banks)
            bank=int(banks[0]);tile=tile%16
        match=None
        for hf,vf in ([(0,0),(1,0),(0,1),(1,1)] if allow_flips else [(0,0)]):
            v=tile[:,::-1] if hf else tile
            v=v[::-1] if vf else v
            key=pack4(v) if bpp==4 else v.tobytes()
            if key in lookup:match=lookup[key]|hf<<10|vf<<11|bank<<12;break
        if match is None:
            key=pack4(tile) if bpp==4 else tile.tobytes()
            idx=len(packed);lookup[key]=idx;packed.append(key);match=idx|bank<<12
        entries.append(match)
    if len(packed)>capacity:raise ValueError(f'BG tile capacity exceeded: {len(packed)} > {capacity}')
    print('BG tiles:',len(packed),'/',capacity)
    packed.extend([bytes(32 if bpp==4 else 64)]*(capacity-len(packed)))
    return b''.join(packed),struct.pack('<'+'H'*len(entries),*entries)

def paint(a,box,text,fg,bg,gap=1):
    x,y,w,h=box; assert x>=0 and y>=0 and x+w<=a.shape[1] and y+h<=a.shape[0]
    mask=text_mask(text,w,h,gap)
    a[y:y+h,x:x+w]=np.where(mask,fg,bg)

def rebuild(jp_path,reference_path,outdir):
    CHECKS.clear()
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    jpraw=Path(jp_path).read_bytes(); jp=ndspy.rom.NintendoDSRom(jpraw)
    ref=ndspy.rom.NintendoDSRom.fromFile(str(reference_path))
    assert jpraw[12:16]==b'ATMJ'
    assert hashlib.sha256(jpraw).hexdigest()=='f52b0c585eaf2cf8d08336db3bce8291255ca48d532f6504e003cc75ab9cfc24','Unsupported original ROM revision'
    paths=ag.tools.parse_fnt(jpraw); inv={v:k for k,v in paths.items()}
    changes={}; decoded={}; codecs={}
    def put(fid,data):
        orig=jp.files[fid]
        assert len(data)==len(ag.decode(orig)),(fid,len(data),len(ag.decode(orig)))
        codec='CMP' if orig[:3]==b'CMP' else 'LZ10' if orig[:1]==b'\x10' else 'raw'
        packed=ag.cmp.cmp_encode_rle(data,ver=1) if codec=='CMP' else ag.tools.lz10_store(data) if codec=='LZ10' else data
        assert ag.decode(packed)==data
        ref.files[fid]=packed;changes[fid]=paths[fid];decoded[fid]=data;codecs[fid]=codec

    # Main menu words are independent 32x16 allocations, not contiguous screen text.
    fid=inv['/data/usd/mainmenu.obc']; d=bytearray(ag.decode(jp.files[fid])); t=np.frombuffer(d[456:],np.uint8).reshape(-1,8,8).copy()
    # Solid white: the old cyan ramp is deliberately removed.
    for index in range(34,38):struct.pack_into('<H',d,4+index*2,0x7fff)
    words={51:'닫기',52:'판매',53:'목록',54:'상태',55:'도구',56:'주문',57:'무구',58:'오의',60:'포격',61:'순이',62:'지도',63:'모드',64:'작전',65:'만지',66:'카부키',67:'극락',68:'키누'}
    for word,s in words.items():
        mask=text_mask(s,32,16,0 if s=='카부키' else 1)
        fg=37 if word<=64 else 1
        new=np.where(mask,fg,0).astype(np.uint8)
        t[word*8:word*8+8]=image_tiles(new)
    # These two labels cross legacy 32px word boundaries: Japanese help begins
    # in word 49, not word 50. Rebuild the complete strip before splitting it.
    footer=np.zeros((16,96),np.uint8)
    paint(footer,(0,0,44,16),'명령',37,0)
    paint(footer,(48,0,32,16),'도움',37,0)
    for part in range(3):t[(48+part)*8:(49+part)*8]=image_tiles(footer[:,part*32:(part+1)*32])
    for start,label in [(552,'체'),(556,'기'),(560,'금'),(564,'후')]:
        t[start:start+4]=image_tiles(text_mask(label,16,16)*1)
    for start,label in [(648,'사용'),(660,'구입'),(672,'판매'),(684,'보관'),(696,'찾기'),(708,'버림')]:
        # Each action owns three independent 16x16 character cells.
        t[start:start+12]=0
        for j,ch in enumerate(label):t[start+j*4:start+j*4+4]=image_tiles(text_mask(ch,16,16)*1)
    put(fid,bytes(d[:456])+t.tobytes())
    ag.ex.save_p(footer,ag.ex.bgr555(d[4:196]),str(outdir/'footer_ko.png'))

    # Province labels: preserve the map, paths, gold capsule frames and original palette.
    fid=2764;d=ag.decode(jp.files[fid]);a=tile_image(np.frombuffer(d[264:],np.uint8).reshape(-1,8,8),256)
    # Coordinates are plaque centers and top edges, measured on the original.
    provinces=[(44,5,'석견'),(76,5,'출운'),(108,5,'인번'),(150,5,'근강'),(181,5,'월전'),(212,5,'월중'),(243,5,'월후'),
               (14,58,'장문'),(45,58,'안예'),(77,58,'길비'),(108,58,'단파'),(150,58,'경'),(181,58,'화다'),
               (108,112,'낭화'),(150,112,'이세'),(181,112,'미장'),(128,142,'기이')]
    original_map=a.copy();map_changed=np.zeros(a.shape,bool);province_checks=[]
    clean_column=a[26,39:50].copy()
    assert clean_column.tolist()==[126,126,127,127,127,127,127,127,127,126,126]
    for cx,top,label in provinces:
        x=cx-5;y=top+7
        a[y:y+33,x:x+11]=clean_column
        expected=np.tile(clean_column,(33,1))
        starts=[16] if len(label)==1 else [7,28]
        for ch,dy in zip(label,starts):
            mask=text_mask(ch,11,11,0)
            dest=a[top+dy:top+dy+11,x:x+11];dest[mask!=0]=96
            expected[dy-7:dy+4][mask!=0]=96
        assert np.array_equal(a[y:y+33,x:x+11],expected),'Unexpected residual province pixels'
        map_changed[y:y+33,x:x+11]=True
        province_checks.append(dict(text=label,box=[x,y,11,33],glyph_rows=[top+dy for dy in starts]))
    assert np.array_equal(a[~map_changed],original_map[~map_changed])
    put(fid,d[:264]+image_tiles(a).tobytes())
    ag.ex.save_p(a,ag.ex.bgr555(d[4:260]),str(outdir/'map_ko.png'))

    commands={1:'공격',2:'검법',3:'돌파',4:'주문',5:'자세',6:'작전',7:'무구',8:'도구',9:'?',10:'비술',11:'체술',12:'귀도',13:'포격',14:'공격',15:'화염',16:'어뢰',17:'열탄'}
    for n,s in commands.items():
        fid=inv[f'/iv_battle/grph/obj/files/bs_obj_command_icon{n}.cobj']
        a=text_mask(s,32,16)*5;put(fid,pack4(image_tiles(a)))
    for n,s in enumerate(['만지','카부키','극락','키누'],1):
        fid=inv[f'/iv_battle/grph/obj/files/bs_obj_name_p{n}.cobj'];t=ag.tiles4(ag.decode(jp.files[fid])).copy()
        t[:8]=image_tiles(text_mask(s,32,16,0 if s=='카부키' else 1)*5)
        # Remaining 12 tiles comprise three 16x16 allocations; last one stays original.
        for start,label in [(8,'체'),(12,'기')]:t[start:start+4]=image_tiles(text_mask(label,16,16)*5)
        put(fid,pack4(t))

    # Save/load buttons: the text sprite is separate from its decorative frame.
    for fid,s in [(9161,'취소'),(9163,'결정'),(9165,'삭제')]:
        d=ag.decode(jp.files[fid]);t=ag.tiles4(d[4:]).copy()
        ani=ag.decode(jp.files[fid-1]);frames=ag.obj_frames(ani,t);r=frames[0][1][0]
        assert r['w']==32 and r['h']==16
        t[r['tile']:r['tile']+8]=image_tiles(text_mask(s,32,16)*4)
        put(fid,d[:4]+pack4(t))
    for fid,s in [(9168,'예'),(9170,'아니오'),(9172,'계속'),(9174,'복사'),(9176,'삭제')]:
        d=ag.decode(jp.files[fid]);t=ag.tiles4(d[4:]).copy()
        # Foreground text occupies tiles 0..7 in both selected and unselected frames.
        t[:8]=image_tiles(text_mask(s,32,16,0 if s=='아니오' else 1)*15)
        put(fid,d[:4]+pack4(t))

    messages={
      9186:['파일을 읽는 중입니다','DS 카드를 빼거나','전원을 끄지 마세요'],
      9188:['불러오지 못했습니다','버튼을 누르거나','화면을 터치해 주세요'],
      9190:['기록이 비어 있지 않습니다','먼저 기록을 지워 주세요'],
      9192:['파일을 지웁니다','지워도 괜찮습니까?'],
      9194:['이미 파일이 있습니다','덮어써도 괜찮습니까?'],
      9196:['저장하는 중입니다','DS 카드를 빼거나','전원을 끄지 마세요'],
      9198:['데이터를 읽지 못했습니다','전원을 끄고 DS 카드를','다시 꽂아 주세요'],
      9200:['데이터를 저장하지 못했습니다','전원을 끄고 DS 카드를','다시 꽂아 주세요'],
    }
    for fid,lines in messages.items():
        d=ag.decode(jp.files[fid]);t=ag.tiles4(d[4:]).copy()
        # Three 64x64 sprites are the panel body; the bottom border is shared.
        body=np.concatenate([tile_image(t[i:i+64],64) for i in (0,64,128)],axis=1)
        before=body.copy();body[8:64,8:184]=4
        y=18 if len(lines)==3 else 26
        for line_index,s in enumerate(lines):
            if fid==9192:
                paint(body,(50,18,130,12) if line_index==0 else (9,42,174,12),s,15,4)
            else:paint(body,(9,y,174,12),s,15,4)
            y+=14
        for block,start in enumerate((0,64,128)):t[start:start+64]=image_tiles(body[:,block*64:(block+1)*64])
        # mes07/08 extend the body into additional lower sprites. Clear old fourth line.
        if fid in (9198,9200):
            for start in (192,200,208,216):
                a=tile_image(t[start:start+8],32)
                a[:9,8 if start==192 else 0:24 if start==216 else 32]=4
                t[start:start+8]=image_tiles(a)
        if fid==9192:
            frames=ag.obj_frames(ag.decode(jp.files[fid-1]),t)
            for frame_no,(_,records) in enumerate(frames):
                rec=records[0];assert (rec['w'],rec['h'])==(32,16)
                t[rec['tile']:rec['tile']+8]=image_tiles(text_mask(str(frame_no+1)+'번',32,16)*15)
        put(fid,d[:4]+pack4(t))

    # Kiten: retain the card and speech-bubble outlines; replace all interior text.
    fc=9140;fs=9143; c=ag.decode(jp.files[fc]);s=ag.decode(jp.files[fs]);a=ag.ex._render_indexed(c,s)
    for row in range(7,111):
        xs=np.where(a[row,:170]==12)[0]
        if len(xs):a[row,xs.min():xs.max()+1]=12
    for y,line in [(12,'처음부터 시작하려면'),(31,'「처음」을'),(52,'이어서 시작하려면'),(71,'「계속」을'),(91,'선택해 주세요!')]:
        paint(a,(10,y,152,13),line,7 if y in (31,71) else 4,12)
    # Flat card interiors; avoid the original gold/red borders.
    paint(a,(47,135,49,40),'처음',1,14)
    paint(a,(159,135,49,40),'계속',1,15)
    tilelist=[];lookup={};entries=[]
    for tile in image_tiles(a):
        assert tile.max()<16
        key=pack4(tile)
        if key not in lookup:lookup[key]=len(tilelist);tilelist.append(key)
        entries.append(lookup[key])
    budget=(len(c)-4)//32
    if len(tilelist)>budget: raise ValueError(f'Kiten tile budget: {len(tilelist)} > {budget}')
    tilelist.extend([bytes(32)]*(budget-len(tilelist)))
    put(fc,c[:4]+b''.join(tilelist));put(fs,s[:4]+struct.pack('<1024H',*entries))
    assert np.array_equal(ag.ex._render_indexed(decoded[fc],decoded[fs]),a)

    # The title demonstration contains a second copy with a permuted palette.
    sourcepal=ag.ex.bgr555(ag.ex.strip_pal_header(ag.decode(jp.files[9142])))
    targetpal=ag.ex.bgr555(ag.decode(jp.files[12630]))
    distance=((np.asarray(sourcepal[:16],np.int32)[:,None,:]-np.asarray(targetpal,np.int32)[None,:,:])**2).sum(axis=2)
    remap=distance.argmin(axis=1).astype(np.uint8)
    duplicate=remap[a]
    cc,ss=repack_bg(duplicate,len(ag.decode(jp.files[12629]))//32)
    put(12629,cc);put(12631,ss)
    assert np.array_equal(render_bg(cc,ss),duplicate)

    # The generated edit supplies only the title-letter area. Everything else is original.
    fid=12602;sfid=12604;pal=ag.ex.bgr555(ag.decode(jp.files[12603]))
    original=render_bg(ag.decode(jp.files[fid]),ag.decode(jp.files[sfid]),8)
    edited=original.copy()
    art=Image.open(Path(__file__).parent/'assets/title_ko_generated.png').convert('RGB').resize((256,256),Image.Resampling.LANCZOS)
    rgb=np.asarray(art)[54:107,28:228].astype(np.int32)
    palette=np.asarray(pal,np.int32)
    # The source letters use a flat blue body. Remove generated subpixel color noise.
    blue=(rgb[:,:,2]>rgb[:,:,1]*1.4)&(rgb[:,:,1]>rgb[:,:,0]*1.35)&(rgb[:,:,2]>50)
    rgb[blue]=[24,80,144]
    # Match colors without dithering to keep a clean, stable limited-color title.
    indices=((rgb.reshape(-1,1,3)-palette[None,:,:])**2).sum(axis=2).argmin(axis=1).reshape(rgb.shape[:2])
    edited[54:107,28:228]=indices
    for y in range(56,104,8):
        for x in range(32,224,8):
            block=edited[y:y+8,x:x+8]
            vals,counts=np.unique(block,return_counts=True)
            if counts.max()>=62:block[:]=vals[counts.argmax()]
    cc,ss=repack_bg(edited,len(ag.decode(jp.files[fid]))//64,8,allow_flips=False)
    put(fid,cc);put(sfid,ss)
    assert np.array_equal(render_bg(cc,ss,8),edited)
    outside=np.ones(original.shape,bool);outside[54:107,28:228]=False
    assert np.array_equal(edited[outside],original[outside])
    ag.ex.save_p(edited,pal,str(outdir/'title_ko.png'))

    fid=9202;sfid=9204;cd=ag.decode(jp.files[fid]);sd=ag.decode(jp.files[sfid])
    original=ag.ex._render_indexed(cd,sd);edited=original.copy()
    pal=ag.ex.bgr555(ag.ex.strip_pal_header(ag.decode(jp.files[9203])))
    art=Image.open(Path(__file__).parent/'assets/save_logo_ko_generated.png').convert('RGB').resize((256,256),Image.Resampling.LANCZOS)
    rgb=np.asarray(art)[149:179,154:256].astype(np.int32)
    palette=np.asarray(pal[:16],np.int32)
    edited[149:179,154:256]=((rgb.reshape(-1,1,3)-palette[None,:,:])**2).sum(axis=2).argmin(axis=1).reshape(rgb.shape[:2])
    cc,ss=repack_bg(edited,(len(cd)-4)//32)
    put(fid,cd[:4]+cc);put(sfid,sd[:4]+ss)
    assert np.array_equal(ag.ex._render_indexed(decoded[fid],decoded[sfid]),edited)
    ag.ex.save_p(edited,pal,str(outdir/'save_logo_ko.png'))

    # Ending logo uses a fixed OBJ tile sheet, not a screen map.
    fid=4592;d=ag.decode(jp.files[fid]);original=tile_image(ag.tiles4(d),256);edited=original.copy()
    pal=ag.ex.bgr555(ag.decode(jp.files[4593]))
    art=Image.open(Path(__file__).parent/'assets/ending_logo_ko_generated.png').convert('RGB').resize((256,256),Image.Resampling.LANCZOS)
    rgb=np.asarray(art)[:48,:96].astype(np.int32);palette=np.asarray(pal[:16],np.int32)
    edited[:48,:96]=((rgb.reshape(-1,1,3)-palette[None,:,:])**2).sum(axis=2).argmin(axis=1).reshape(rgb.shape[:2])
    put(fid,pack4(image_tiles(edited)))
    outside=np.ones(original.shape,bool);outside[:48,:96]=False
    assert np.array_equal(edited[outside],original[outside])
    ag.ex.save_p(edited,pal,str(outdir/'ending_logo_ko.png'))

    # Opening credits are bitmap resources too. Preserve every associated screen map.
    staff={
      11715:[['기획·감수','히로이 오지']],
      11724:[['음악','히사이시 조']],
      11732:[['원화','츠지노 토라지로']],
      11740:[['오리지널 작품','PC 엔진 SUPER CD-ROM²','감독          연출','마스다 쇼지    이와사키 히로마사']],
      11752:[['원작          음악','P.H.차다    후쿠다 야스히코']],
      11763:[['센고쿠 만지마루','이쿠라 카즈에','고쿠라쿠 타로','아카보시 쇼이치로']],
      11771:[['가부키 단주로     키누','야마구치 캇페이    이노우에 아즈미'],['특별 출연','키시다 교코']],
    }
    for fid,translations in staff.items():
        maps=[fid+2+i for i in range(len(translations))]
        images=[]
        for sfid,lines in zip(maps,translations):
            a=render_bg(ag.decode(jp.files[fid]),ag.decode(jp.files[sfid]))
            ink=a>1;ys=np.where(ink.any(axis=1))[0]
            bands=np.split(ys,np.where(np.diff(ys)>1)[0]+1)
            positions=[]
            if fid==11740:
                positions=[(10,3,236,12),(10,16,236,12),(10,30,236,12),(5,47,246,12)]
            else:
                assert len(bands)==len(lines),(fid,len(bands),len(lines))
                for rows in bands:
                    xs=np.where(ink[rows].any(axis=0))[0]
                    cy=(int(rows[0])+int(rows[-1]))//2;cx=(int(xs[0])+int(xs[-1]))//2
                    # Find the opaque panel's horizontal allocation at this row.
                    lo=cx
                    while lo>0 and a[cy,lo-1]!=0:lo-=1
                    hi=cx
                    while hi+1<256 and a[cy,hi+1]!=0:hi+=1
                    half=min(cx-lo,hi-cx)-2
                    positions.append((cx-half,cy-5,half*2,11))
            a[ink]=1
            for box,line in zip(positions,lines):paint(a,box,line,15,1,gap=0 if fid==11763 else 1)
            images.append(a)
        cc,ss=repack_bg(np.concatenate(images,axis=0),len(ag.decode(jp.files[fid]))//32)
        put(fid,cc)
        for page,(sfid,a) in enumerate(zip(maps,images)):
            page_map=ss[page*2048:(page+1)*2048];put(sfid,page_map)
            assert np.array_equal(render_bg(cc,page_map),a)
            ag.ex.save_p(a,ag.ex.bgr555(ag.decode(jp.files[fid+1])),str(outdir/f'staff_{fid}_{page}.png'))

    templates=minimap_signs.prepare(jp);signs={};map_count=0
    map_dir=outdir/'minimaps';map_dir.mkdir(exist_ok=True)
    for fid,path in paths.items():
        if not path.startswith('/data/usd/') or not path.endswith('.chr') or fid<2796:continue
        d=ag.decode(jp.files[fid]);offset=8+int.from_bytes(d[:2],'little')
        if len(d)-offset!=49152:continue
        new,records,a,pal=minimap_signs.rebuild(d,templates);map_count+=1
        if records:
            put(fid,new);signs[fid]=records
            ag.ex.save_p(a,pal.tolist(),str(map_dir/f'{fid}.png'))
    print('Minimaps scanned:',map_count,'changed:',len(signs),'signs:',sum(map(len,signs.values())))

    output=outdir/'Tengai_Makyou_II_KR_image_rework.nds';ref.saveToFile(str(output))
    reread=ndspy.rom.NintendoDSRom.fromFile(str(output))
    for fid,data in decoded.items():assert ag.decode(reread.files[fid])==data
    old=ndspy.rom.NintendoDSRom.fromFile(str(reference_path))
    assert reread.arm9==old.arm9 and reread.arm7==old.arm7
    for fid in range(len(old.files)):
        if fid not in changes:assert reread.files[fid]==old.files[fid],fid
    report=dict(source_sha256=hashlib.sha256(jpraw).hexdigest(),files=changes,original_codecs=codecs,province_checks=province_checks,text_checks=CHECKS,minimap_signs=signs,minimaps_scanned=map_count,
                verification='decoded payload readback and unrelated file preservation passed',runtime_verified=False,
                pending=['embedded mainmenu button assembly audit','complete in-game scene coverage including battle and ending','unclassified scene texture text audit'])
    (outdir/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(output);print('Rebuilt resources:',len(changes),'text fit checks:',len(CHECKS))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--jp',required=True);ap.add_argument('--reference',required=True);ap.add_argument('--outdir',required=True)
    a=ap.parse_args();rebuild(a.jp,a.reference,a.outdir)
