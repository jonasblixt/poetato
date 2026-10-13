# PoEtato — PCB stackup and controlled impedance

The board is 6 layers on JLCPCB's **JLC06161H-2116A** stackup (decided
2026-10-13), with controlled impedance for the RMII, USB and Ethernet MDI nets.

The same stackup and the impedance table are drawn on the `User.Stackup`
layer (User.3) of `hw/poetato/poetato.kicad_pcb`, to the right of the board.
The widths come from `doc/scripts/impedance.py` (§4).

---

## 1. Stackup

1.6 mm finished, 1 oz outer copper, 0.5 oz inner copper, FR-4. Thicknesses and
Dk are from JLCPCB's impedance page (jlcpcb.com/impedance), read 2026-10-13.

| Layer | Use | Material | Thickness | Dk |
|---|---|---|---|---|
| F.Cu | **L1 signal** | Copper 1 oz | 0.035 mm | |
| | | Prepreg 2116 | 0.1164 mm | 4.16 |
| In1.Cu | **L2 GND** | Copper 0.5 oz | 0.0152 mm | |
| | | Core | 0.13 mm | 4.6 |
| In2.Cu | **L3 signal** | Copper 0.5 oz | 0.0152 mm | |
| | | Prepreg 2116 | 0.1164 mm | 4.16 |
| | | Core, no copper | 0.70 mm | 4.6 |
| | | Prepreg 2116 | 0.1164 mm | 4.16 |
| In3.Cu | **L4 PWR** | Copper 0.5 oz | 0.0152 mm | |
| | | Core | 0.13 mm | 4.6 |
| In4.Cu | **L5 GND** | Copper 0.5 oz | 0.0152 mm | |
| | | Prepreg 2116 | 0.1164 mm | 4.16 |
| B.Cu | **L6 signal** | Copper 1 oz | 0.035 mm | |

Laminate total 1.556 mm, plus solder mask (Dk 3.8).

The layer order was read from a flattened table on JLCPCB's page. Check it
against their stackup viewer before ordering.

## 2. Why this stackup

The layer assignment is Sig / GND / Sig / PWR / GND / Sig. Two things follow
from it:

- **L3 must return its current in GND, not PWR.** It needs to sit much closer
  to L2 than to L4. On 2116A it is 0.13 mm from L2 and 0.93 mm from L4.
- **L4 PWR and L5 GND should be close.** The planes then act as a distributed
  decoupling capacitor. On 2116A they are 0.13 mm apart.

Only JLCPCB's thin-core stackups do both. Of those, 2116A has the thickest
outer prepreg, so it gives the widest traces.

| Rejected | Why |
|---|---|
| JLC06161H-3313, -1080A, -2116B (thick cores) | L3 sits 0.10–0.15 mm from L4 PWR and 0.5–0.6 mm from L2 GND, so it references PWR. L4–L5 is 0.5 mm or more, so the planes barely couple |
| JLC06161H-1080B, -1080C, -3313E (thin cores, thinner outer prepreg) | Same structure as 2116A but with 0.076–0.099 mm to L2. The 100 Ω differential pairs come out at 0.06–0.10 mm wide, at or below JLCPCB's 0.09 mm minimum, where the etch tolerance becomes a large share of the width |
| 0.18 mm or more to L2 (-3313C, -3313D, -2116, -2116C, the 7628 family) | The outer 50 Ω trace grows to roughly 0.3 mm or more (estimated, not solved), wider than the 0.5 mm-pitch QFP pads it starts from. The L4–L5 gap is 0.1–0.4 mm |

## 3. Impedance classes

| Class | Nets | L1 / L6, W / S | L3, W / S | Reference |
|---|---|---|---|---|
| 50 Ω single-ended | RMII: `ETH_REF_CLK`, `ETH_TXD0/1`, `ETH_TXEN`, `ETH_RXD0/1`, `ETH_RXDV`. Optional: QSPI | 0.18 mm | 0.16 mm | L2 / L5 GND |
| 90 Ω differential | `USB_DP` / `USB_DM`, connector → USBLC6 → MCU | 0.16 / 0.15 mm | 0.13 / 0.15 mm | L2 / L5 GND |
| 100 Ω differential | `ETH_TX_P/N`, `ETH_RX_P/N`, PHY → magjack | 0.14 / 0.20 mm | 0.12 / 0.20 mm | L2 / L5 GND |

W is the trace width, S the gap between the two traces of a pair.

- **`ETH_REF_CLK` matters most.** It is the 50 MHz clock from the MCU into the
  PHY's XI pin through a 33 Ω series resistor. Treat the rest of RMII as best
  effort.
- **QSPI is optional.** The S25FL064L runs up to about 108 MHz, but on traces
  of a few centimetres the series termination matters more than the impedance.
  Route at the 50 Ω width anyway, because it costs nothing.
- **Not controlled:** RS-485 A/B (slow, short on-board stubs), SWD, MDC/MDIO,
  the crystals, field I/O.

## 4. How the widths were computed

`doc/scripts/impedance.py` is a 2D field solver. It solves the cross-section
on a nonuniform grid and computes Z0 from the capacitance with and without the
dielectric. `--check` compares it with two analytic cases, centred stripline
and microstrip, and it agrees with both within about 1 %.

```sh
pip install numpy scipy
python doc/scripts/impedance.py                 # JLC06161H-2116A
python doc/scripts/impedance.py --stackup all   # the thin-core candidates
python doc/scripts/impedance.py --check
```

Assumptions:

- 35 µm finished outer copper, 15.2 µm inner copper.
- Solder mask Dk 3.8, 30 µm over laminate, 15 µm over copper.
- Rectangular trace cross-section. Real traces are trapezoidal, which raises
  the impedance by a few ohms.

Expect the results to be within about ±5 % of the fab. **JLCPCB's impedance
calculator is the reference for the order:** confirm the widths there for
JLC06161H-2116A, and update §3 and the drawing on the board if they differ.

## 5. Routing rules that follow from the stackup

- Route controlled nets on L1 and L6 over unbroken GND on L2 and L5. No splits
  or slots under them.
- Route L3 signals only where L2 is unbroken GND. L4 is too far away to serve
  as a return path.
- When a controlled net changes layer, place a GND stitching via next to the
  signal via, so the return current can follow it between L2 and L5.

## 6. Open items

- **Confirm the widths** in JLCPCB's impedance calculator (§4).
- **Physical stackup in Board Setup** still has KiCad's default 6-layer
  stack. Enter the §1 values so KiCad's own stackup outputs match.
- **Net classes** for the three impedance classes (and QSPI, if it is routed
  at 50 Ω) are not created yet. The project has only `Default`.
- **Order with impedance control** and stackup JLC06161H-2116A. The impedance
  test report is checked in `doc/verification-plan.md` §8.
