#!/usr/bin/env python3
"""Stackup drawing, impedance table and fabrication notes on User.3.

Draws the JLC06161H-2116A cross-section, the controlled-impedance table and
the fabrication notes of doc/pcb-stackup.md onto the User.3 layer (named
User.Stackup), right of and below the board. Everything goes in one group,
"Stackup JLC06161H-2116A", so it moves as a unit. A previous copy of that
group is removed first, so the script can be re-run after changing the
values below. Close the board in KiCad before running it.

    python doc/scripts/stackup_drawing.py hw/poetato/poetato.kicad_pcb

Keep STACK, IMP and FAB_NOTES in step with doc/pcb-stackup.md.
"""
import re
import sys
import uuid

GROUP = "Stackup JLC06161H-2116A"

LAYER = "User.3"
X0, Y0 = 180.0, 30.0          # top-left of the drawing block
SCALE = 28.0                   # cross-section vertical scale (mm per mm)
SEC_W = 22.0                   # cross-section width
ROW = 3.4                      # label row pitch

items = []


def uid():
    return str(uuid.uuid4())


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def text(s, x, y, size=1.2, th=0.15, just="left", bold=False):
    u = uid()
    j = f"\n\t\t\t(justify {just})" if just else ""
    b = "\n\t\t\t\t(bold yes)" if bold else ""
    items.append((u, f"""\t(gr_text "{esc(s)}"
\t\t(at {x:.3f} {y:.3f} 0)
\t\t(layer "{LAYER}")
\t\t(uuid "{u}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size {size} {size})
\t\t\t\t(thickness {th}){b}
\t\t\t){j}
\t\t)
\t)"""))


def line(x1, y1, x2, y2, w=0.1):
    u = uid()
    items.append((u, f"""\t(gr_line
\t\t(start {x1:.3f} {y1:.3f})
\t\t(end {x2:.3f} {y2:.3f})
\t\t(stroke
\t\t\t(width {w})
\t\t\t(type solid)
\t\t)
\t\t(layer "{LAYER}")
\t\t(uuid "{u}")
\t)"""))


def rect(x1, y1, x2, y2, w=0.1, fill=False):
    u = uid()
    items.append((u, f"""\t(gr_rect
\t\t(start {x1:.3f} {y1:.3f})
\t\t(end {x2:.3f} {y2:.3f})
\t\t(stroke
\t\t\t(width {w})
\t\t\t(type solid)
\t\t)
\t\t(fill {"yes" if fill else "no"})
\t\t(layer "{LAYER}")
\t\t(uuid "{u}")
\t)"""))


def hatch(x1, y1, x2, y2, pitch=1.0, w=0.05):
    """45-degree hatch clipped to the rectangle."""
    h = y2 - y1
    k = x1 - h
    while k < x2:
        # line y = y2 - (x - k), x from k to k + h
        xa, ya = k, y2
        xb, yb = k + h, y1
        if xa < x1:
            ya -= x1 - xa
            xa = x1
        if xb > x2:
            yb += xb - x2
            xb = x2
        if xb > xa:
            line(xa, ya, xb, yb, w)
        k += pitch


# ---------------------------------------------------------------- data
# (name, kind, function, material, thickness mm, Dk)
STACK = [
    ("F.Cu",   "cu",   "L1 SIG", "Copper 1 oz",   0.035,  None),
    ("",       "pp",   "",       "Prepreg 2116",  0.1164, 4.16),
    ("In1.Cu", "cu",   "L2 GND", "Copper 0.5 oz", 0.0152, None),
    ("",       "core", "",       "Core",          0.13,   4.6),
    ("In2.Cu", "cu",   "L3 SIG", "Copper 0.5 oz", 0.0152, None),
    ("",       "pp",   "",       "Prepreg 2116",  0.1164, 4.16),
    ("",       "core", "",       "Core, no Cu",   0.70,   4.6),
    ("",       "pp",   "",       "Prepreg 2116",  0.1164, 4.16),
    ("In3.Cu", "cu",   "L4 PWR", "Copper 0.5 oz", 0.0152, None),
    ("",       "core", "",       "Core",          0.13,   4.6),
    ("In4.Cu", "cu",   "L5 GND", "Copper 0.5 oz", 0.0152, None),
    ("",       "pp",   "",       "Prepreg 2116",  0.1164, 4.16),
    ("B.Cu",   "cu",   "L6 SIG", "Copper 1 oz",   0.035,  None),
]
TOTAL = sum(r[4] for r in STACK)

