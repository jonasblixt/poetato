#!/usr/bin/env python3
"""Generate the PoEtato architecture SVGs."""
import os, html

OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

BG     = "#FAF9F7"
PANEL  = "#FFFFFF"
INK    = "#22201D"
MUTED  = "#6E6862"
RULE   = "#D9D4CC"

VIOLET = "#6B4E9E"; VIOLET_T = "#F3EFF8"
BLUE   = "#2C6BAA"; BLUE_T   = "#EAF1F8"
AMBER  = "#B5751A"; AMBER_T  = "#FBF3E7"
GREEN  = "#3E7C4F"; GREEN_T  = "#EDF4EE"
RED    = "#B33A3A"; RED_T    = "#FAEDED"

FONT = "ui-sans-serif,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,'SF Mono',Menlo,Consolas,monospace"


def esc(s):
    return html.escape(str(s), quote=False)


def head(w, h, title, subtitle=None):
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'viewBox="0 0 {w} {h}" font-family="{FONT}" role="img" '
         f'aria-label="{esc(title)}">']
    s.append('<defs>'
             f'<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
             f'markerHeight="7" orient="auto-start-reverse">'
             f'<path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker>'
             '</defs>')
    s.append(f'<rect width="{w}" height="{h}" fill="{BG}"/>')
    s.append(f'<text x="30" y="36" font-size="20" font-weight="600" fill="{INK}">{esc(title)}</text>')
    if subtitle:
        s.append(f'<text x="30" y="58" font-size="13" fill="{MUTED}">{esc(subtitle)}</text>')
    return s


def domain(s, x, y, w, h, label, stroke, tint):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{tint}" '
             f'stroke="{stroke}" stroke-width="1.2" stroke-opacity="0.45"/>')
    s.append(f'<text x="{x+14}" y="{y+22}" font-size="11" font-weight="700" '
             f'letter-spacing="1.1" fill="{stroke}">{esc(label)}</text>')


def box(s, x, y, w, h, lines, stroke=INK, fill=PANEL, fs=13, bold_first=True):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" '
             f'stroke="{stroke}" stroke-width="1.4"/>')
    n = len(lines)
    lh = 16 if fs <= 13 else 18
    total = n * lh
    start = y + (h - total) / 2 + lh - 4
    for i, ln in enumerate(lines):
        weight = "600" if (i == 0 and bold_first) else "400"
        size = fs if i == 0 else fs - 2
        col = INK if i == 0 else MUTED
        s.append(f'<text x="{x+w/2}" y="{start + i*lh}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{col}" text-anchor="middle">{esc(ln)}</text>')


def barrier(s, x, y0, y1, label):
    s.append(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y1}" stroke="{RED}" '
             f'stroke-width="1.6" stroke-dasharray="7 5" stroke-opacity="0.75"/>')
    s.append(f'<text x="{x-5}" y="{y1-4}" font-size="10.5" font-weight="600" fill="{RED}" '
             f'text-anchor="start" transform="rotate(-90 {x-5} {y1-4})">{esc(label)}</text>')


def path(s, d, label=None, lx=0, ly=0, color=MUTED, anchor="middle"):
    s.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5" '
             f'marker-end="url(#ar)"/>')
    if label:
        s.append(f'<text x="{lx}" y="{ly}" font-size="11" fill="{color}" '
                 f'text-anchor="{anchor}">{esc(label)}</text>')


def note(s, x, y, lines, fs=11, color=MUTED, anchor="start"):
    for i, ln in enumerate(lines):
        s.append(f'<text x="{x}" y="{y + i*16}" font-size="{fs}" fill="{color}" '
                 f'text-anchor="{anchor}">{esc(ln)}</text>')


def write(name, s):
    s.append('</svg>')
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(s))
    print("wrote", p)


