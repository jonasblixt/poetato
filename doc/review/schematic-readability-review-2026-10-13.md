# PoEtato schematic readability review

This review covers **readability only**: signal flow direction, density and sheet structure, font size consistency, naming, and text that collides with other items. Electrical correctness is covered by the 2026-10-09 review and is not repeated here. Like the other reviews, this is a living document: rows are updated in place and fixed items stay in the tables.

| | |
|---|---|
| Review started | 2026-10-13 |
| Revision checked | git `a62dd31` (schematic files unmodified in the working copy; only `poetato.kicad_pcb` had local changes). |
| Tools | `kicad-cli` 10.0.6 PDF export of all 10 sheets, rendered to PNG at 110 and 200 dpi and inspected visually. Font sizes and bold flags were read directly from the `.kicad_sch` files, not estimated from the renders. |
| Sheets | root `poetato`, `ethernet_poe`, `mcu`, `io` with sub-sheets `rs485`, `di` ×3, `do` ×2. |
| Preference applied | Inputs on the left, outputs on the right. Logic on the left and field on the right, where a sheet has both. |
| Not checked | Electrical content, ERC and netlist. Anything about layout. |

**Status:**
- **Open**: not addressed.
- **Fixed**: verified fixed in the schematic.
- **Resolved (decision)**: stays as it is by decision.

## Summary

The top level, the Ethernet PHY section, the isolated 24 V supply, the DO channel and the RS-485 transceiver already read left to right. Four power blocks and the DI channel read right to left. The MCU and Ethernet & PoE sheets each hold about 80 parts on A3 and are the hardest to read. Meanwhile RS485 is sparse and the top level is about 70 % empty. The smallest text on every sheet is the power symbol text (0.762 mm), and the LED fields are almost as small (0.99 mm).

Suggested order of work:
1. Fonts and value formatting (FONT-*, VAL-1). These are mechanical.
2. Rename and reorder the DO/DI sheets (NAME-1, NAME-2).
3. Mirror the RS-485 5 V buck and the DI channel (FLOW-3, FLOW-4).
4. Split the sheets (DENS-1 to DENS-3). This also fixes FLOW-1 and FLOW-2.

## Findings

### Signal flow

| ID | Status | Sheet | Refs | Finding | Suggested fix |
|---|---|---|---|---|---|
| FLOW-1 | Open | MCU | U18, L4, C82, C83, C85 | **3.3 V buck reads right to left.** P12V0 enters on the right and P3V3 leaves on the left, because the symbol has SW on the left and VIN on the right. | Mirror the block, or redraw the TPS563252 library symbol with VIN on the left. Better still, move it to a power sheet (DENS-1). |
| FLOW-2 | Open | Ethernet & PoE | T3, FB1–FB4, U4, T2, U5, P12V0 | **PoE PD reads right to left across the whole lower half.** Power enters at T3 (far right), passes U4 and then T2, and leaves as P12V0 at the far left edge. | Move it to its own sheet, with POE_CT1/CT2/SP1/SP2 entering from the left as hierarchical labels and P12V0 leaving on the right (DENS-1). |
| FLOW-3 | Open | RS485 | U17, L3, C76, C77, C79, C80, C93 | **5 V isolated buck reads right to left.** VIN (P24V0_FIELD) is on the right and P5V_RS485 leaves on the left. | Mirror the block. The page has plenty of room. |
| FLOW-4 | Open | DI (×3) | U12, R54, R57, D12, C86 | **DI channel reads right to left.** IN_P/IN_N are on the right and OUT is on the left. This conflicts with the logic-left / field-right convention on the IO sheet. | Mirror the leaf sheet so the field input is on the left and OUT/EN are on the right. Keep the IO parent as it is: where pins sit on a sheet symbol is independent of the layout inside the sheet. |
| FLOW-5 | Open | IO | U19, J1, D24 | The 24 V eFuse output leaves U19 OUT at the right edge. The wire then loops back left around the page to reach J1 in the middle. | Put a `P24V0_FIELD_PROT` net label at U19 OUT and at J1 pin 1, and drop the long wire. Alternatively, move the isolated supply to its own sheet. |
| FLOW-6 | Open | MCU | U1 | The DO1_ON/DO2_ON hierarchical labels sit on the left of U1, while DI_EN, DI1–DI3 and P24V_FIELD_EN sit on the right. All of them go to the IO sheet, which is on the right at the top level. This follows from the pin sides of the bank symbol. | Low priority. If U1 is split into units (DENS-2), group the IO bank on the right. |

### Density and sheet structure

