"""
QR code encoder, plus an independent decoder used to verify what the encoder
produced. Byte mode, error correction level M, versions 1 to 10.

Nothing in the container can make a QR code, so this is written from the spec.
It is not trusted until decode(encode(s)) == s for every string we ship, AND
until the decoder can read a QR that was made elsewhere.
"""

# ---------------------------------------------------------------- GF(256)
EXP = [0] * 512
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def gmul(a, b):
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]


def rs_generator(n):
    g = [1]
    for i in range(n):
        g2 = [0] * (len(g) + 1)
        for j, c in enumerate(g):
            g2[j] ^= c
            g2[j + 1] ^= gmul(c, EXP[i])
        g = g2
    return g


def rs_ecc(data, n):
    gen = rs_generator(n)
    res = list(data) + [0] * n
    for i in range(len(data)):
        c = res[i]
        if c:
            for j, gc in enumerate(gen):
                res[i + j] ^= gmul(gc, c)
    return res[len(data):]


# ------------------------------------------------- version tables, level M
# (total codewords, ec codewords per block, [(block count, data per block), ...])
VERSIONS_M = {
    1:  (26,  10, [(1, 16)]),
    2:  (44,  16, [(1, 28)]),
    3:  (70,  26, [(1, 44)]),
    4:  (100, 18, [(2, 32)]),
    5:  (134, 24, [(2, 43)]),
    6:  (172, 16, [(4, 27)]),
    7:  (196, 18, [(4, 31)]),
    8:  (242, 22, [(2, 38), (2, 39)]),
    9:  (292, 22, [(3, 36), (2, 37)]),
    10: (346, 26, [(4, 43), (1, 44)]),
}
VERSIONS_L = {
    1:  (26,   7, [(1, 19)]),
    2:  (44,  10, [(1, 34)]),
    3:  (70,  15, [(1, 55)]),
    4:  (100, 20, [(1, 80)]),
    5:  (134, 26, [(1, 108)]),
    6:  (172, 18, [(2, 68)]),
    7:  (196, 20, [(2, 78)]),
    8:  (242, 24, [(2, 97)]),
    9:  (292, 30, [(2, 116)]),
    10: (346, 18, [(2, 68), (2, 69)]),
}
# the two bits the format information carries for each level
TABLES = {0: VERSIONS_M, 1: VERSIONS_L}
LEVEL_BITS = {"M": 0, "L": 1}

ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
         7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}
REMAINDER = {1: 0, 2: 7, 3: 7, 4: 7, 5: 7, 6: 7, 7: 0, 8: 0, 9: 0, 10: 0}


def data_capacity(ver, level="M"):
    total, ecc, blocks = TABLES[LEVEL_BITS[level]][ver]
    return total - ecc * sum(c for c, _ in blocks)


def pick_version(nbytes, level="M"):
    for v in range(1, 11):
        cc_bits = 8 if v < 10 else 16
        need = (4 + cc_bits + nbytes * 8 + 7) // 8
        if need <= data_capacity(v, level):
            return v
    raise ValueError("payload too long for version 10 at level %s: %d bytes" % (level, nbytes))


# ---------------------------------------------------------------- bit stream
class Bits:
    def __init__(self):
        self.b = []

    def put(self, value, length):
        for i in range(length - 1, -1, -1):
            self.b.append((value >> i) & 1)

    def __len__(self):
        return len(self.b)


def make_codewords(payload, ver, level="M"):
    raw = payload.encode("utf-8")
    cc_bits = 8 if ver < 10 else 16
    bs = Bits()
    bs.put(0b0100, 4)                 # byte mode
    bs.put(len(raw), cc_bits)
    for byte in raw:
        bs.put(byte, 8)

    cap = data_capacity(ver, level) * 8
    if len(bs) > cap:
        raise ValueError("does not fit")
    bs.put(0, min(4, cap - len(bs)))              # terminator
    while len(bs) % 8:
        bs.b.append(0)
    data = [int("".join(str(x) for x in bs.b[i:i + 8]), 2) for i in range(0, len(bs), 8)]
    pad = [0xEC, 0x11]
    i = 0
    while len(data) < data_capacity(ver, level):
        data.append(pad[i % 2]); i += 1

    # split into blocks, compute ecc, interleave
    total, ecc_n, spec = TABLES[LEVEL_BITS[level]][ver]
    blocks, pos = [], 0
    for count, dlen in spec:
        for _ in range(count):
            blocks.append(data[pos:pos + dlen]); pos += dlen
    eccs = [rs_ecc(b, ecc_n) for b in blocks]

    out = []
    for i in range(max(len(b) for b in blocks)):
        for b in blocks:
            if i < len(b):
                out.append(b[i])
    for i in range(ecc_n):
        for e in eccs:
            out.append(e[i])
    return out