# ----------------------------------------------------------------- 1. system
def system_block():
    W, H = 1240, 650
    s = head(W, H, "PoEtato - System Block Diagram",
             "PoE only - MCX N247, 3 isolated inputs, 2 OptoMOS outputs, RS-485, SE050 key store")

    domain(s, 28, 78, 222, 410, "ETHERNET / PSE SIDE", VIOLET, VIOLET_T)
    domain(s, 286, 78, 414, 410, "LOGIC DOMAIN", BLUE, BLUE_T)
    domain(s, 736, 78, 244, 410, "FIELD DOMAIN  24 V", AMBER, AMBER_T)
    domain(s, 1016, 78, 196, 410, "OUTPUT CHANNELS", GREEN, GREEN_T)

    barrier(s, 268, 70, 560, "barrier 1  -  magnetics + flyback")
    barrier(s, 718, 70, 560, "barrier 2  -  field")
    barrier(s, 998, 70, 560, "barrier 3  -  per channel")

    # PSE side
    box(s, 44, 118, 190, 52, ["RJ45 + magjack", "integrated magnetics"], VIOLET)
    box(s, 44, 186, 190, 48, ["PD bridge + class.", "802.3af Type 1"], VIOLET)
    box(s, 44, 250, 190, 52, ["Si3402-B", "isolated flyback"], VIOLET)
    note(s, 46, 336, ["48 V from PSE, UPS-backed.", "No mains anywhere", "inside the enclosure."])

    # Logic column A - power and the fault chain
    box(s, 302, 118, 176, 46, ["KSZ8081RNB PHY", "RMII, MDIO on P1_2/3"], BLUE)
    box(s, 302, 180, 176, 44, ["12 V rail"], BLUE)
    box(s, 302, 238, 176, 44, ["Buck  3V3"], BLUE)
    box(s, 302, 296, 176, 52, ["LP3470 supervisor", "drives RESET_N"], RED, fs=12)
    box(s, 302, 364, 176, 44, ["2x NTK3134N low-side"], RED, fs=12)
    box(s, 302, 424, 176, 44, ["2x LED drive, 220R"], RED, fs=12)

    # Logic column B - compute
    box(s, 498, 118, 186, 120,
        ["MCX N247 (MCXN247VKLT)", "Cortex-M33 @ 150 MHz, TrustZone", "HLQFP100, -40..+125 C", "2 MB flash / 512 KB SRAM"], BLUE)
    box(s, 498, 258, 186, 48, ["SE050C2 secure element", "I2C 0x48, own bus"], BLUE, fs=12)
    box(s, 498, 320, 186, 44, ["QSPI (optional, data only)"], BLUE, fs=12)
    box(s, 498, 378, 186, 44, ["USB HS recovery / SWD"], BLUE, fs=12)

    # Field domain
    box(s, 752, 118, 212, 52, ["SN6507 push-pull", "isolated 24 V, 3 W"], AMBER)
    box(s, 752, 186, 212, 54, ["3x ISO1211 field side", "each channel isolated, Type 3"], AMBER)
    box(s, 752, 254, 212, 54, ["ISO3082 + buck 5V", "RS-485 / Modbus RTU"], AMBER)
    box(s, 752, 322, 212, 48, ["24 V field out", "PTC limited"], AMBER)

    # Output channels
    for i in range(2):
        box(s, 1032, 118 + i * 56, 164, 44, [f"OptoMOS CH{i+1}"], GREEN, fs=12)
    note(s, 1032, 252, ["AQY212GS, 60 V / 1 A", "true dry contact,", "each pair floating"])

    # connectors
    path(s, "M234,142 L300,142", "10/100", 267, 134)
    path(s, "M234,276 L268,276 L268,202 L300,202", "12 V", 264, 246, anchor="end")
    path(s, "M478,141 L488,141 L488,152 L496,152", "RMII", 468, 112)
    path(s, "M496,230 L488,230 L488,386 L480,386", "DOn_ON", 484, 292, anchor="end")
    path(s, "M390,408 L390,422", "LED sink", 398, 418, anchor="start")
    path(s, "M684,178 L718,178 L718,213 L750,213", "3x GPIO", 706, 170)
    path(s, "M684,214 L702,214 L702,281 L750,281", "UART", 702, 302, anchor="start")
    path(s, "M478,446 L488,446 L488,506 L1176,506 L1176,220", "output LED drive", 830, 500)

    # terminals
    note(s, 752, 534, ["+24V FLD  -  0V FLD  -  DI1+/- .. DI3+/-",
                       "RS-485 A / B / GND / shield  -  sensor 24 V"], 11.5, INK)
    note(s, 1032, 534, ["DO1, DO2", "isolated pairs"], 11.5, INK)

    # legend
    lx = 30
    for i, (c, t) in enumerate([(VIOLET, "cable side"), (BLUE, "logic"),
                                (AMBER, "field 24 V"), (GREEN, "output, floating"),
                                (RED, "fault / safety chain")]):
        s.append(f'<rect x="{lx}" y="{568 + i*15 - 8}" width="9" height="9" rx="2" fill="{c}"/>')
        s.append(f'<text x="{lx+14}" y="{568 + i*15}" font-size="10.5" fill="{MUTED}">{esc(t)}</text>')

    write("system-block.svg", s)