| ID | Status | Sheet | Refs | Finding | Suggested fix |
|---|---|---|---|---|---|
| DENS-1 | Open | Ethernet & PoE, MCU | — | **Ethernet & PoE holds ~83 parts on A3 (test points not counted).** The T3 centre taps V1–V4 run from the PHY box down into the PoE box. The blue isolation barrier polyline also cuts across the PHY section to get there. Power is spread over four sheets: 12 V on Ethernet, 3.3 V on MCU, 24 V on IO and 5 V on RS485. | New **PoE & power** sheet: Si3402 → flyback → P12V0 → 3.3 V buck, left to right on one A3. That leaves the Ethernet sheet with just the PHY, straps, T3 and link LEDs. Note that an orphan `power.kicad_sch` was removed in `05cff1d`, so whether a power sheet comes back is your call. |
| DENS-2 | Open | MCU | — | **The MCU sheet holds ~77 parts (test points not counted) and 11 functional blocks:** MCU, SWD, LPUART debug, USB, reset supervisor, flash, SE051, 3.3 V buck, RTC backup, status LEDs, crystals and decoupling. Several nets cross the page as long wires even though they also carry labels: SE_SCL/SE_SDA, SYS_STS_RED/GREEN, RESET_N (from J3 down to the supervisor), ISP_N and LPUART1_RXD/TXD. | Split into **MCU core** (U1, decoupling, crystals, reset/supervisor, VDD_CORE DCDC, RTC backup) and **MCU peripherals** (flash, SE051, SWD, LPUART, USB with ESD, status LEDs). Join them with labels rather than page-length wires. |
| DENS-3 | Fixed | Top level | — | The top level is about 70 % empty, and the power architecture does not appear on it. | Add a small power tree (PoE → 12 V → 3.3 V; isolated 24 V field supply; isolated 5 V RS-485 supply) as text or graphics in the free space. **Fixed 2026-10-13:** "Power tree" block added below the sheet symbols. It is drawn in native graphics only (no wires or symbols) and shows rail net names, both isolation barriers and the three ground domains. ERC 0 violations. |
| DENS-4 | Open | RS485 | — | Only ~29 parts on A3. The content sits in the middle and the lower left is empty. | No split needed. Mirroring the buck (FLOW-3) is a good moment to tighten it. Changing the sheet to A4 is optional. |

### Font sizes

All sizes below are read from the files. The baseline is 1.27 mm for references, values, labels, sheet pins and notes.

| ID | Status | Sheet | Refs | Finding | Suggested fix |
|---|---|---|---|---|---|
| FONT-1 | Open | all | GND, P3V3, P12V0, GND_FIELD, P24V0_FIELD etc. | **Power symbol text is 0.762 mm**, which is about 60 % of the baseline and about 2 pt when printed on A3. All 154 placed GND and supply symbols use it: MCU 73, Ethernet 35, IO 19, RS485 18, DI 6, DO 3. This is the hardest text to read on every sheet. | Set 1.27 mm in the library symbols, then reset the placed instances with *Edit → Edit Text & Graphic Properties*. Field sizes are stored per instance, so a library update alone does not change them. |
| FONT-2 | Open | all | D7, D8, D9, D13–D16, D22 + the other DI copies | **LED Reference and Color fields are 0.99 mm.** | Use 1.27 mm, as in FONT-1. |
| FONT-3 | Open | MCU, Eth, IO, RS485, DI, DO | U7, U8, U9, U11, U17, U18, U20, J4, J5, J6, J8, Q1, Q3, Q6–Q10, Q12, D27 | **Reference and Value are 1.524 mm on some ICs, FETs and connectors**, while U1, U3, U4, U10, U12, U16 and everything else use 1.27 mm. Neighbouring parts on the same sheet therefore don't match. These parts probably came from libraries with a different default. | Pick one size (1.27 mm) and batch-set it. Fix the library defaults too. |
| FONT-4 | Open | MCU, IO, RS485 | — | **Block titles are inconsistent.** "SWD Debug port", "3.3V Supply", "Voltage supervisor / Reset generation", "Ethernet PHY" and "PoE (Power over Ethernet)" are 2.54 mm inside a dashed box. "RTC & SRAM Backup power (>= 8h)" is a 1.27 mm title. "LPUART1 Debug Port" is 1.27 mm with no box. "RS485 5V Supply" is 2.54 mm with no box and sits *below* its block. On IO, "Isolated 24V, 3W supply" is loose 1.27 mm text on the right of the page, not near the supply. | Use one convention: a 2.54 mm title in the top left corner of a dashed box, one per functional block. Give LPUART debug, RS485 transceiver, RS485 5 V supply, the isolated 24 V supply and the status LEDs their own boxes. |

### Naming and ordering

