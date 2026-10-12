#!/usr/bin/env python3
"""
PoEtato board outline and floorplan for Italtronic 35.0807000.BL
(Modulbox Compact 8M XTS, A version).

Emits:
  poetato-outline.dxf   board outline + cut-outs, import to KiCad Edge.Cuts
  ../img/floorplan.svg  dimensioned floorplan drawing

Dimensions are MEASURED from the Italtronic drawing
(datasheets/mechanical/35.0807000-enclosure_Italtronic.pdf, drawing M-05181-00):

    enclosure         142 x 90 x 32.2 mm, 8 modules, ABS/PC
    body              140 +/-0.1 long
    PCB               87.0 +/-0.1  x  139.0 +/-0.1  x  1.6 +/-0.1
    front face split  13.8 | 62.4 | 13.8 across the 90 mm dimension:
                      two terminal shelves with the front panel between them
    version A         "terminal blocks/connectors can be mounted on either side"
    top panel         part of the mould, NOT removable

ALL CONNECTORS ON ONE EDGE (Y = 0), including the RJ45. The enclosure supports
both shelves; only the Y = 0 shelf is populated.

Consequence, and it is the main cost of the single-edge choice: each isolation
domain has to reach that edge, so the domains become COLUMNS rising from Y = 0
rather than horizontal strips. Barriers 1, 2 and 3 are therefore U-shaped
(up one side, across the top, down the other) instead of straight slots, and
total slot length roughly doubles. The 139 x 87 board absorbs it comfortably.

LED PLACEMENT IS CONSTRAINED: only the central 62.4 mm band of the 90 mm face
is visible - the outer 13.8 mm strips are under the terminal shelves. In board
coordinates that is roughly Y 12 .. 74. The LED row sits at Y ~ 40.

STILL ASSUMED: usable component height above the board, and the exact position
of the moulded connector apertures along the shelf. Confirm both before routing.

Origin is the lower-left board corner. X runs along the DIN rail.
Y = 0 is the single CONNECTOR edge. Units are millimetres.
"""
import os

# ------------------------------------------------------------------- measured
BOARD_W      = 139.0  # Italtronic drawing, "Dimension of PCB"
BOARD_H      = 87.0
CORNER_CHAM  = 2.5    # ASSUMED corner relief
MOUNT_HOLES  = []     # slot-retained, as with the previous enclosure
TALL_BUDGET  = 20.0   # ASSUMED, from 32.2 overall - confirm against the STEP
VISIBLE_Y    = (12.0, 74.0)   # central 62.4 mm band, outside the terminal shelves

PITCH        = 3.5    # terminal pitch
SLOT_W       = 1.6    # isolation slot width

# ------------------------------------------- columns rising from the Y=0 edge
CABLE   = dict(x0=3.0,  x1=40.0, y1=34.0)     # RJ45 + PD front end
FIELD   = dict(x0=46.0, x1=96.0, y1=35.0)     # 12 terminal positions + field side
OUT     = dict(x0=102.0, x1=136.0, y1=27.0)   # 2 floating output islands
N_OUT   = 2

RJ45      = (6.0, 22.0)   # x span on the connector edge
RJ45_DEPTH = 21.0

FIELD_X0 = 50.0
FIELD_GROUPS = [("DI1 - DI4", 4), ("+24/0V", 2), ("RS-485", 4), ("SENSOR", 2)]
FIELD_N  = sum(n for _, n in FIELD_GROUPS)    # 12 positions = 42 mm

TERM_D   = 9.0        # how far a terminal block reaches onto the board

# straddle gaps in the top run of each U, (x0, x1, label)
FIELD_GAPS = [(54.0, 74.0, "ISO1211 x3"), (78.0, 92.0, "ISO3082")]
CABLE_GAPS = [(24.0, 38.0, "PD flyback")]


def out_islands():
    span = OUT["x1"] - OUT["x0"]
    w = (span - (N_OUT - 1) * SLOT_W) / N_OUT
    return [(OUT["x0"] + i * (w + SLOT_W), w) for i in range(N_OUT)]