# ------------------------------------------------------------------ 2. power
def power_tree():
    W, H = 1080, 790
    s = head(W, H, "PoEtato - Power Tree",
             "PoE only - 4.14 W of the 12.95 W 802.3af Type 1 budget, so Class 2")

    barrier(s, 300, 100, 462, "barrier 1  -  flyback")
    barrier(s, 636, 100, 462, "barrier 2  -  push-pull")

    box(s, 40, 120, 220, 56, ["PSE  48 V", "UPS-backed, main building"], VIOLET)
    box(s, 40, 208, 220, 56, ["PD bridge + class.", "802.3af Type 1"], VIOLET)
    box(s, 40, 296, 220, 62, ["Si3402-B flyback", "48 V -> 12 V isolated", "approx. 85% eff."], VIOLET)

    box(s, 336, 120, 262, 54, ["12 V logic rail", "approx. 1.2 A available"], BLUE)
    box(s, 336, 206, 124, 56, ["Buck 3V3", "MCU + PHY", "~1.0 W"], BLUE, fs=12)
    box(s, 474, 206, 124, 56, ["OptoMOS LEDs", "3V3, NTK3134N", "~0.05 W"], RED, fs=12)
    box(s, 336, 294, 262, 58, ["SN6507 push-pull", "12 V -> 24 V, ~1:2 ratio", "3 W isolated"], AMBER)

    box(s, 672, 120, 250, 58, ["Digital inputs, via contacts", "3 ch x 2.47 mA @ 24 V", "0.18 W worst case"], AMBER)
    box(s, 672, 202, 250, 58, ["Buck 24V -> 5V", "ISO3082 field side", "0.15 W"], AMBER)
    box(s, 672, 284, 250, 62, ["Field sensor supply", "24 V out, PTC 150 mA", "1.5 W allocated"], AMBER)
    box(s, 672, 388, 250, 70, ["OptoMOS LED drive", "2 ch, GPIO -> NTK3134N",
                                "220R from 3V3", "0.05 W"], GREEN, fs=12)
    note(s, 672, 476, ["The field 24 V always comes from the",
                       "push-pull - never straight from the",
                       "external 24 V input, which would short",
                       "out barrier 2."], 11, INK)

    path(s, "M150,176 L150,206")
    path(s, "M150,264 L150,294")
    path(s, "M260,326 L312,326 L312,147 L334,147")
    path(s, "M398,174 L398,204")
    path(s, "M460,234 L472,234")
    path(s, "M467,174 L467,292")
    path(s, "M598,322 L636,322 L636,149 L670,149")
    path(s, "M598,322 L636,322 L636,231 L670,231")
    path(s, "M598,322 L636,322 L636,315 L670,315")
    path(s, "M536,262 L610,262 L610,417 L670,417")

    tbl = [
        ("Logic: MCX N247 + KSZ8081 + SE050", "1.05 W"),
        ("Digital inputs, 3 channels closed", "0.18 W"),
        ("Field rail preload (10 kOhm)", "0.07 W"),
        ("RS-485 field side via buck", "0.15 W"),
        ("Field sensor supply allocation", "1.50 W"),
        ("OptoMOS drive, 2 channels (from 3V3)", "0.05 W"),
        ("Isolated converter losses (approx. 20%)", "0.50 W"),
        ("PD flyback losses (approx. 15%)", "0.64 W"),
    ]
    y0 = 566
    s.append(f'<rect x="40" y="{y0-28}" width="882" height="{len(tbl)*20+64}" rx="8" '
             f'fill="{PANEL}" stroke="{RULE}"/>')
    s.append(f'<text x="58" y="{y0-8}" font-size="12.5" font-weight="700" fill="{INK}">'
             f'Power budget at the PD input</text>')
    for i, (k, v) in enumerate(tbl):
        yy = y0 + 16 + i * 20
        s.append(f'<text x="58" y="{yy}" font-size="11.5" fill="{MUTED}">{esc(k)}</text>')
        s.append(f'<text x="880" y="{yy}" font-size="11.5" font-family="{MONO}" '
                 f'fill="{INK}" text-anchor="end">{esc(v)}</text>')
    yy = y0 + 16 + len(tbl) * 20
    s.append(f'<line x1="58" y1="{yy-14}" x2="880" y2="{yy-14}" stroke="{RULE}"/>')
    s.append(f'<text x="58" y="{yy+2}" font-size="11.5" font-weight="700" fill="{INK}">'
             f'Total drawn / available</text>')
    s.append(f'<text x="880" y="{yy+2}" font-size="11.5" font-family="{MONO}" '
             f'font-weight="700" fill="{INK}" text-anchor="end">4.14 W / 12.95 W</text>')

    write("power-tree.svg", s)


