"""Exact bitmap recognition and replacement of the six recurring minimap signs."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFont, ImageDraw
import audit_graphics as ag

TEMPLATES=[(2797,90,40,'宿','숙'),(2797,173,95,'道','도'),(2797,173,122,'武','무'),
           (2797,107,144,'預','창'),(2797,159,144,'茶','차'),(2800,115,69,'雑','잡')]

def unpack(d):
    palette_size=int.from_bytes(d[:2],'little');offset=8+palette_size
    assert int.from_bytes(d[offset-4:offset],'little')==len(d)-offset
    a=np.frombuffer(d[offset:],np.uint8).reshape(24,32,8,8).transpose(0,2,1,3).reshape(192,256).copy()
    colors=ag.ex.bgr555(d[4:4+palette_size])
    # Unprovided palette entries may be shared by the runtime; never match them as text.
    colors.extend([(255,0,255)]*(256-len(colors)))
    return a,np.asarray(colors,np.uint8),offset

def dark(rgb):
    return (rgb[:,:,0]<100)&(rgb[:,:,1]<100)&(rgb[:,:,2]<70)

def glyph(text):
    f=ImageFont.truetype(str(Path(__file__).parent/'mainmenu/Galmuri14.ttf'),9)
    im=Image.new('L',(24,24));ImageDraw.Draw(im).text((3,3),text,font=f,fill=255)
    bits=np.asarray(im)>100;y,x=np.where(bits);bits=bits[y.min():y.max()+1,x.min():x.max()+1]
    h,w=bits.shape
    assert 0<h<=9 and 0<w<=10
    out=np.zeros((9,10),bool);out[(9-h)//2:(9-h)//2+h,(10-w)//2:(10-w)//2+w]=bits
    return out

def prepare(rom):
    result=[]
    for fid,x,y,jp,ko in TEMPLATES:
        a,pal,_=unpack(ag.decode(rom.files[fid]));rgb=pal[a[y:y+9,x:x+10]];mask=dark(rgb)
        codes=sum(mask[:,i].astype(np.uint16)*(1<<i) for i in range(10))
        result.append((jp,ko,codes,glyph(ko)))
    return result

def matches(rgb,templates):
    m=dark(rgb);h,w=m.shape
    rowcode=sum(m[:,i:i+w-9].astype(np.uint16)*(1<<i) for i in range(10))
    result=[]
    for jp,ko,codes,bitmap in templates:
        found=np.ones((h-8,w-9),bool)
        for row in range(9):found&=rowcode[row:row+h-8]==codes[row]
        for y,x in zip(*np.where(found)):
            block=rgb[y:y+9,x:x+10]
            gold=(block[:,:,0]>160)&(block[:,:,1]>80)&(block[:,:,2]<90)
            if gold.mean()<0.3:continue
            result.append((int(x),int(y),jp,ko,bitmap))
    return result

def rebuild(d,templates):
    a,pal,offset=unpack(d);rgb=pal[a];hits=matches(rgb,templates);records=[]
    for x,y,jp,ko,bits in hits:
        def color(rgb):return int(((pal.astype(np.int32)-np.asarray(rgb,np.int32))**2).sum(axis=1).argmin())
        bg=color((248,192,8));fg=color((0,24,0));lower=color((240,152,24))
        block=np.full((9,10),bg,np.uint8);block[-2:]=lower;block[bits]=fg
        a[y:y+9,x:x+10]=block
        records.append(dict(box=[x,y,10,9],jp=jp,ko=ko,ink_pixels=int(bits.sum())))
    assert not matches(pal[a],templates),'Residual original Japanese sign bitmap'
    payload=a.reshape(24,8,32,8).transpose(0,2,1,3).tobytes()
    return d[:offset]+payload,records,a,pal