def u_slots(col, gaps):
    """Slot rectangles forming a U around a column rising from Y=0."""
    x0, x1, y1 = col["x0"], col["x1"], col["y1"]
    h = SLOT_W / 2
    out = [(x0 - SLOT_W, 0.0, x0, y1 + h),          # left leg
           (x1, 0.0, x1 + SLOT_W, y1 + h)]          # right leg
    x = x0 - SLOT_W
    for g0, g1, _ in sorted(gaps):
        if g0 > x:
            out.append((x, y1 - h, g0, y1 + h))
        x = g1
    if x < x1 + SLOT_W:
        out.append((x, y1 - h, x1 + SLOT_W, y1 + h))
    return out


def all_slots():
    s = u_slots(CABLE, CABLE_GAPS) + u_slots(FIELD, FIELD_GAPS)
    isl = out_islands()
    y1 = OUT["y1"]; h = SLOT_W / 2
    s.append((isl[0][0] - SLOT_W, 0.0, isl[0][0], y1 + h))
    s.append((isl[-1][0] + isl[-1][1], 0.0, isl[-1][0] + isl[-1][1] + SLOT_W, y1 + h))
    for i in range(N_OUT - 1):
        x = isl[i][0] + isl[i][1]
        s.append((x, 0.0, x + SLOT_W, y1 + h))
    s.append((isl[0][0] - SLOT_W, y1 - h, isl[-1][0] + isl[-1][1] + SLOT_W, y1 + h))
    return s


# ------------------------------------------------------------------ DXF (R12)
class Dxf:
    def __init__(self): self.e = []

    def line(self, x1, y1, x2, y2, layer="Edge"):
        self.e += ["0", "LINE", "8", layer,
                   "10", f"{x1:.3f}", "20", f"{y1:.3f}", "30", "0.0",
                   "11", f"{x2:.3f}", "21", f"{y2:.3f}", "31", "0.0"]

    def rect(self, x0, y0, x1, y1, layer="Edge"):
        self.line(x0, y0, x1, y0, layer); self.line(x1, y0, x1, y1, layer)
        self.line(x1, y1, x0, y1, layer); self.line(x0, y1, x0, y0, layer)

    def save(self, path):
        body = ["0", "SECTION", "2", "ENTITIES"] + self.e + ["0", "ENDSEC", "0", "EOF"]
        with open(path, "w", encoding="ascii") as f:
            f.write("\n".join(body) + "\n")
        print("wrote", path)


def build_dxf(path):
    d, c, W, H = Dxf(), CORNER_CHAM, BOARD_W, BOARD_H
    for a, b in [((c, 0), (W - c, 0)), ((W - c, 0), (W, c)), ((W, c), (W, H - c)),
                 ((W, H - c), (W - c, H)), ((W - c, H), (c, H)), ((c, H), (0, H - c)),
                 ((0, H - c), (0, c)), ((0, c), (c, 0))]:
        d.line(a[0], a[1], b[0], b[1])
    for x0, y0, x1, y1 in all_slots():
        d.rect(x0, y0, x1, y1, "Slot")
    d.save(path)


# ------------------------------------------------------------------- floorplan
BG, PANEL, INK, MUTED, RULE = "#FAF9F7", "#FFFFFF", "#22201D", "#6E6862", "#D9D4CC"
VIOLET, BLUE, AMBER, GREEN, RED = "#6B4E9E", "#2C6BAA", "#B5751A", "#3E7C4F", "#B33A3A"
VT, BT, AT, GT = "#F3EFF8", "#EAF1F8", "#FBF3E7", "#EDF4EE"
FONT = "ui-sans-serif,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

S = 5.4
OX, OY = 62, 560


def px(x, y):
    return OX + x * S, OY - y * S