# ------------------------------------------------------------------ 3. input
def input_channel():
    W, H = 1200, 560
    s = head(W, H, "PoEtato - Isolated Input Channel",
             "ISO1211, sinking, IEC 61131-2 Type 3 - one isolated channel per input, 3 channels")

    domain(s, 34, 96, 560, 286, "FIELD SIDE  24 V", AMBER, AMBER_T)
    domain(s, 990, 96, 176, 286, "LOGIC SIDE", BLUE, BLUE_T)

    box(s, 54, 140, 136, 52, ["+24V FLD", "terminal"], AMBER, fs=12)
    box(s, 54, 300, 136, 52, ["DIn-  terminal", "wire to 0V FLD"], AMBER, fs=12)

    # contact symbol
    s.append(f'<line x1="190" y1="166" x2="246" y2="166" stroke="{INK}" stroke-width="1.6"/>')
    s.append(f'<circle cx="250" cy="166" r="4" fill="{PANEL}" stroke="{INK}" stroke-width="1.6"/>')
    s.append(f'<line x1="253" y1="163" x2="292" y2="150" stroke="{INK}" stroke-width="1.6"/>')
    s.append(f'<circle cx="296" cy="166" r="4" fill="{PANEL}" stroke="{INK}" stroke-width="1.6"/>')
    s.append(f'<line x1="300" y1="166" x2="334" y2="166" stroke="{INK}" stroke-width="1.6"/>')
    note(s, 196, 208, ["reed switch, wall button", "or 3-wire PNP sensor"], 11.5)

    box(s, 336, 140, 104, 52, ["R_THR", "1 k MELF"], AMBER, fs=12)
    box(s, 456, 140, 124, 52, ["TVS SMF36A", "+ C_IN 10 nF"], AMBER, fs=12)

    # the chip straddles its own barrier
    s.append(f'<text x="792" y="134" font-size="13.5" font-weight="600" fill="{INK}" '
             f'text-anchor="middle">ISO1211  -  single-channel isolated input</text>')
    s.append(f'<rect x="614" y="146" width="356" height="144" rx="6" fill="{PANEL}" '
             f'stroke="{INK}" stroke-width="1.4"/>')
    barrier(s, 792, 152, 284, "internal barrier")
    s.append(f'<text x="700" y="176" font-size="10.5" font-weight="700" letter-spacing="1" '
             f'fill="{AMBER}" text-anchor="middle">FIELD</text>')
    s.append(f'<text x="884" y="176" font-size="10.5" font-weight="700" letter-spacing="1" '
             f'fill="{BLUE}" text-anchor="middle">LOGIC</text>')
    note(s, 700, 202, ["R_SENSE 562 R", "current limit 2.25 mA", "self-powered from input"], 11.5,
         MUTED, anchor="middle")
    note(s, 884, 202, ["push-pull OUT", "EN = DI_EN (shared)", "VCC1 = 3V3"], 11.5,
         MUTED, anchor="middle")

    box(s, 1006, 186, 144, 64, ["GPIO + 2.2 k pull-down", "to MCX N247"], BLUE, fs=11)

    path(s, "M440,166 L454,166")
    path(s, "M580,166 L612,166", "SENSE", 596, 158)
    path(s, "M190,326 L660,326 L660,292", "FGND = DIn-", 400, 318)
    path(s, "M970,218 L1004,218")

    note(s, 40, 424, [
        "2.25 mA of wetting current with 24 V open-circuit sits well above any fritting threshold, while the",
        "chip's current limiter keeps input power flat with supply voltage instead of rising linearly.",
    ], 11.5, INK)
    note(s, 40, 470, [
        "Each input is its own floating pair DIn+/DIn-. No wire-break or field-supply detection: firmware",
        "debounces and treats inputs as valid only with the field supply on. Silkscreen +24V FLD / 0V FLD - never COM.",
    ], 11.5, MUTED)

    write("input-channel.svg", s)


