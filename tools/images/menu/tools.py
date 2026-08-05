import struct
def rd16(rom,o): return rom[o]|(rom[o+1]<<8)
def rd32(rom,o): return rom[o]|(rom[o+1]<<8)|(rom[o+2]<<16)|(rom[o+3]<<24)
def fat_count(rom): return rd32(rom,0x4C)//8
def read_file(rom,fid):
    fat=rd32(rom,0x48); s=rd32(rom,fat+fid*8); e=rd32(rom,fat+fid*8+4)
    return rom[s:e],(s,e)
def parse_fnt(rom):
    fnt=rd32(rom,0x40); paths={}
    def walk(did,pre):
        e=fnt+(did&0xFFF)*8; sub=fnt+rd32(rom,e); fid=rd16(rom,e+4); o=sub
        while True:
            t=rom[o]; o+=1
            if t==0: break
            ln=t&0x7F; nm=rom[o:o+ln].decode('shift_jis','replace'); o+=ln
            if t&0x80:
                ch=rd16(rom,o); o+=2; walk(ch,pre+'/'+nm)
            else:
                paths[fid]=pre+'/'+nm; fid+=1
    walk(0xF000,''); return paths
def lz10_dec(data):
    if not data or data[0]!=0x10: return None
    size=data[1]|(data[2]<<8)|(data[3]<<16); out=bytearray(); i=4
    while len(out)<size and i<len(data):
        fl=data[i]; i+=1
        for b in range(8):
            if len(out)>=size: break
            if fl&(0x80>>b):
                if i+1>=len(data): break
                v=(data[i]<<8)|data[i+1]; i+=2
                ln=(v>>12)+3; ds=(v&0xFFF)+1
                for _ in range(ln): out.append(out[-ds])
            else:
                if i<len(data): out.append(data[i]); i+=1
    return bytes(out)
def append_repoint(rom,fid,new,align=0x200):
    fat=rd32(rom,0x48); nf=fat_count(rom)
    mx=max(rd32(rom,fat+f*8+4) for f in range(nf))
    ap=(mx+align-1)&~(align-1); end=ap+len(new)
    if end>len(rom): rom.extend(b'\xFF'*(end-len(rom)))
    rom[ap:ap+len(new)]=new
    e=fat+fid*8; rom[e:e+4]=ap.to_bytes(4,'little'); rom[e+4:e+8]=end.to_bytes(4,'little')
    return ap

def lz10_store(data):
    """LZ10 무손실(전부-리터럴) 인코딩. 백레퍼런스를 안 써서 어떤 디코더에서도
    안전하게 풀린다(게임 메뉴는 BIOS 16비트 VRAM 쓰기라 disp<2 매치가 깨짐).
    파일은 약 +12.5% 커지지만 정확히 복원된다."""
    n = len(data)
    out = bytearray([0x10, n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF])
    i = 0
    while i < n:
        out.append(0x00)  # 플래그: 다음 8개는 모두 리터럴
        for _ in range(8):
            if i < n:
                out.append(data[i]); i += 1
    return bytes(out)