# (target, signals, layer, width, gap, reference)
IMP = [
    ("50 Ω SE",    "RMII, QSPI, SWD",         "L1 / L6", "0.18", "-",    "L2 / L5 GND"),
    ("",           "",                        "L3",      "0.16", "-",    "L2 GND"),
    ("90 Ω diff",  "USB_D_P / USB_D_N",       "L1 / L6", "0.16", "0.15", "L2 / L5 GND"),
    ("",             "",                        "L3",      "0.13", "0.15", "L2 GND"),
    ("100 Ω diff", "ETH_TX_P/N, ETH_RX_P/N",  "L1 / L6", "0.14", "0.20", "L2 / L5 GND"),
    ("",              "",                        "L3",      "0.12", "0.20", "L2 GND"),
]

# ---------------------------------------------------------------- title
text("PCB STACKUP  JLCPCB JLC06161H-2116A", X0, Y0, size=2.0, th=0.3, bold=True)
text(f"6 layers, 1.6 mm finished ({TOTAL:.3f} mm laminate + mask), "
     "outer 1 oz, inner 0.5 oz, FR-4", X0, Y0 + 3.6, size=1.1, th=0.15)

# ---------------------------------------------------------------- stackup
ytab = Y0 + 9.0                 # header row
ysec = ytab + 2.6               # top of cross-section / first label row
cx = {"layer": X0 + SEC_W + 9.0}
cx["func"] = cx["layer"] + 12.5
cx["mat"] = cx["func"] + 12.0
cx["th"] = cx["mat"] + 24.0
cx["dk"] = cx["th"] + 13.0
xend = cx["dk"] + 8.0

for key, label in (("layer", "Layer"), ("func", "Use"), ("mat", "Material"),
                   ("th", "Thickness"), ("dk", "Dk")):
    text(label, cx[key], ytab, size=1.2, th=0.2, bold=True)
text("Cross-section (vertical x28)", X0, ytab, size=1.0, th=0.15)
line(cx["layer"] - 1.0, ytab + 1.3, xend, ytab + 1.3, 0.15)

y = ysec
for i, (name, kind, func, mat, t, dk) in enumerate(STACK):
    h = t * SCALE
    y1, y2 = y, y + h
    if kind == "cu":
        rect(X0, y1, X0 + SEC_W, y2, w=0.05, fill=True)
    else:
        rect(X0, y1, X0 + SEC_W, y2, w=0.1)
        if kind == "core":
            hatch(X0, y1, X0 + SEC_W, y2)
    ymid = (y1 + y2) / 2
    yrow = ysec + ROW * (i + 0.5)
    # leader: section edge -> elbow -> label row
    line(X0 + SEC_W, ymid, X0 + SEC_W + 2.5, ymid, 0.08)
    line(X0 + SEC_W + 2.5, ymid, X0 + SEC_W + 6.0, yrow, 0.08)
    line(X0 + SEC_W + 6.0, yrow, cx["layer"] - 1.0, yrow, 0.08)
    ty = yrow + 0.6  # baseline-ish centring for 1.2 mm text with bottom justify
    bold = kind == "cu"
    if name:
        text(name, cx["layer"], yrow, size=1.2, th=0.2 if bold else 0.15, bold=bold)
    if func:
        text(func, cx["func"], yrow, size=1.2, th=0.2, bold=True)
    text(mat, cx["mat"], yrow, size=1.2)
    text(f"{t:.4f} mm" if t < 0.1 or kind == 'pp' else f"{t:.2f} mm", cx["th"], yrow, size=1.2)
    text("-" if dk is None else f"{dk:.2f}", cx["dk"], yrow, size=1.2)
    y = y2