# ----------------------------------------------------------------- 4. output
def output_channel():
    W, H = 1180, 560
    s = head(W, H, "PoEtato - Output Channel",
             "Plain GPIO drives a low-side FET that sinks the LED - one of two channels")

    domain(s, 34, 96, 686, 286, "LOGIC SIDE", BLUE, BLUE_T)
    domain(s, 768, 96, 366, 286, "FIELD SIDE  floating", GREEN, GREEN_T)
    barrier(s, 744, 90, 392, "barrier 3  -  per channel")

    box(s, 54, 132, 152, 60, ["MCU GPIO", "DOn_ON, hi-Z in reset"], BLUE, fs=12)
    box(s, 54, 250, 152, 60, ["2.2 k pull-down", "gate off in reset"], RED, fs=12)
    box(s, 266, 250, 196, 60, ["NTK3134N", "low-side LED sink"], RED, fs=12)
    box(s, 506, 132, 200, 78, ["LED drive", "220R from 3V3", "approx. 10 mA, >= 7.8 mA worst"],
        BLUE, fs=12)

    box(s, 790, 132, 196, 78, ["AQY212GS", "PhotoMOS relay", "60 V / 1 A, AC+DC"], GREEN)
    box(s, 790, 250, 196, 60, ["10R + PPTC + TVS", "at the terminal"], GREEN, fs=12)
    box(s, 1012, 132, 104, 78, ["DOn", "A / B", "terminals"], GREEN, fs=12)

    path(s, "M206,162 L230,162 L230,280 L264,280", "gate", 236, 222, anchor="start")
    path(s, "M130,192 L130,248")
    path(s, "M364,250 L364,200 L504,200", "LED cathode", 372, 226, anchor="start")
    path(s, "M706,171 L788,171", "optical", 747, 163)
    path(s, "M888,210 L888,248")
    path(s, "M986,280 L1064,280 L1064,212")

    note(s, 40, 424, [
        "The LED is fed from 3V3 through 220R and sunk by an NTK3134N whose gate a plain GPIO drives. The 2.2 k pull-down holds the",
        "gate low whenever the pin is hi-Z, so any reset opens the contact. No interlock: a stuck GPIO or shorted FET = stuck button.",
    ], 11.5, INK)
    note(s, 40, 478, [
        "A refresh-driven charge pump was considered and dropped: with hardware-timer PWM a hung core keeps the timer",
        "running, so it would not have caught the case it existed for - and it adds an ageing circuit that fails toward",
        "intermittent rather than toward off. Maximum on-time is enforced in software instead, and reported.",
    ], 11.5, MUTED)

    write("output-channel.svg", s)