def build_svg(path):
    W, H = 900, 830
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}" font-family="{FONT}">',
         f'<rect width="{W}" height="{H}" fill="{BG}"/>',
         f'<text x="30" y="34" font-size="19" font-weight="600" fill="{INK}">'
         f'PoEtato - Board Floorplan</text>',
         f'<text x="30" y="55" font-size="12.5" fill="{MUTED}">'
         f'Italtronic 35.0807000.BL, 8M XTS - PCB {BOARD_W:.0f} x {BOARD_H:.0f} mm, '
         f'all connectors on the Y=0 edge</text>']

    def rect(x0, y0, x1, y1, fill, stroke, w=1.2, dash=None, op=1.0):
        ax, ay = px(x0, y1); bx, by = px(x1, y0)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        o.append(f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{bx-ax:.1f}" '
                 f'height="{by-ay:.1f}" fill="{fill}" fill-opacity="{op}" '
                 f'stroke="{stroke}" stroke-width="{w}"{da}/>')

    def txt(x, y, s, size=9, fill=INK, anchor="middle", weight="400"):
        ax, ay = px(x, y)
        o.append(f'<text x="{ax:.1f}" y="{ay:.1f}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}">{s}</text>')

    # logic background, then the three column domains
    rect(0, 0, BOARD_W, BOARD_H, BT, BLUE, 0)
    rect(CABLE["x0"], 0, CABLE["x1"], CABLE["y1"], VT, VIOLET, 0)
    rect(FIELD["x0"], 0, FIELD["x1"], FIELD["y1"], AT, AMBER, 0)
    for x0, w in out_islands():
        rect(x0, 0, x0 + w, OUT["y1"], GT, GREEN, 0)

    # visible window through the front panel
    ax, ay = px(0, VISIBLE_Y[1]); bx, by = px(BOARD_W, VISIBLE_Y[0])
    o.append(f'<rect x="{ax:.1f}" y="{ay:.1f}" width="{bx-ax:.1f}" height="{by-ay:.1f}" '
             f'fill="none" stroke="{MUTED}" stroke-width="1" stroke-dasharray="6 4"/>')
    txt(BOARD_W - 2, VISIBLE_Y[1] + 2.5, "visible through the 62.4 mm front panel",
        8.5, MUTED, anchor="end")

    # outline
    c = CORNER_CHAM
    pts = [(c, 0), (BOARD_W - c, 0), (BOARD_W, c), (BOARD_W, BOARD_H - c),
           (BOARD_W - c, BOARD_H), (c, BOARD_H), (0, BOARD_H - c), (0, c)]
    d = "M " + " L ".join(f"{px(x,y)[0]:.1f},{px(x,y)[1]:.1f}" for x, y in pts) + " Z"
    o.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="1.8"/>')

    for x0, y0, x1, y1 in all_slots():
        rect(x0, y0, x1, y1, RED, RED, 0.8, op=0.75)
    for g0, g1, lab in FIELD_GAPS:
        txt((g0 + g1) / 2, FIELD["y1"] + 2.0, lab, 7.5, RED)
    for g0, g1, lab in CABLE_GAPS:
        txt((g0 + g1) / 2, CABLE["y1"] + 2.0, lab, 7.5, RED)

    # connector edge
    rect(RJ45[0], 0, RJ45[1], RJ45_DEPTH, PANEL, VIOLET, 1.2)
    txt((RJ45[0] + RJ45[1]) / 2, RJ45_DEPTH / 2 + 2, "RJ45", 9, VIOLET, weight="600")
    txt((RJ45[0] + RJ45[1]) / 2, RJ45_DEPTH / 2 - 4, "magjack", 7.5, VIOLET)
    x = FIELD_X0
    for lab, n in FIELD_GROUPS:
        rect(x, 0, x + n * PITCH, TERM_D, PANEL, AMBER, 1.2)
        txt(x + n * PITCH / 2, TERM_D / 2 - 1, lab, 7, AMBER, weight="600")
        x += n * PITCH
    for i, (x0, w) in enumerate(out_islands()):
        rect(x0 + (w - 2 * PITCH) / 2, 0, x0 + (w + 2 * PITCH) / 2, TERM_D,
             PANEL, GREEN, 1.2)
        txt(x0 + w / 2, TERM_D / 2 - 1, f"DO{i+1}", 8, GREEN, weight="600")
        txt(x0 + w / 2, OUT["y1"] - 7, "AQY212GS", 7.5, GREEN)

    txt(BOARD_W / 2, -7.5,
        f"one edge: RJ45 + {FIELD_N} field positions ({FIELD_N*PITCH:.0f} mm) "
        f"+ {N_OUT*2} output positions", 9.5, INK)

    # LED row inside the visible band
    n_di = FIELD_GROUPS[0][1]
    for i in range(n_di):
        cx, cy = px(FIELD_X0 + 1.75 + i * PITCH, 40.0)
        o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.1" fill="{BLUE}"/>')
    txt(FIELD_X0 + n_di * PITCH / 2, 44.0, f"{n_di} x DI LED", 8, BLUE)
    for x0, w in out_islands():
        cx, cy = px(x0 + w / 2, 40.0)
        o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.1" fill="{BLUE}"/>')
    txt((OUT["x0"] + OUT["x1"]) / 2, 44.0, "2 x DO LED", 8, BLUE)
    for i in range(4):
        cx, cy = px(8.0 + i * 5.0, 40.0)
        o.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.1" fill="{BLUE}"/>')
    txt(16.0, 44.0, "system", 8, BLUE)

    # indicative placement
    parts = [(52, 52, 17, 17, "MCX N247", BLUE), (75, 54, 12, 10, "PHY", BLUE),
             (92, 54, 10, 8, "flash", BLUE), (92, 66, 11, 8, "SE051", BLUE),
             (8, 56, 15, 12, "12V rail", BLUE), (28, 56, 14, 10, "bucks", BLUE),
             (25, 5, 13, 12, "Si3402", VIOLET), (25, 19, 13, 12, "flyback", VIOLET),
             (52, 13, 20, 9, "ISO1211 x3", AMBER), (76, 13, 16, 9, "ISO3082", AMBER),
             (78, 24, 14, 9, "xfmr", AMBER)]
    for x, y, w, h, lab, col in parts:
        rect(x, y, x + w, y + h, PANEL, col, 1.0, dash="3 2")
        txt(x + w / 2, y + h / 2 - 1.2, lab, 7.5, col)

    # dimensions
    ax, ay = px(0, -14); bx, by = px(BOARD_W, -14)
    o.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{MUTED}" stroke-width="1"/>')
    o.append(f'<text x="{(ax+bx)/2:.1f}" y="{ay-5:.1f}" font-size="9.5" fill="{MUTED}" '
             f'text-anchor="middle">{BOARD_W:.1f} +/-0.1 mm</text>')
    ax, ay = px(-8, 0); bx, by = px(-8, BOARD_H)
    o.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="{MUTED}" stroke-width="1"/>')
    o.append(f'<text x="{ax-6:.1f}" y="{(ay+by)/2:.1f}" font-size="9.5" fill="{MUTED}" '
             f'text-anchor="middle" transform="rotate(-90 {ax-6:.1f} {(ay+by)/2:.1f})">'
             f'{BOARD_H:.1f} +/-0.1 mm</text>')

    ly = 676
    for i, (c_, t) in enumerate([(VIOLET, "cable / PSE domain"), (BLUE, "logic domain"),
                                 (AMBER, "field 24 V domain"),
                                 (GREEN, "output islands, each floating"),
                                 (RED, "isolation slot, 1.6 mm")]):
        o.append(f'<rect x="30" y="{ly + i*17 - 9}" width="11" height="11" rx="2" fill="{c_}"/>')
        o.append(f'<text x="48" y="{ly + i*17}" font-size="10.5" fill="{MUTED}">{t}</text>')

    o.append(f'<text x="330" y="{ly-4}" font-size="10.5" font-weight="700" fill="{INK}">'
             f'Single-edge layout: what it costs</text>')
    for i, t in enumerate([
            "Every domain must reach the connector edge, so they are columns, not strips.",
            "Barriers 1, 2 and 3 become U-shaped and total slot length roughly doubles.",
            "The logic domain is the background; the other three are peninsulas rising from Y=0.",
            "Only 72 mm of the 139 mm edge is used, so spacing between columns is generous.",
            "LEDs must stay inside the dashed band - the outer 13.8 mm strips sit under the shelves."]):
        o.append(f'<text x="330" y="{ly + 14 + i*15}" font-size="10" fill="{MUTED}">{t}</text>')

    o.append('</svg>')
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(o))
    print("wrote", path)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    build_dxf(os.path.join(here, "poetato-outline.dxf"))
    build_svg(os.path.join(here, "..", "img", "floorplan.svg"))