yrows_end = ysec + ROW * len(STACK)
ysec_end = y
ybot = max(yrows_end, ysec_end) + 1.0
line(cx["layer"] - 1.0, ybot, xend, ybot, 0.15)
text(f"Total {TOTAL:.3f} mm (+ solder mask, Dk 3.8)", cx["mat"], ybot + 2.0, size=1.2, th=0.2, bold=True)

# ---------------------------------------------------------------- impedance table
yi = ybot + 7.0
text("CONTROLLED IMPEDANCE  (order with impedance control)", X0, yi, size=1.5, th=0.25, bold=True)
ih = yi + 3.5
icol = [X0, X0 + 15.0, X0 + 46.0, X0 + 59.0, X0 + 69.0, X0 + 79.0, xend]
heads = ["Target", "Signals", "Layer", "W mm", "S mm", "Reference"]
IROW = 3.0
rows = len(IMP) + 1
rect(icol[0], ih, icol[-1], ih + IROW * rows, w=0.15)
for c in icol[1:-1]:
    line(c, ih, c, ih + IROW * rows, 0.08)
for r in range(1, rows):
    yy = ih + IROW * r
    # group the L1/L6 + L3 rows of one class visually
    line(icol[0] if r % 2 == 1 else icol[2], yy, icol[-1], yy, 0.15 if r == 1 else 0.08)
for c, hd in zip(icol, heads):
    text(hd, c + 1.0, ih + IROW / 2, size=1.1, th=0.2, bold=True)
for r, row in enumerate(IMP, start=1):
    yy = ih + IROW * (r + 0.5)
    for k, (c, val) in enumerate(zip(icol, row)):
        if not val:
            continue
        # target and signals span the L1/L6 + L3 row pair
        text(val, c + 1.0, yy + (IROW / 2 if k < 2 else 0), size=1.1, bold=(k == 0), th=0.2 if k == 0 else 0.15)

# W/S/H geometry sketch
ys = ih + IROW * rows + 4.0
text("Geometry", X0, ys, size=1.1, th=0.2, bold=True)
sx = X0
pw = 44.0
yp = ys + 9.0                       # reference plane
gh = 1.4                            # trace height
yt = yp - 4.0                       # trace bottom
rect(sx, yp, sx + pw, yp + 1.0, w=0.05, fill=True)
text("Reference plane (GND)", sx + pw + 1.5, yp + 0.5, size=1.0)
line(sx, yt, sx + pw, yt, 0.05)     # laminate surface
tw, ts = 9.0, 7.0
t1 = sx + 8.0
t2 = t1 + tw + ts
rect(t1, yt - gh, t1 + tw, yt, w=0.05, fill=True)
rect(t2, yt - gh, t2 + tw, yt, w=0.05, fill=True)
yd = yt - gh - 1.5
line(t1, yd, t1 + tw, yd, 0.08)
line(t1 + tw, yd, t2, yd, 0.08)
for xx in (t1, t1 + tw, t2):
    line(xx, yd - 0.6, xx, yd + 0.6, 0.08)
text("W", t1 + tw / 2 - 0.5, yd - 1.2, size=1.0)
text("S", t1 + tw + ts / 2 - 0.4, yd - 1.2, size=1.0)
xh = t2 + tw + 3.0
line(xh, yt, xh, yp, 0.08)
for yy in (yt, yp):
    line(xh - 0.6, yy, xh + 0.6, yy, 0.08)
text("H = dielectric to reference", xh + 1.0, (yt + yp) / 2, size=1.0)
text("SE: one trace of width W", sx + pw + 1.5, yt - gh, size=1.0)
ys = yp - 7.0  # keeps the notes offset below unchanged

