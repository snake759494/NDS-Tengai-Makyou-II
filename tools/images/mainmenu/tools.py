"""
tools.py — 천외마경II(ATMJ) NDS 롬 메뉴 패치용 공통 도구 (순수 파이썬)
- FAT(파일 할당 테이블) 읽기
- LZ10 압축 해제
- LZ10 무손실 저장(전부-리터럴, VRAM 안전)
- FNT(파일 이름 테이블) 파싱: 파일명 -> fid

의존성: 표준 라이브러리만 사용 (numpy/PIL 불필요)
"""

def read_file(rom, fid):
    """FAT에서 파일 fid의 바이트와 (시작,끝) 오프셋 반환."""
    fat = int.from_bytes(rom[0x48:0x4C], 'little')
    e = fat + fid * 8
    s = int.from_bytes(rom[e:e + 4], 'little')
    en = int.from_bytes(rom[e + 4:e + 8], 'little')
    return rom[s:en], (s, en)


def fat_count(rom):
    """FAT 엔트리(파일) 개수."""
    return int.from_bytes(rom[0x4C:0x50], 'little') // 8


def lz10_dec(data):
    """표준 LZ10(GBA/NDS, 매직 0x10) 압축 해제. 실패 시 None."""
    if not data or data[0] != 0x10:
        return None
    size = data[1] | (data[2] << 8) | (data[3] << 16)
    out = bytearray()
    pos = 4
    try:
        while len(out) < size:
            fl = data[pos]; pos += 1
            for i in range(8):
                if len(out) >= size:
                    break
                if fl & (0x80 >> i):
                    b0 = data[pos]; b1 = data[pos + 1]; pos += 2
                    ln = (b0 >> 4) + 3
                    ds = (((b0 & 0xF) << 8) | b1) + 1
                    for _ in range(ln):
                        out.append(out[-ds])
                else:
                    out.append(data[pos]); pos += 1
    except IndexError:
        return None
    return bytes(out)


def lz10_store(data):
    """LZ10 무손실 저장 — 매치를 전혀 쓰지 않는 '전부 리터럴' 인코딩.

    게임의 메뉴 그래픽은 VRAM으로 압축 해제되며, 이때 displacement<2 매치는
    16비트 VRAM 쓰기와 충돌해 화면이 깨진다(원본 압축은 disp>=2만 사용).
    매치를 아예 쓰지 않으면 어떤 LZ10 디코더에서도 100% 안전하다.
    파일은 원본보다 커지지만(약 +12.5%) 롬의 0xFF 패딩 영역에 넣으므로 문제없다.
    """
    out = bytearray(b'\x10') + len(data).to_bytes(3, 'little')
    i = 0
    n = len(data)
    while i < n:
        out.append(0x00)  # 플래그 0 = 다음 8개 모두 리터럴
        for _ in range(8):
            if i < n:
                out.append(data[i]); i += 1
    return bytes(out)


def parse_fnt(rom):
    """FNT를 파싱해 {fid: '전체/경로'} 딕셔너리 반환."""
    fnt_off = int.from_bytes(rom[0x40:0x44], 'little')

    def dir_entry(idx):
        o = fnt_off + idx * 8
        return (int.from_bytes(rom[o:o + 4], 'little'),
                int.from_bytes(rom[o + 4:o + 6], 'little'),
                int.from_bytes(rom[o + 6:o + 8], 'little'))

    paths = {}

    def walk(dir_id, prefix):
        sub, first, _ = dir_entry(dir_id & 0x0FFF)
        o = fnt_off + sub
        fid = first
        while True:
            t = rom[o]; o += 1
            if t == 0:
                break
            ln = t & 0x7F
            is_dir = t & 0x80
            name = rom[o:o + ln].decode('shift_jis', 'replace'); o += ln
            if is_dir:
                sd = int.from_bytes(rom[o:o + 2], 'little'); o += 2
                walk(sd, prefix + '/' + name)
            else:
                paths[fid] = prefix + '/' + name
                fid += 1

    walk(0xF000, '')
    return paths


def append_repoint(rom, fid, new_compressed, align=0x200):
    """새 압축 데이터를 롬의 패딩 영역에 추가하고 FAT[fid]를 그 위치로 변경.

    헤더는 건드리지 않으므로(FAT는 헤더 CRC 영역 밖) 헤더 CRC가 유지된다.
    rom 은 bytearray 여야 한다. 추가 위치(start)를 반환.
    """
    fat = int.from_bytes(rom[0x48:0x4C], 'little')
    nf = fat_count(rom)
    max_end = max(int.from_bytes(rom[fat + f * 8 + 4: fat + f * 8 + 8], 'little')
                  for f in range(nf))
    ap = (max_end + (align - 1)) & ~(align - 1)
    end = ap + len(new_compressed)
    if end > len(rom):
        # 패딩이 모자라면 파일을 확장(에뮬레이터는 큰 파일도 매핑)
        rom.extend(b'\xFF' * (end - len(rom)))
    rom[ap:ap + len(new_compressed)] = new_compressed
    e = fat + fid * 8
    rom[e:e + 4] = ap.to_bytes(4, 'little')
    rom[e + 4:e + 8] = end.to_bytes(4, 'little')
    return ap