# ---------------------------------------------------------------- matrix
def _bch_remainder(v, g=0x537):
    while v.bit_length() > 10:
        v ^= g << (v.bit_length() - 11)
    return v


def bch_format(fmt):
    return ((fmt << 10) | _bch_remainder(fmt << 10)) ^ 0x5412


def bch_version(ver):
    g = 0x1F25
    v = ver << 12
    while v.bit_length() > 12:
        v ^= g << (v.bit_length() - 13)
    return (ver << 12) | v


def blank(size):
    return [[None] * size for _ in range(size)]


def place_function_patterns(m, ver):
    size = len(m)

    def finder(r, c):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                rr, cc = r + dr, c + dc
                if not (0 <= rr < size and 0 <= cc < size):
                    continue
                if dr in (-1, 7) or dc in (-1, 7):
                    m[rr][cc] = 0
                elif dr in (0, 6) or dc in (0, 6) or (2 <= dr <= 4 and 2 <= dc <= 4):
                    m[rr][cc] = 1
                else:
                    m[rr][cc] = 0

    finder(0, 0); finder(0, size - 7); finder(size - 7, 0)

    for i in range(size):
        if m[6][i] is None:
            m[6][i] = 1 - (i % 2)
        if m[i][6] is None:
            m[i][6] = 1 - (i % 2)

    for r in ALIGN[ver]:
        for c in ALIGN[ver]:
            if (r < 8 and c < 8) or (r < 8 and c > size - 9) or (r > size - 9 and c < 8):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    m[r + dr][c + dc] = 1 if (max(abs(dr), abs(dc)) != 1) else 0

    m[size - 8][8] = 1                      # dark module

    for i in range(9):                      # reserve format areas
        if m[8][i] is None: m[8][i] = 0
        if m[i][8] is None: m[i][8] = 0
    for i in range(8):
        if m[8][size - 1 - i] is None: m[8][size - 1 - i] = 0
        if m[size - 1 - i][8] is None: m[size - 1 - i][8] = 0

    if ver >= 7:
        vb = bch_version(ver)
        for i in range(18):
            bit = (vb >> i) & 1
            m[size - 11 + i % 3][i // 3] = bit
            m[i // 3][size - 11 + i % 3] = bit
    return m


def reserved_mask(ver):
    """A matrix marking every module that is a function pattern."""
    size = ver * 4 + 17
    m = blank(size)
    place_function_patterns(m, ver)
    return [[c is not None for c in row] for row in m]


MASKS = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]


def place_data(m, reserved, bits):
    size = len(m)
    idx = 0
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for r in rows:
            for c in (col, col - 1):
                if reserved[r][c]:
                    continue
                m[r][c] = bits[idx] if idx < len(bits) else 0
                idx += 1
        upward = not upward
        col -= 2
    return m


def penalty(m):
    size = len(m)
    score = 0
    for line in list(m) + [list(col) for col in zip(*m)]:
        run, prev = 0, None
        for v in line:
            if v == prev:
                run += 1
            else:
                if run >= 5:
                    score += 3 + (run - 5)
                run, prev = 1, v
        if run >= 5:
            score += 3 + (run - 5)
        s = "".join(str(v) for v in line)
        score += 40 * (s.count("10111010000") + s.count("00001011101"))
    for r in range(size - 1):
        for c in range(size - 1):
            b = m[r][c] + m[r][c + 1] + m[r + 1][c] + m[r + 1][c + 1]
            if b in (0, 4):
                score += 3
    dark = sum(sum(row) for row in m)
    score += 10 * (abs(dark * 100 // (size * size) - 50) // 5)
    return score


def encode(payload, level="M"):
    ver = pick_version(len(payload.encode("utf-8")), level)
    cw = make_codewords(payload, ver, level)
    bits = []
    for byte in cw:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    bits += [0] * REMAINDER[ver]

    reserved = reserved_mask(ver)
    best, best_score, best_mask = None, None, None
    for mi, fn in enumerate(MASKS):
        m = blank(ver * 4 + 17)
        place_function_patterns(m, ver)
        place_data(m, reserved, bits)
        for r in range(len(m)):
            for c in range(len(m)):
                if not reserved[r][c] and fn(r, c):
                    m[r][c] ^= 1
        fmt = bch_format((LEVEL_BITS[level] << 3) | mi)
        size = len(m)
        # Both orders below were established by decoding a QR made elsewhere,
        # not from memory: copy one runs MSB-first, copy two LSB-first.
        seq1 = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
                (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
        for i, (r, c) in enumerate(seq1):
            m[r][c] = (fmt >> (14 - i)) & 1
        seq2 = [(8, size - 1 - i) for i in range(8)] + [(size - 15 + i, 8) for i in range(8, 15)]
        for i, (r, c) in enumerate(seq2):
            m[r][c] = (fmt >> i) & 1
        m[size - 8][8] = 1
        s = penalty(m)
        if best_score is None or s < best_score:
            best, best_score, best_mask = m, s, mi
    return best, ver, best_mask


# ---------------------------------------------------------------- decoder
def decode(m):
    """Read a QR matrix back. Assumes level M, no damage."""
    size = len(m)
    ver = (size - 17) // 4
    seq1 = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    raw = 0
    for r, c in seq1:
        raw = (raw << 1) | m[r][c]
    assert _bch_remainder(raw ^ 0x5412) == 0, "format information does not check out"
    raw ^= 0x5412
    mask_id = (raw >> 10) & 0b111
    ec_level = (raw >> 13) & 0b11
    assert ec_level in TABLES, "level %d not supported by this decoder" % ec_level

    reserved = reserved_mask(ver)
    un = [row[:] for row in m]
    fn = MASKS[mask_id]
    for r in range(size):
        for c in range(size):
            if not reserved[r][c] and fn(r, c):
                un[r][c] ^= 1

    bits = []
    col, upward = size - 1, True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for r in rows:
            for c in (col, col - 1):
                if not reserved[r][c]:
                    bits.append(un[r][c])
        upward = not upward
        col -= 2

    cw = [int("".join(str(b) for b in bits[i:i + 8]), 2) for i in range(0, (len(bits) // 8) * 8, 8)]

    total, ecc_n, spec = TABLES[ec_level][ver]
    blocks = []
    for count, dlen in spec:
        for _ in range(count):
            blocks.append([0] * dlen)
    i = 0
    for k in range(max(len(b) for b in blocks)):
        for b in blocks:
            if k < len(b):
                b[k] = cw[i]; i += 1
    data = [x for b in blocks for x in b]

    bits = []
    for byte in data:
        for j in range(7, -1, -1):
            bits.append((byte >> j) & 1)
    mode = int("".join(str(b) for b in bits[0:4]), 2)
    assert mode == 0b0100, "expected byte mode, got %r" % mode
    cc_bits = 8 if ver < 10 else 16
    n = int("".join(str(b) for b in bits[4:4 + cc_bits]), 2)
    start = 4 + cc_bits
    out = bytearray()
    for k in range(n):
        chunk = bits[start + k * 8:start + k * 8 + 8]
        out.append(int("".join(str(b) for b in chunk), 2))
    return out.decode("utf-8")


# ---------------------------------------------------------------- image
def to_png(m, path, scale=8, quiet=4):
    from PIL import Image
    size = len(m)
    side = (size + quiet * 2) * scale
    im = Image.new("1", (side, side), 1)
    px = im.load()
    for r in range(size):
        for c in range(size):
            if m[r][c]:
                for dy in range(scale):
                    for dx in range(scale):
                        px[(c + quiet) * scale + dx, (r + quiet) * scale + dy] = 0
    im.save(path)
    return im


def matrix_from_png(path):
    """Read a QR back out of a PNG.

    The module grid is found by taking the bounding box of the dark pixels -
    which spans exactly the symbol, quiet zone excluded - then trying every
    legal symbol size and keeping the one whose finder patterns and timing
    pattern actually check out. Measuring a run along the diagonal was not
    reliable: it gave 39 modules, which is not a legal size at all.
    """
    from PIL import Image
    im = Image.open(path).convert("L")
    w, h = im.size
    px = im.load()
    dark = lambda x, y: px[x, y] < 128

    xs = [x for x in range(w) if any(dark(x, y) for y in range(0, h, 3))]
    ys = [y for y in range(h) if any(dark(x, y) for x in range(0, w, 3))]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    span = max(x1 - x0, y1 - y0) + 1

    def sample(size):
        step = span / size
        return [[1 if dark(min(w - 1, int(x0 + (c + .5) * step)),
                           min(h - 1, int(y0 + (r + .5) * step))) else 0
                 for c in range(size)] for r in range(size)]

    def looks_right(m):
        size = len(m)
        for (r, c) in [(0, 0), (0, size - 7), (size - 7, 0)]:
            for dr in range(7):
                for dc in range(7):
                    want = 1 if (dr in (0, 6) or dc in (0, 6)
                                 or (2 <= dr <= 4 and 2 <= dc <= 4)) else 0
                    if m[r + dr][c + dc] != want:
                        return False
        for i in range(8, size - 8):
            if m[6][i] != 1 - (i % 2) or m[i][6] != 1 - (i % 2):
                return False
        return True

    for ver in range(1, 11):
        size = ver * 4 + 17
        m = sample(size)
        if looks_right(m):
            return m
    raise ValueError("no legal module grid fits this image (span %d px)" % span)