# ------------------------------------------------------------------ 5. fault
def fault_arch():
    W, H = 1160, 616
    s = head(W, H, "PoEtato - Fault Architecture",
             "One watchdog, and output FETs that every reset turns off")

    box(s, 40, 110, 200, 80, ["Application tasks", "each sets a flag", "flags cleared on feed"], BLUE)
    box(s, 40, 230, 200, 66, ["Supervisor thread", "all flags present?"], BLUE)

    box(s, 296, 84, 220, 66, ["LP3470 supervisor", "power-up, brown-out"], BLUE)
    box(s, 296, 190, 220, 90, ["MCX N WWDT", "windowed, ~1 s timeout", "MOD[LOCK], warning IRQ"], RED)
    box(s, 572, 150, 220, 90, ["RESET_b", "pin reset state:", "DO1_ON / DO2_ON hi-Z"], RED)
    box(s, 858, 150, 262, 90, ["2x NTK3134N LED sink", "2.2 k gate pull-downs", "no hardware interlock"],
        RED, fill=RED_T)
    box(s, 572, 336, 220, 90, ["Re-arm policy", "reset counter, retained RAM", ">= 3 in a row: stay disarmed"], BLUE)
    box(s, 960, 336, 160, 70, ["OptoMOS CH1/CH2", "open on any reset"], GREEN, fs=12)

    path(s, "M140,190 L140,228")
    path(s, "M240,263 L268,263 L268,235 L294,235", "feed", 272, 228, anchor="start")
    path(s, "M516,117 L544,117 L544,168 L570,168", "reset", 548, 140, anchor="start")
    path(s, "M516,215 L570,215", "reset", 543, 207)
    path(s, "M792,195 L856,195", "hi-Z = off", 824, 187)
    path(s, "M792,371 L900,371 L900,242", "arm", 846, 363)
    path(s, "M1040,240 L1040,334")

    s.append(f'<rect x="40" y="448" width="1080" height="124" rx="8" fill="{PANEL}" '
             f'stroke="{RULE}"/>')
    note(s, 58, 474, [
        "Every reset opens the outputs: the DOn_ON pins go hi-Z and the gate pull-downs - not firmware - hold both LED FETs off.",
        "The WWDT turns a hung core into a reset within ~1 s. On the opener's toggle input that is a long button press.",
        "A watchdog proves liveness, not correctness. Live-but-wrong software is bounded by a software maximum on-time and the opener's own safety.",
        "No output is pulsed during boot. Three abnormal resets in a row leave the outputs disarmed until a command or a power cycle.",
        "Residual: core hung with an output on AND the WWDT failing = stuck button until a PoE power cycle. The door does not move.",
    ], 11.5, INK)

    write("fault-architecture.svg", s)