| ID | Status | Sheet | Refs | Finding | Suggested fix |
|---|---|---|---|---|---|
| NAME-1 | Open | IO, DO, DI | — | **Sub-sheet names are off by one compared with the channel numbers.** "Digital Output" is DO1, but "Digital Output1" is DO2 (K2, DO2_ON). "Digital Input", "Digital Input1" and "Digital Input2" are DI1, DI2 and DI3. The sheet path in the title block (for example `/IO/Digital Output1/`) therefore names the wrong channel. | Rename the sheets `DO1`, `DO2`, `DI1`, `DI2`, `DI3` to match the nets and the J1 pinout. |
| NAME-2 | Open | — | — | **Page numbers interleave the channels:** 6 = DO, 7 = DI, 8 = DO1, 9 = DI1, 10 = DI2. | Renumber so the pages go DO1, DO2, DI1, DI2, DI3, and put RS485 next to IO. |
| VAL-1 | Open | Eth, DO, DI | R11, R28, R30, R52, R53, R57, C50, C89, C90, C91 | **Value formatting is mixed.** Some resistors have no Ω: R52/R53 "10", R57 "1k", R11/R28/R30 "0". Capacitors use "uF" while inductors use "µH". Precision varies: "22uF" (C50) vs "22.0uF" elsewhere, and "1nF" (C89–C91) vs "1.0nF" (C62–C69). | Use one style, e.g. "10Ω", "1kΩ", "0Ω", "22.0µF", "1.0nF". This overlaps with F2-1 in the 2026-10-09 review. |

### Local collisions and clutter

| ID | Status | Sheet | Refs | Finding | Suggested fix |
|---|---|---|---|---|---|
| LOC-1 | Open | MCU | SYS_STS_GREEN, P4_16/P4_17 wires | The SYS_STS_GREEN wire runs through the note "These share the same light pipe". The LED wires run through "TP18/TP70 Switch node measurement". | Move the notes, or replace the wires with labels (DENS-2). |
| LOC-2 | Open | MCU | TP18, L1, DCDC_LX, PWR_FLAG | TP18, the vertical DCDC_LX label, L1 and PWR_FLAG are stacked on top of each other next to U1 pin 53. | Give the VDD_CORE DCDC a little more room, and put the label horizontally. |
| LOC-3 | Open | MCU | TP22, P3V3_FB_1 | The P3V3_FB_1 label overlaps the TP22 reference. | Move one of them. |
| LOC-4 | Open | MCU | TP64, TP65, ETH_RXDV | TP64 and TP65 crowd the ETH_RXDV net name at U1 pins 5–6. TP64 also sits next to the pin 5 no-connect marker. | Move the TPs a grid step to the left, or pull the net name back. |
| LOC-5 | Open | MCU | 3.3 V supply PWR_FLAG ×2 | The "PWR_FLAG" text is far to the left of its symbols, outside the block. | Move the text next to the symbol. |
| LOC-6 | Open | Ethernet | R10, R27, R31, R32, R33, R35–R39, R41 | On the vertical strap and pull resistors, the value is rotated and printed through the resistor body, and R10/R27 text nearly touch. The 33 Ω series resistors (R17–R20, R24–R26) and R42/R43/R44 on MCU also print the value inside the body. Every other resistor puts its fields beside the body. | Put the fields beside the body, as on the other resistors. |
| LOC-7 | Open | Ethernet | R10, R27, R31–R41 | Nothing says what the straps select (PHYAD, RMII mode, CONFIG, ISO), so reading the sheet needs the KSZ8081 datasheet. | Add a short strap table as a note next to U3. |
| LOC-8 | Open | Ethernet | TP6, TP69, TP1, TP10 | The TP6 reference overlaps the POE_VDD label. The "TP Placement" note is in the lower middle of the PoE box, far from TP1, TP4 and TP10. The dashed lines joining the TP pairs cross wires. | Move TP6 clear of POE_VDD, and put the placement notes next to the TPs they describe. |
| LOC-9 | Open | Ethernet | — | The "Place TP63 on signal without stub…" note is squeezed between the RXD1 and RXDV rows and runs right up to TP63. | Move it into free space, e.g. below the TXEN row, close to TP63/TP66. |
| LOC-10 | Open | IO | — | Spec notes ("Output 1 - 2: ≤ 30 V DC…", "Input 1 - 3: IEC 61131-2…", "Isolated 24V, 3W supply") float loosely to the right, beside the "Isolation:" text box. | Put each note next to its block (DO sheets, DI sheets, supply), or merge them all into the box. |
| LOC-11 | Open | RS485 | R81, C78, P5V_RS485_FB | R81's "1%" field and C78's (DNP) "C0G" field sit on the P5V_RS485_FB wire. | Move the fields, or route the FB wire one grid step lower. |
| LOC-12 | Open | DO (×2) | K1/K2, R52/R53, F1/F2 | The notes "1.5-2.1 A peak @ 24V short", "< 20ms TtT @ 2A" and "PhotoMos: 3A, < 100ms req" are crowded between K1, R52 and F1, so it is unclear which part each one describes. | Put each note directly under the part it describes (R52, F1, K1). |
| LOC-13 | Open | Top level | BOM Entry ×16 | The BOM-only symbols in the lower left have no heading. | Add a "Mechanical / BOM-only items" heading, ideally inside a box. |