# ---------------------------------------------------------------- notes
yn = yp + 5.0
notes = [
    "Notes",
    "1. Widths from a 2D field solve: solder mask Dk 3.8, 30 µm over laminate, 15 µm over Cu;",
    "   rectangular trace profile. Expect about ±5 %. Confirm in the JLCPCB impedance",
    "   calculator for JLC06161H-2116A before ordering.",
    "2. L3 references L2 GND (0.13 mm); L4 PWR is 0.93 mm away. Route L3 signals only",
    "   over unbroken L2 GND.",
    "3. Dk per JLCPCB: prepreg 2116 4.16, core 4.6 (test frequency not stated).",
]
for i, n in enumerate(notes):
    text(n, X0, yn + i * 2.4, size=1.1 if i else 1.3, th=0.2 if i == 0 else 0.15, bold=(i == 0))

# ---------------------------------------------------------------- fabrication notes
# below the board, vendor-neutral (doc/pcb-stackup.md §7)
FX, FY = 30.0, 128.0
FAB_NOTES = [
    "1. Build to IPC-6012 Class 2. 6-layer rigid FR-4, Tg >= 150 °C, rated for lead-free assembly.",
    "   Reference build: JLCPCB stackup JLC06161H-2116A, Tg 155 option.",
    "2. Finished board thickness 1.60 mm ±10 %.",
    "3. Finished copper: outer layers 1 oz (35 µm), inner layers 0.5 oz.",
    "4. Layer order and use per the stackup table. Dielectric thicknesses are nominal; other materials and",
    "   constructions are acceptable if the impedance targets and finished thickness are met and",
    "   L1-L2, L2-L3, L4-L5 and L5-L6 each stay <= 0.15 mm.",
    "5. Controlled impedance per the table, ±10 %. The fab may change the width of controlled traces by up to",
    "   ±0.025 mm (keeping the pair pitch) to meet the targets. TDR test coupons and an impedance test",
    "   report are required (IPC-TM-650 2.5.5.7).",
    "6. Surface finish ENIG. LPI solder mask both sides, Dk about 3.8.",
    "7. Vias are plain plated through-holes, smallest finished hole 0.25 mm. No via filling or capping",
    "   required (no IPC-4761 Type VII). Non-functional inner-layer pads are removed in the data.",
]
text("FABRICATION NOTES", FX, FY, size=1.5, th=0.25, bold=True)
for i, n in enumerate(FAB_NOTES):
    text(n, FX, FY + 3.0 + i * 2.4, size=1.1)


# ---------------------------------------------------------------- write
def remove_group(s, name):
    """Drop a previous copy of the group and every top-level item in it."""
    m = re.search(r'\n\t\(group "' + re.escape(name) + r'"\n.*?\n\t\)(?=\n)', s, re.S)
    if not m:
        return s, 0
    members = set(re.findall(r'"([0-9a-f-]{36})"', m.group(0)))
    s = s[:m.start()] + s[m.end():]
    out, block, n = [], None, 0
    for ln in s.split("\n"):
        if block is None and re.match(r"^\t\(gr_", ln):
            block = [ln]
            continue
        if block is not None:
            block.append(ln)
            if ln == "\t)":
                u = re.search(r'^\t\t\(uuid "([^"]+)"\)', "\n".join(block), re.M)
                if u and u.group(1) in members:
                    n += 1
                else:
                    out.extend(block)
                block = None
            continue
        out.append(ln)
    return "\n".join(out), n


def main(src, dst):
    s = open(src, encoding="utf-8").read()
    s, removed = remove_group(s, GROUP)
    gid = uid()
    members = " ".join(f'"{u}"' for u, _ in items)
    group = (f'\t(group "{GROUP}"\n\t\t(uuid "{gid}")\n'
             f'\t\t(members {members}\n\t\t)\n\t)')
    body = "\n".join(t for _, t in items)
    gi = s.index("\n\t(group ")
    s = s[:gi] + "\n" + body + s[gi:]
    ei = s.index("\n\t(embedded_fonts")
    s = s[:ei] + "\n" + group + s[ei:]
    s = s.replace('(43 "User.3" user)', '(43 "User.3" user "User.Stackup")', 1)
    open(dst, "w", encoding="utf-8", newline="\r\n").write(s)
    print(f"removed {removed} old items, wrote {len(items)}; laminate {TOTAL:.4f} mm")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
