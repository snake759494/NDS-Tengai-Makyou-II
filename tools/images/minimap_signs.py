"""Exact bitmap recognition and replacement of the six recurring minimap signs."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFont, ImageDraw
import audit_graphics as ag

TEMPLATES=[(2797,90,40,'宿','숙'),(2797,173,95,'道','도'),(2797,173,122,'武','무'),
           (2797,107,144,'預','보'),(2797,159,144,'茶','차'),(2800,115,69,'雑','잡')]

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

# Hand-drawn 10x9 sign glyphs.  Rendering a 9px font clipped strokes
# (무 came out as 드, 잡 as 짐), so the bitmaps are fixed here.
GLYPHS={
'숙':"""
....##....
...#..#...
..#....#..
##########
....##....
.########.
........#.
........#.
..........""",
'도':"""
.#######..
.#........
.#........
.#######..
..........
....##....
....##....
##########
..........""",
'무':"""
.########.
.#......#.
.#......#.
.########.
..........
##########
....##....
....##....
....##....""",
'보':"""
.#......#.
.#......#.
.########.
.#......#.
.########.
....##....
....##....
##########
..........""",
'차':"""
...#....#.
.#####..#.
...#....#.
..#.#...##
.#...#..#.
#.....#.#.
........#.
........#.
..........""",
'잡':"""
#####..#..
..#....#..
.#.#...###
#...#..#..
.......#..
..#...#...
..#####...
..#...#...
..#####...""",
}

def glyph(text):
    rows=GLYPHS[text].strip().split()
    out=np.array([[c=='#' for c in r] for r in rows],bool)
    assert out.shape==(9,10),text
    return out

def prepare(rom):
    result=[]
    for fid,x,y,jp,ko in TEMPLATES:
        a,pal,_=unpack(ag.decode(rom.files[fid]));rgb=pal[a[y:y+9,x:x+10]];mask=dark(rgb)
        codes=sum(mask[:,i].astype(np.uint16)*(1<<i) for i in range(10))
        result.append((jp,ko,codes,glyph(ko)))
    return result

def matches(rgb,templates,max_dist=8,min_gold=0.4):
    """Find signs whose ink differs from a template by at most max_dist pixels.

    Some maps (e.g. wab1 after the flower event, wga1, ynl0) redraw the same
    signs with a few pixels changed, so exact row matching misses them.  The
    background around the ink must still be the gold sign plate.
    """
    from numpy.lib.stride_tricks import sliding_window_view
    m=sliding_window_view(dark(rgb),(9,10))
    gold=(rgb[:,:,0]>160)&(rgb[:,:,1]>80)&(rgb[:,:,2]<90)
    g=sliding_window_view(gold,(9,10))
    best={}
    for jp,ko,codes,bitmap in templates:
        ink=np.array([[(int(c)>>i)&1 for i in range(10)] for c in codes],bool)
        dist=(m!=ink).sum((2,3))
        for y,x in zip(*np.where(dist<=max_dist)):
            if g[y,x][~ink].mean()<min_gold:continue
            key=(int(x),int(y));d=int(dist[y,x])
            if key not in best or d<best[key][0]:best[key]=(d,jp,ko,bitmap)
    return [(x,y,jp,ko,bitmap) for (x,y),(d,jp,ko,bitmap) in sorted(best.items())]

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
