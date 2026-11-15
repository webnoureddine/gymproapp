"""Code 128 (set B) barcode as SVG — readable by USB scanners and phone cameras. No external package."""
PATTERNS = (
    "212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 113222 "
    "123122 123221 223211 221132 221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 212123 212321 "
    "232121 111323 131123 131321 112313 132113 132311 211313 231113 231311 112133 112331 132131 113123 113321 133121 "
    "313121 211331 231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 314111 221411 431111 111224 "
    "111422 121124 121421 141122 141221 112214 112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 "
    "111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 214121 412121 111143 111341 131141 114113 "
    "114311 411113 411311 113141 114131 311141 411131 211412 211214 211232"
).split()
STOP = "2331112"
START_B = 104


def code128_widths(text):
    values = [START_B]
    for ch in text:
        o = ord(ch)
        if not 32 <= o <= 126:
            raise ValueError("Code128-B supports printable ASCII only")
        values.append(o - 32)
    checksum = (values[0] + sum(v * i for i, v in enumerate(values[1:], 1))) % 103
    values.append(checksum)
    return "".join(PATTERNS[v] for v in values) + STOP


def code128_svg(text, height=40, module=2, quiet=10, color="#000"):
    widths = code128_widths(text)
    x = quiet * module
    bars = []
    for i, w in enumerate(widths):
        w = int(w) * module
        if i % 2 == 0:  # even positions are bars, odd are spaces
            bars.append(f'<rect x="{x}" y="0" width="{w}" height="{height}"/>')
        x += w
    total = x + quiet * module
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {height}" preserveAspectRatio="none" '
            f'shape-rendering="crispEdges" fill="{color}">' + "".join(bars) + "</svg>")