# ------------------------------------------------------------- 6. boot chain
def boot_chain():
    W, H = 1160, 640
    s = head(W, H, "PoEtato - Boot Chain and Flash Map",
             "MCX N ROM authenticates punchboot, punchboot authenticates the application")

    y = 108
    box(s, 40, y, 232, 92,
        ["BootROM", "MCX N secure boot", "RoT key hash in CMPA/OTP", "immutable"], VIOLET)
    box(s, 316, y, 232, 92,
        ["punchboot (ported)", "bpak, signed", "A/B + rollback", "updatable"], RED)
    box(s, 592, y, 232, 92,
        ["Zephyr application", "slot A or slot B", "internal flash", "updatable"], BLUE)
    box(s, 868, y, 232, 92,
        ["SE050", "private-key custody", "key never leaves", "TLS provisioning"], GREEN)

    path(s, "M272,154 L314,154", "authenticates", 293, 146)
    path(s, "M548,154 L590,154", "authenticates", 569, 146)
    path(s, "M824,154 L866,154", "uses", 845, 146)

    note(s, 40, 228, [
        "Root of trust is the key hash in CMPA/OTP - programming it and advancing the lifecycle is effectively one-way.",
        "Signatures are ECDSA P-256, verified on the PKC hardware accelerator; hashing on ELS. Keep the format open to PQC later.",
    ], 11.5, INK)

    # ---- flash map
    fy = 300
    s.append(f'<text x="40" y="{fy-14}" font-size="13.5" font-weight="600" fill="{INK}">'
             f'Internal flash - 2 MB, two 1 MB banks (not to scale)</text>')
    parts = [
        ("punchboot", "bank 0 - 128 KB", 140, RED, RED_T),
        ("pb state A", "1 sector", 95, RED, RED_T),
        ("pb state B", "1 sector", 95, RED, RED_T),
        ("app slot A", "bank 0 - ~880 KB", 250, BLUE, BLUE_T),
        ("app slot B", "bank 1 - ~880 KB", 300, BLUE, BLUE_T),
        ("config / logs", "~128 KB", 120, GREEN, GREEN_T),
    ]
    x = 60
    for name, size, w, stroke, tint in parts:
        s.append(f'<rect x="{x}" y="{fy}" width="{w}" height="64" rx="4" fill="{tint}" '
                 f'stroke="{stroke}" stroke-width="1.4"/>')
        s.append(f'<text x="{x+w/2}" y="{fy+27}" font-size="12.5" font-weight="600" '
                 f'fill="{INK}" text-anchor="middle">{esc(name)}</text>')
        s.append(f'<text x="{x+w/2}" y="{fy+46}" font-size="11.5" fill="{MUTED}" '
                 f'text-anchor="middle">{esc(size)}</text>')
        x += w

    note(s, 40, 400, [
        "One application slot per flash bank. The slots live at different addresses, so the application is either linked per",
        "slot or the banks are swapped/remapped in hardware. Check the MCX N reference manual for bank swap/remap and decide",
        "before the build system. External QSPI is optional and never holds code.",
    ], 11.5, INK)

    # ---- recovery
    ry = 476
    s.append(f'<rect x="40" y="{ry}" width="1060" height="130" rx="8" fill="{PANEL}" '
             f'stroke="{RULE}"/>')
    s.append(f'<text x="58" y="{ry+24}" font-size="12.5" font-weight="700" fill="{INK}">'
             f'Recovery path - a hard board requirement, not a nicety</text>')
    note(s, 58, ry + 48, [
        "punchboot-tools talks over USB, so USB is a production and recovery interface here, not only a debug port.",
        "USB1 HS (pins 40-43) with a 24 MHz crystal; the ISP boot pin stays reachable so the ROM ISP can be forced if punchboot is bricked.",
        "Keep at least one board with the lifecycle not advanced for development - budget the extra board up front.",
        "Anti-rollback counter belongs in MCU OTP, not the SE050: a boot-time I2C dependency adds a failure mode for no real gain.",
    ], 11.5, MUTED)

    write("boot-chain.svg", s)


system_block()
power_tree()
input_channel()
output_channel()
fault_arch()
boot_chain()
print("done")
