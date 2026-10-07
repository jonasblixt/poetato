# PoEtato schematic review

This is a living document that lists **every finding raised in this review**, each with a status. Rows are updated in place when the schematic or the docs change. Fixed findings stay in the tables, so the history of what was found is visible.

| | |
|---|---|
| Review started | 2026-10-04 |
| Revision checked | Working copy saved 2026-10-07 21:10. **Not in git**: `hw/` is untracked; HEAD is `3f27572`. Rails renamed during the review: P12V → P12V0, P24V_FIELD → P24V0_FIELD (converter side) and P24V0_FIELD_PROT (terminal side of F3); older finding text keeps the old names. |
| Tools | KiCad 10.0.6 `kicad-cli` (netlist, ERC, PDF in `hw/poetato/.review/`) |
| Sheets | root `poetato`, `ethernet_poe`, `mcu`, `io` (= /IO/) with sub-sheets `rs485` (/IO/RS485/), `di` ×3 and `do` ×2. `power.kicad_sch` is empty and not instantiated. |
| ERC | 0 errors, 4 warnings: `COOL_POUR` single-pin label on ISO1211 SUB (expected, ISO121x p.3), `multiple_net_names` ×3 in /IO/RS485/ (H2-2). |
| Not checked | Si3402 FB pin in isolated mode (figure not readable as text). Lifecycle on manufacturer pages. DC-bias derating is estimated, not read from Murata curves. The Littelfuse SMAJ table does not extract cleanly as text; SMAJ V_BR/V_C values come from the Value field and the matching rows of the SMF datasheet, which uses the same breakdown/clamp ratings per voltage. |

**Severities:**
- **Error**: will not work or can damage.
- **Warning**: risk, margin or testability gap.
- **Note**: housekeeping.
- **Question**: intent unclear.

**Status:**
- **Open**: not addressed.
- **Partly fixed**: some of it is done; the status cell says what remains.
- **Fixed**: verified fixed in the schematic.
- **Resolved (decision)**: the schematic stays as it is by design decision, and the docs record it.
- **Not an issue**: withdrawn after Jonas's input.
- **Info**: verified, nothing to do.

Open and partly fixed items are listed first in each table.

## Findings

### Errors

| ID | Status | Sheet | Refs | Finding | Evidence | Suggested fix / resolution |
|---|---|---|---|---|---|---|
| M4-1 | **Open** | MCU | U1 pins 40–42 | USB1 HS is not connected (sheet note "TODO: Add HS USB"). It is the only ROM ISP interface (arch §4), so the only ROM recovery path apart from SWD. | Netlist | Add connector, ESD, VBUS directly to pin 42, D+/D− to pins 40/41. |
| E1-3 | Fixed | IO | U19 | TPS26625 OVP (pin 3) is left unconnected with a no-connect flag. The datasheet says to tie OVP to RTN when unused, and arch §3 states "OVP: tied to RTN". A floating OVP input can sit anywhere and randomly cut off the field terminal. | TPS2662 p.4 (Table 6-1, pin 3); arch §3 table | OVP now on the RTN net with R85/R95/C52 (net `Net-(U19-OVP)`, H2-style auto name only). |
| C1-1 | Fixed | IO | T1, U15, C28, C29 | Primary centre tap T1-2 was not connected to P12V, so there was no field rail. | Netlist | T1-2 now on P12V with C28/C29. |
| C1-2 | Fixed | IO | T1, D22–D25 | The bridge rectified the whole 1:2.29 secondary (≈ 53 V instead of ≈ 24 V). | Würth 750319693 p.1–2 | Centre-tap full-wave: T1-5 → GND_FIELD, D22/D24/L7 removed. ≈ 23–26 V. |
| V1-1 | Fixed | MCU | U18, R63, R89 | TPS563252 divider 7.5 k / 10 k gave 1.05 V instead of 3.3 V (V_REF 0.6 V). | SLUSEQ5A p.5, p.17 | R63 133 k / R89 29.4 k → **3.32 V** (3.21–3.42 V). |
| X4-1 | Fixed | MCU | U10 | SE051 SDA/SCL were swapped (pin 9 = SDA on SE_SCL). | SE051 DS p.12 Table 3 | Swapped. |
| R3-1 | Fixed | DO | R62, R96 (old R63) | AQY212GS LED current was 1.3–1.7 mA with 1.3 kΩ (I_Fon max 3 mA). | ASCTB133E p.3–4 | 220 Ω: 7.8–10.5 mA (but see R3-2). |
| W2-1 | Fixed | MCU | U2 | LP3470A308 V_IT+ 3.28 V typ (≤ 3.35 V) on a 3.21–3.42 V rail; reset might never release. | SNVSBF5C p.3, p.6 | LP3470A293: V_IT− 2.89–2.97 V, V_IT+ ≤ 3.10 V. The PHY brown-out window remains (DOC-1). |
| E-NEW-1 | Fixed | Eth | U3 | After a symbol edit, KSZ8081 VDDA_3.3 (pin 3) and VDDIO (pin 17) were disconnected. | ERC/netlist | Reconnected. |
| M4-2 | Not an issue | MCU / IO | U1 P1_8/P1_9, J4 | The ROM UART ISP pins drive the RS-485 transceiver, and J4 is not on ISP pins. | RM Table 227 | Decision 2026-10-04: no UART ISP. USB1 HS is the only ROM ISP interface, plus SWD (arch §4). |

### Warnings

| ID | Status | Sheet | Refs | Finding | Evidence | Suggested fix / resolution |
|---|---|---|---|---|---|---|
| K1-1 | **Open** | MCU | Y3, C1, C2 | NX3225SA STD-CSR-1 is specified at C_L = 8 pF, ±15 ppm + ±15 ppm. C1/C2 = 4.7 pF give C_L ≈ 5.4–7.4 pF, so pulling is ≈ +33 … +190 ppm. That exceeds the KSZ8081's ±50 ppm for the 50 MHz reference derived from this crystal. | NDK STD-CSR-1; MCX DS Table 35 p.47; DS00002202D Table 7-12 p.57 | C1/C2 ≈ 10 pF. |
| K1-3 | **Open** | MCU | Y1 | NX3215SA STD-MUA-8 is the **12.5 pF** load-capacitance version. The internal caps would need ≈ 21 pF per pin, so Cx ≈ 42 pF + pads, against the MCX N limit of ≤ 22 pF. The docs ask for C_L ≤ 7 pF. | NDK NX3215SA sheet; MCX DS p.49 Table 37 | NX3215SA-32.768K-STD-MUA-14 (6 pF), with internal load caps set in firmware. |
| K1-4 | **Open** | MCU | Y3 | NX3225SA STD-CSR-1 operating range is only −10 … +75 °C. The board must cold-start in a winter garage (poe-verification tests −25/−30 °C). | NDK STD-CSR-1, items 6/7 | 24 MHz crystal rated −40 … +85 °C or wider, C_L 8 pF. |
| R2-1 | **Partly fixed** | IO | U17, R8 | The unregulated field rail against TPS54202H V_IN 28 V recommended / 30 V abs max, with no base load. | SLVSDG7A p.4–5 | R8 10 k preload added. Remaining: bench-measure at minimum load and 57 V PoE. R8 is now 1206 (27–36 % of its 0.25 W rating). |
| C3-2 | Fixed | IO | U19 R95, U15 R72 | The eFuse limit sits too close to the SN6507 limit. R95 66.5 k gives I_OL = 6.636/66.5 = 100 mA (≈ 90–110 mA). R72 75 k gives the SN6507 ≈ 0.32 A typical and ≈ 0.23 A minimum primary current, interpolated: I·R ≈ 23.7 k·A typical and 15.7–18.2 min across the table. That is ≈ 0.14 A typical and ≈ 0.10 A minimum on the secondary (÷ 2.29). With the ≈ 10 mA for RS-485, preload and UVLO divider on top, a terminal short or the 1000 µF ramp can push the converter into its limit first. Then `P24V0_FIELD` sags and RS-485 can drop, the case arch §3 says the eFuse prevents. The "3 W (125 mA)" in arch §3 is the transformer rating, not the binding limit. | TPS2662 p.7, p.20 (Eq. 3); SN6507 p.5; arch §3 | Final values (sheet saved 21:10): R95 100 k → I_OL = 66 mA (≈ 60–73 mA; the datasheet gives ±5 % at 44.2 k and −20/+28 % at 267 k, so this is interpolated), and R72 back to 75 k. Worst case: eFuse ≈ 73 mA plus ≈ 10–15 mA RS-485/preload/UVLO ≈ 88 mA, against the converter's ≈ 92–106 mA minimum on the secondary (≈ 0.14 A typical). That keeps a margin at the corner and a large one typically, and the SN6507 maximum (≈ 0.39–0.49 A primary) stays inside the 0.5 A switch rating. Bench check stays in arch §15 (terminal short, 1000 µF start-up, cold/hot). Short-circuit heating: 24 V × 66 mA ≈ 1.6 W × 44.8 K/W (p.6) ≈ +72 K, so Tj ≈ 127 °C at 55 °C ambient, below TSD. The part cycles on the ≈ 2.2 s timer and 512 ms retry instead. Arch §3 still says 66.5 k / 100 mA (DOC-1). |
| E1-4 | Fixed | IO | U19, P24V0_FIELD_PROT | No output capacitor on `P24V0_FIELD_PROT` (only D24 and J1-1), while arch §3 lists C_OUT 1 µF 100 V. C_IN at the pin is C79 100 nF, not 1 µF as the table says. | Netlist; TPS2662 p.6 (test conditions C(OUT) = 1 µF); arch §3 | C58 1 µF 100 V X7R 1206 (GRM31CR72A105KA01) on `P24V0_FIELD_PROT`; C53 (same part) added on `P24V0_FIELD` as C_IN, matching arch §3. |
| T2-1 | Fixed | all | — | Signal TPs were missing. | Netlist | TPs added on SE I²C, DO1/2_ON, DI1–3, DI_EN and RS-485 RXD/TXD/DE/RE_N. Then TP50–TP61: P24V_FIELD_EN, ETH_RST_N, ETH_MDC/MDIO, QSPI D0–D3/CS_N/SCK and two GND. TP62 on ETH_IRQ_N. All T2 signals covered. |
| E1-1 | Fixed | IO | U19, D24, J1-1, P24V0_FIELD_PROT | Field rail on the terminal with no PTC/fuse (decided: ~150 mA PTC) and no TVS. | arch §3, §10; netlist; SN6507 p.5, p.17; Bel 0ZCJ table p.1 | F4 (no PPTC could trip below the ≈ 0.14 A converter limit) replaced by U19 TPS26625DRCR eFuse, auto-retry (decision 2026-10-07, arch §3), with D24 SMAJ28CA on J1-1. Wiring checked against `power/field/TPS2662x_TI.pdf`: IN = P24V0_FIELD, OUT = P24V0_FIELD_PROT, GND = GND_FIELD, RTN and PowerPAD (pins 5, 11) on their own net with R95/R85/C52 (p.24). UVLO 1.2 × 214/14 = 18.3 V rising, 16.8 V falling (p.6). SHDN open is fine: internal pull-up, 2.8 V open-circuit (p.6). FLT unused (decided). Follow-ups: E1-3, E1-4, C3-2. |
| E1-2 | Fixed | DO | D18, D19 | SMAJ28CA standoff 28 V is below the 30 V AC/DC output rating. | Littelfuse SMAJ; Value field | Now SMAJ33CA: 33 V standoff, 53.3 V max clamp, below the AQY212GS 60 V load rating. Arch §7 still says SMAJ28CA (DOC-1). |
| Q2-4 | Resolved (decision) | IO, Eth | J6 | No 12 V bench header with series Schottky. | arch §3 (old) | J6 (Würth 61300211121, 2.54 mm 2-pin) added directly on `P12V0`, pin 1 GND / pin 2 +12 V. Decision 2026-10-06: no series diode. D4 blocks backfeed into T2, and powering the TLVH431/opto feedback from the bench supply is harmless. Recorded in arch §3. Residual risk: no reverse-polarity protection on an unkeyed header (bench discipline, current-limited supply). |
| D1-1 | Fixed | — | — | Required datasheets were missing in `datasheets/`. | Inventory | Covered since: IHLP "-1Z" inductors (`magnetics/IHLP-1212-EZ-1Z_Vishay.pdf`); Würth 150040VS73240 (`discretes/150040VS73240_Wurth.pdf`: WL-SMCC 0402 bright green, V_F ≈ 2.0 V typ at 20 mA, I_F 30 mA max, −40…+85 °C, cathode marked; at 464 Ω from 3V3 the LEDs run at ≈ 3 mA); Phoenix plugs 1757116 / 1757035 (`connectors/1757116-` and `1757035-MSTB-plug_drawing_Phoenix.pdf`, image-only drawings, identified by order number). Last ones added: 150040SS73240 (D15, super red 630 nm) and 150040AS73240 (D16, amber 605 nm), V_F ≈ 2 V, `discretes/`; Würth 60900213421 WR-PHD 2.54 mm jumper with test point for J5 (`connectors/60900213421-jumper_Wurth.pdf`). All required parts now have a datasheet. |
| E2-1 | Fixed | IO | J1, J2, M15, M16 | J1/J2 were Phoenix MSTBA 2,5 (5.08 mm) headers while the docs said "3.5 mm, MC 1,5"; the mating plugs were not in the BOM. | Phoenix 1757349 / 1757268 p.1; distributor listings for 1757116 / 1757035 | Pitch decided as 5.08 mm, docs updated. Plugs now BOM-only items: M15 1757116 (MSTB 2,5/12-ST-5,08) and M16 1757035 (MSTB 2,5/4-ST-5,08). Enclosure fit is mechanical, outside this review. |
| I2-3 | Fixed | Eth, IO | C89 (SHIELD↔GND), C90 (12 V↔VPOS), C91 (GND↔VNEG), C92 (GND↔GND_FIELD) | The GA3 Y2 caps were replaced by KEMET C1808C102KHRACTU (1 nF, 3 kV DC, X7R, 1808, not safety-certified); datasheet and AC suitability unverified. | `passives/C1808C102KHRACTU_X7R-HV-SMD_KEMET.pdf` p.1, p.12, p.23 | Datasheet covers it (ordering code C·1808·C·102·K·**H = 3,000 V**·R = X7R). DWV for 1808 at ≥ 1 kV: 120 % of rated (3.6 kV DC, 5 s; p.12). The 1500 Vrms hipot is 2.12 kV peak, well inside. KEMET notes X7R is "not recommended for AC line filtering or pulse applications" (p.2). That does not apply to a one-off 60 s hipot or to common-mode bypass on SELV. Conformal coating is recommended for MLCCs ≥ 1500 V to prevent surface arcing (p.23), and is already planned (arch §11). The first board hipot still serves as the AC check (poe-verification §0). |
| I2-2 | Resolved (decision) | Eth | C52, C53 (barrier 1) | poe-verification §0 planned a 2250 V DC hipot for 60 s across barrier 1, above the Y-caps' DC 2150 V voltage-proof test (AC 2000 Vrms). | GA3 DS p.3 items 3–4 | Decision 2026-10-05: barrier 1 requirement is **1500 Vrms AC, 60 s** (802.3), verified by AC hipot (≈ 0.9 mA Y-cap leakage, trip ≈ 3 mA). Recorded in arch §11 *Isolation requirements* and poe-verification §0. |
| I2-1 | Fixed | Eth, IO | C52, C53, C58, C70 | Y-rating of GA352QR7GF102KW01 was not verified (no datasheet). | `passives/GA352QR7GF102KW01_Murata.pdf` p.1–3 | Verified Y2 (IEC 60384-14), voltage proof AC 2000 Vrms / DC 2150 V. The parts have since been replaced by KEMET 3 kV MLCCs: I2-3. |
| G3-1 | Resolved (decision) | all | TP1–TP49 | All TPs are BOM-excluded PCB pads; G3 asks for probe-able loop/through-hole parts for ground TPs and Bode injection points. | Schematic `in_bom no` | Decision 2026-10-05 (Jonas): TPs stay BOM-excluded pads; loop test points are hand-soldered onto them where needed. |
| L1-2 | Fixed | MCU, Eth | L1, L2 | IHLP-1212AE-11 (IHLP1212AEER1R0M11) is "Not for New Designs"; alternative IHLP1212-EZ-1Z. | Vishay IHLP-1212AE-11 DS p.1 | L1/L2 now IHLP1212AEEZ1R0M1Z (L4/L5 likewise moved to the BZ "EZ…1Z" parts). Confirmed in `magnetics/IHLP-1212-EZ-1Z_Vishay.pdf` (not NRND): IHLP1212AEEZ1R0M1Z 1.0 µH, DCR 26.6 mΩ typ; IHLP1212BZEZ2R2M1Z 2.2 µH, 36/40.5 mΩ, heat 5.7 A, sat ≥ 5.3 A; IHLP1212BZEZ3R3M1Z 3.3 µH, 50.4/54.9 mΩ, heat 4.5 A, sat ≥ 3.7 A (p.1–2). All are far above the load currents (≤ ~0.4 A). |
| F1-1 | Not an issue | all | TP1–TP49 | All 48 TPs have no `Part Number` / `Manufacturer` fields. | Schematic files: `in_bom no` on every TP | The TPs are excluded from the BOM (PCB pads), so F1 does not apply. |
| R3-2 | Fixed | DO, DI, IO, MCU | Q1, Q12 (PhotoMOS LEDs); Q3, Q11, Q13, Q6, Q9, Q10 (status LEDs) | 2N7002 driven directly from 3.3 V GPIOs: V_GS(th) up to 2.5 V, R_DS(on) specified only at V_GS = 5 V / 10 V, so the PhotoMOS LED current was not guaranteed. | onsemi 2N7002 DS p.2–3; NTK3134N DS p.1–2 | All eight replaced by NTK3134NT1G: V_GS(th) 0.45–1.2 V, R_DS(on) 0.26 Ω typ at 2.5 V, V_DSS 20 V, V_GS ±8 V. SOT-723 pins 1 G / 2 S / 3 D match the wiring. Drop at 10 mA is a few mV. |
| P1-1 | Fixed | Eth | C40, C41 | KSZ8081 VDD_1.2 had 1 µF + 10 µF; the datasheet asks for 2.2 µF + 0.1 µF. | DS00002202D p.10, p.31 | C41 2.2 µF 0603 X7R, C40 100 nF 0402 X7R. |
| R2-2 | Fixed | Eth | D1, D2, U4 | SWO clamp was SMAJ33A (V_BR 36.7–40.6 V, V_C ≈ 53.3 V): SWO peak ≈ 95–111 V against the Si3402-B 100 V abs max. The EVB uses DFLT30A. | Si3402-B p.4; EVB BOM p.8 | DFLT30A-7 as on the EVB: V_RWM 30 V, V_BR 33.3 V min, V_C 48.4 V at 5.15 A (`protection/DFLT_Diodes.pdf` p.2). SWO peak ≈ 57 + 33…48 + 0.7 ≈ 91–106 V; at realistic leakage-spike currents the clamp sits near V_BR (≈ 91–96 V). Confirm on the bench per poe-verification §4. |
| Q2-2 | Fixed | IO | C70, T1 | No Y-cap GND↔GND_FIELD for the SN6507 push-pull common-mode current. | arch §11 *Isolation practice* | C70 1 nF (GA352QR7GF102KW01) now GND↔GND_FIELD. Its Y-rating: I2-1. |
| E3-1 | Fixed | IO, Eth | C70, R51, C58, R15, J2-4, T3 | The RS-485 shield returned to logic GND via C70/R51, so shield current crossed the logic ground plane. | arch §11 | SHIELD net = T3 S1/S2 + J2-4; SHIELD↔GND via C58 1 nF ∥ R15 12 MΩ; R51 removed. |
| Q2-3 | **Closed** | Eth | — | No PTC/fuse in the PD path and no ~90 V GDT. | context; arch §11 | Requirement dropped 2026-10-05 (judged unnecessary); removed from arch §11 and context doc. |
| C3-1 | Fixed | IO | R72 | SN6507 I_LIM 1.0–1.59 A (18 k), against 0.5 A switches; a field short could exceed Class 2. | SN6507 p.1, p.5 | 75 k → ≈ 0.33 A; later 62 k → ≈ 0.38 A typical for eFuse margin (C3-2). |
| V4-1 | Fixed | Eth | R6 | 24.3 k detection resistor was 0402 on 57 V (EVB uses 0805). | EVB BOM p.8 | 0805. |
| K1-2 | Fixed | MCU | C3, C4 | External 12 pF 32 kHz load caps on top of the internal ones (checklist: omit). | Checklist 3.2; DS p.49 | DNP. Crystal C_L itself: K1-3. |
| K2-1 | Resolved (decision) | Eth / MCU | U3, U1 P1_4 | KSZ8081RNB powers up in 25 MHz mode; the schematic feeds 50 MHz into XI. | DS00002202D p.20, p.44, p.66 | Firmware sets Reg 1Fh.7 after every PHY reset; sequence documented in arch §4. |
| X3-1 | Fixed | MCU | U10 | SE051 LA/LB and RST_N were left open (datasheet: tie). | SE051 DS p.12–13 | Tied to GND. |
| X3-2 | Fixed | DI | C86–C88 | ISO1211 C_IN ≥ 1 nF missing; no debounce. | ISO121x p.24 | 10 nF C0G added; debounce in firmware, documented in arch §6. |
| B1-1 | Fixed | Eth | R16 | Flyback injection point was 0 Ω. | Netlist | 10 Ω 0805. |
| B1-2 | Fixed | MCU | R88 | No TPs around the TPS563252 injection resistor. | Netlist | TP22, TP23/24, GND TPs. |
| B1-3 | Fixed | IO | R80 | No TPs around the TPS54202H injection resistor, and no GND_FIELD TP. | Netlist | TP28, TP29/31. TP27/32 moved to GND_FIELD. |
| T1-1 | Fixed | all | — | Rails without a TP: P3V3, P24V_FIELD, P5V_RS485, ETH_VDD_1.2, P3V3_ETH_VDDA, supercap node, SN6507 CT. | Netlist | TPs added. |
| G1-1 | Fixed | IO, MCU | — | Field domain had no ground TP; logic was short of the rule. | Netlist | TP27/32 GND_FIELD, TP37 GND. Remaining counts: G2-1. |
| G1-2 | Fixed | IO | TP27, TP32 | New ground TPs were on logic GND, not GND_FIELD. | Netlist | Moved to GND_FIELD. |
| P2-1 | Fixed | MCU | C83 | TPS563252 input cap 10 µF 0603 was effectively < 10 µF. | SLUSEQ5A p.17 | 22 µF 1210 X7R 25 V. |
| H1-1 | Fixed | all | — | ERC had 55 errors (unconnected pins, pin types, missing PWR_FLAGs). | ERC JSON | 0 errors; PWR_FLAGs only on driven rails. |
| Q2-1 | Resolved (decision) | DO | Q1, Q2 | No DO_EN rail gate or boot check; one 2N7002 per channel. | context; arch §8 (old) | Deliberate (2026-10-04). Arch §7–8, context doc and diagrams now describe the schematic. Residual (stuck GPIO / shorted FET = stuck button) is accepted. |

### Notes

| ID | Status | Refs | Finding |
|---|---|---|---|
| C2-1 | **Partly fixed** | C34, C72, C80, C53 | SN6507 recommends C_OUT < 10 × C_SS = 22 µF (C34 2.2 µF; p.19, p.24). On `P24V0_FIELD` today: C72 22 µF + C80 10 µF (≈ 3–4 µF at 26 V) + C53 1 µF + C79 0.1 µF ≈ 27 µF effective, 33 µF nominal. C58 sits behind the eFuse and charges later, so it does not count. Simplest fix: C34 → 4.7 µF (in the 0.05–5 µF range), which allows 47 µF. Soft-start goes from ≈ 8 ms to ≈ 18 ms, by T_SS ≈ C_SS·1 V/(275 µA − 0.6 V/R_ILIM), consistent with the p.22 example (0.5 µF, 50 k → 2 ms). Otherwise, confirm a clean start-up on the bench. |
| T3-3 | **Open** | TP63 (`Net-(U3-TXD0)`), TP64 (ETH_RXD0) | New TPs on RMII TXD0 and RXD0, which T3 lists as no-TP signals. Both sit at the receiving end, after the series resistors R19/R18, which is the least harmful place and the useful one for measuring. Fine if the pad sits directly on the trace with no stub. TP63's net has an auto name: label it `ETH_TXD0_PHY` or similar (T4). |
| X3-3 | **Open** | R35, R23 | CONFIG0 pull-up R35 is 1 k; 4.7 k recommended (DS00002202D p.13). MDC pull-up R23 is unnecessary. |
| P1-2 | **Open** | C42–C44 | KSZ8081 VDDIO has ~12 µF locally; 22 µF + 0.1 µF recommended (p.31). |
| G2-1 | **Open** | — | Ground TPs: logic 7, ok. Field 2 (TP27, 32) of 3. PSE 2 (TP4, 6) of 3. |
| S2-1 | **Partly fixed** | U2 | Pin types were corrected on U1, U3, U10, U12–U14 and U15. Remaining: LP3470 pins all "input". |
| S1-1 | **Open** | U6, D17, U4 | TLVH431 pins 1/2 are hidden. BAS70-04 symbol lacks pin 2 (wiring correct, diode 2 unused). Si3402 pin 5 is named NC but is PLOSS. |
| F2-1 | **Open** | U12–14, U15, Y3, D12/20/21, D17, J4/J5, Q7/Q8, F1/F2 | PN `ISO1211` is not orderable. U15 PN has trailing spaces. Y3 "…24.000MHZ…" vs NDK "…24.000M…". "Littlefuse". "Wurth" vs "Wurth Elektronik"; "Phoenix" (M15, M16) vs "Phoenix Contact" (J1, J2). FDV304P "Fairchild" (onsemi). The D17 datasheet is Nexperia's, but the part is Vishay. F1/F2 Value shows the trip current. SMAJ values show V_BR. |
| H2-1 | **Partly fixed** | — | Duplicate net names (ETH_/ENET_, D01_ON, FLD_24V) fixed. The IO sheet now lives in `io.kicad_sch`, with RS-485 as its sub-sheet `rs485.kicad_sch` (/IO/RS485/). Remaining: orphan `power.kicad_sch`, and a library nicknamed `power` holds non-power parts (TLVH431, LP3470A293, TP). |
| T4-1 | **Open** | 13 TPs | Auto-named TP nets: TP5, TP8, TP9, TP10, TP11, TP13, TP16, TP17, TP18, TP22, TP28, TP30, TP36. TP33 is now on the named rail `P24V0_FIELD`. The protected terminal net `P24V0_FIELD_PROT` has no TP (J1-1 can serve). |
| T3-1 | **Open** | TP18, TP30 | Switch-node TPs are not marked as deliberate (TP1 SWO is deliberate per poe-verification). |
| H3-1 | **Open** | C3, C4, R11, R16, R28, R30, J5 | DNP / 0 Ω options and the termination jumper have no note saying what they select or their default. |
| H4-1 | **Open** | IO sheet | Sheet notes contradict the docs: "60V AC/DC, 1A" (rating ≤ 30 V / 100 mA), "Isolated 24V, 1.5W" (docs 3 W). |
| R1-1 | **Open** | C47–C51 | 100 V MLCCs on 57 V = 1.75× (rule 2×); same as EVB. Accept or upsize. |
| L1-1 | **Open** | — | Lifecycle not checked online (apart from L1-2). |
| DOC-1 | **Partly fixed** | docs | **Done:**<br>• Arch: USB-only ISP; KSZ8081 50 MHz firmware step; digital inputs (ISO1211); output drive and fault architecture; budget margin; "eight inputs".<br>• Context doc: digital inputs and output drive.<br>• NTK3134N output/status-LED FETs and the LP3470A293 supervisor, including the PHY brown-out window (arch §7–8, key parts, context, diagrams).<br>• Barrier caps: arch §11, context and poe-verification §0 now say KEMET 1 nF / 3 kV DC (C89–C92), "≥ 3 kV DC, verified by the 1500 Vrms hipot", with Y2 not required.<br><br>**Remaining:**<br>• Context doc "Keep a UART ISP header too".<br>• `doc/img/floorplan.svg` / `doc/mech/outline.py` show ISO1228 and DO_EN blocks.<br>• Supercap/VDD_BAT, bench header and GDT are only in arch.<br>• SE050 vs SE051.<br>• SE RST_N control (not possible in I²C mode, SE051 p.10).<br>• security-requirements §6 N947 hedge.<br>• poe-verification stale items: R5 75 Ω, TLVH431, 470 µF EMZL, SMAJ33A, FA2672 datasheet, R16 10 Ω.<br>• Open: arch §7 still names SMAJ28CA for D18/D19, now SMAJ33CA (E1-2).<br>• Open: arch §3 (table, current-limit and ramp text), §1 tree, key parts and decision log still say R_ILIM 66.5 k / 100 mA, 80 mA terminal rating and "≈ 90 mA minimum limit"; now 100 k / 66 mA (≈ 60–73 mA). The 1000 µF ramp (49 mA typical, ≈ 78 mA worst) can now touch the limit and finish in current limit: ≈ 0.4 s at 60 mA, well inside the ≈ 2.2 s timer. |
| D2-2 | **Open** | `datasheets/discretes/` | `2N7002_NDS7002A_onsemi.pdf` is no longer used by any placed part (all 2N7002 replaced by NTK3134N). Remove it, or keep it as reference for why the FET was changed (arch §7 cites it). |
| H2-2 | **Open** | /IO/RS485/ #PWR0117, #PWR0127, #PWR01 | ERC `multiple_net_names` ×3: in the RS-485 sub-sheet, the GND_FIELD and SHIELD power symbols sit on the same nets as the hierarchical labels `RS485_SIGNAL_GND` / `RS485_SHIELD`. The netlist keeps GND_FIELD / SHIELD. Use either the power symbols or the hierarchical labels in the sub-sheet, not both. |
| H2-3 | **Open** | rs485.kicad_sch, io.kicad_sch | Hierarchical label `RS485_DE_N` drives ISO3082 DE, which is active-high (ISO3082 p.19). The name suggests active-low. The IO sheet labels `DO1_EN`/`DO2_EN` are carried on nets named `DO1_ON`/`DO2_ON`. Harmless (the top-level names win) but confusing. |
| D2-3 | **Open** | `datasheets/discretes/`, `datasheets/passives/` | No longer used by any part: `magnetics/IHLP-1212AE-11_Vishay.pdf` (L1/L2 now the -1Z series), `SML-P11_Rohm.pdf` and `SML-P12_Rohm.pdf` (all LEDs are now Würth), and `GA352QR7GF102KW01_Murata.pdf` (replaced by KEMET, I2-3). Remove, or keep the GA3 as reference. |
| REPO-1 | **Open** | — | Commit `hw/`; add `hw/poetato/.review/` to `.gitignore`. |
| S1-3 | Fixed | D26 → D22 | ERC `lib_symbol_issues` on D26: the only LED left on the Rohm SML-P11MTT86 symbol. | ERC | 0 errors, 4 warnings: `COOL_POUR` single-pin label on ISO1211 SUB (expected, ISO121x p.3), `multiple_net_names` ×3 in /IO/RS485/ (H2-2). |
| S3-1 | Fixed | — | `power:GND` graphic renamed to supply rails (28 symbols). | Inventory | All supply rails use supply symbols. GND_FIELD and SHIELD on the ground graphic are fine (ground nets); a chassis-style symbol for SHIELD would read more clearly. |
| D2-1 | Fixed | `datasheets/` | 10 files were not used by any placed part: 6 obsolete (TPS3436, Si3402-C, FA2805 EP13, USBLC6-4SC6 non-Y, CamdenBoss CNMB/6 drawing, SE050) and 4 duplicates (two older AQY21GS catalogues, two PNG renders of UG10092 p.14). | Removed by Jonas. All remaining files are renamed `<part or series>_<manufacturer>.pdf`; the rest is reference material (app notes, EVB guide, MCX N RM/UG/xlsx, EVK schematic, enclosure, light pipe, XY-MD02 manual). |
| S1-2 | Info | D7–D11, D13–D16 (Würth); D26 (Rohm) | LED symbols: the Würth 150040xS73240 symbols use pin 1 = cathode, the Rohm SML-P11 symbol (D26) uses pin 1 = anode (from the symbol graphics). All are wired correctly; footprints must map pads to match. |
| C2-2 | Info | U15, T1 | CLK is tied to GND, so the SN6507 runs at its default 1 MHz (780–1296 kHz, p.5). Würth's typical application for 750319693 is 400–600 kHz. Volt-seconds are fine: 12 V × 0.64 µs ≈ 7.7 V·µs worst case against 18 V·µs (Würth p.1). Inductance and leakage are specified at 1 MHz. Core and AC copper loss at 1 MHz are not specified, so check T1 temperature at full field load on the bench. Arch §11 already assumes the 1 MHz edges. |
| C2-3 | Info | L5, D23, D25 | The rectifier output (`Net-(D23-K)`) has no capacitor: L5 is a choke-input filter. SN6507 p.24 puts the 1–10 µF bulk capacitor at the rectifier output and uses an inductor only with duty-cycle control (DC pin unused here). It works: during the 70 ns break-before-make, L5 sees −V_out (ΔI ≈ 26 V × 70 ns / 3.3 µH ≈ 0.55 A), so it runs discontinuous at every realistic load and V_out sits near the rectified peak, as assumed in R2-1. It also means each cycle ends with L5 ringing against the diode capacitance. R75/C36 and R76/C71 damp the anodes. A 100 nF–1 µF 100 V ceramic at `Net-(D23-K)` would give L5 a defined input and turn it into a CLC filter. Optional. |
| D-PNE | Info | D23, D25 | PNE20020ER is 200 V / 2 A hyperfast, not the Schottky SN6507 recommends (p.23). That costs ~0.2–0.3 V and ~0.1 W. Accepted by Jonas. |
| C84 | Fixed | C84 | The TPS563252 feed-forward cap was DNP; it is now 33 pF fitted (SLUSEQ5A Table 8-2). |
| T3-2 | Merged | TP30 | Switch-node TP on U17 SW; tracked in T3-1. |
| T4-2 | Merged | TP22, TP28 | Auto-named injection TP nets; tracked in T4-1. |

### Questions

| ID | Status | Question / answer |
|---|---|---|
| Q-10 | **Open** | There are 8 light pipes (M1–M8, Bivar PLP2-750) for 10 LEDs (D7–D11, D13–D16, D22). Which two LEDs stay inside the box (e.g. the RS-485 activity LEDs D13/D16)? Record it on the sheet. |
| Q-5 | **Open** | EVB 12 V configuration R1 = 1.3 k (EVB Table 2 p.9) has no schematic equivalent; what is it? FA2672 symbol has no pins 1/4: NC on the part? FB tied to VPOS: confirm against Si3402-B Fig. 2. |
| Q-3 | Resolved (decision) | Field supply switched by firmware (P3_16 → SN6507 EN, 2.2 k pull-down, off in reset): intentional (decided 2026-10-06). Recorded in arch §3 *Field supply enable* and the context doc. |
| Q-8 | Resolved (decision) | QSPI U11 (S25FL064L): fitted as standard, holds the filesystem (configuration, logs, data), never code (decided 2026-10-06). Arch §4 / key parts / §15, context and security-requirements updated. |
| Q-9 | Resolved (decision) | Terminal pitch: 5.08 mm MSTBA 2,5, as in the schematic (decided 2026-10-06). Arch §10 and the context doc updated. |
| Q-6 | Resolved | RS-485 shield return: to a common SHIELD net with the Ethernet shield, bonded at the box end only, not via logic GND. Decision recorded in arch §11 (*Shields and the SHIELD net*), including UTP behaviour and an optional functional earth. Schematic change tracked in E3-1. |
| Q-1 | Resolved (decision) | 3 × ISO1211 instead of ISO1228: deliberate. Docs updated to the schematic (arch §6, context, diagrams). |
| Q-2 | Resolved (decision) | Per-channel 2N7002 output drive: deliberate. See Q2-1. |
| Q-4 | Resolved | KSZ8081 straps and clock mode checked against DS00002202D; the clock mode became K2-1. |
| Q-7 | Resolved | LED orientation: correct, see S1-2. |

## Checks performed

Last run against the revision in the header. "Pass" means verified against the cited source; findings are listed above.

- **F** Fields: F1 pass (TPs are excluded from the BOM; all other symbols have PN and manufacturer). F2 open (F2-1).
- **D** Datasheets:
  - D1 pass: every required part has its datasheet in `datasheets/` (D1-1 fixed).
  - D2: one unused file, the 2N7002 datasheet (D2-2); files follow `<part>_<manufacturer>.pdf` (D2-1).
- **S** Symbols:
  - S1 pass for MCXN247 (pinout xlsx), Si3402-B, SE051, ISO1211, ISO3082, SN6507, TPS563252, TPS54202H, TLVH431, LP3470A, USBLC6-4SC6Y, KSZ8081RNB, S25FL064L SOIC8 (ordering code ✓), VO618A, PNE20020ER, FDV304P, BAS70-04 (wiring), SM712 (pin 3 common), SML-P11/P12 (wiring).
  - NTK3134N SOT-723 (1 G, 2 S, 3 D): pass for Q1, Q3, Q6, Q9–Q13.
  - S3 pass (all supplies on supply symbols). S1-1, S1-3, S2-1 open.
  - PWR_FLAGs are only on genuinely driven rails.
- **T** Test points:
  - T1 pass: every rail has a TP (the post-PTC `P24V0_FIELD` via J1-1 only).
  - T3 pass: no TPs on crystal, RMII or MDI nets.
  - Field supply (U15, T1, D23/D25, L5, U19) re-reviewed end to end: pin strapping (EN, DC open, SR, CLK→GND 1 MHz, SS/ILIM), transformer V·µs and pinout, rectifier/snubbers, filter, preload, eFuse limit vs converter limit, short-circuit heating (C2-1, C2-2, C2-3, C3-2).
  - T2 pass (T2-1 fixed). T3: RMII TPs at the receivers (T3-3). T4 open.
- **G** Ground TPs: G1 pass. G2 Note (G2-1). G3 resolved by decision (G3-1: hand-soldered loops on pads).
- **B** Bode access:
  - Flyback: R16 10 Ω, TP5/TP8 ↔ TP9, TP7, divider and opto on the feedback side: pass.
  - TPS563252: R88 51 Ω, TP22 ↔ TP23/24: pass.
  - TPS54202H: R80 49.9 Ω, TP28 ↔ TP29/31, TP27/32 GND_FIELD: pass.
  - SN6507: no loop; output TP33, return TP27/32: pass.
  - B4 pass.
- **V** Dividers:
  - Flyback 12.02 V (11.57–12.49 V): pass.
  - P3V3 3.32 V (3.21–3.42 V): pass.
  - TPS563252 EN, TPS54202H FB 5.08 V (4.87–5.30 V) and EN: pass.
  - PoE 24.3 k / 75 Ω (Class 2): pass.
  - ISO1211 thresholds: pass.
  - LP3470A293 vs P3V3: pass.
  - V4: pass.
- **P** Decoupling: MCX N per UG10092 Table 2, TPS563252 C_IN and KSZ8081 VDD_1.2 (2.2 µF + 100 nF) pass; KSZ8081 VDDIO Note (P1-2).
- **R** Ratings:
  - AQY212GS LED 7.8–10.5 mA with 220 Ω and NTK3134N (R_DS(on) 0.26 Ω at 2.5 V): pass.
  - FDV304P at 3.3 V: pass.
  - Snubbers 41 %: pass.
  - PNE20020ER, PDS5100Q, SMAJ58A/58CA, SMF36A, SM712: pass.
  - R8 preload 1206: 27–36 %, pass.
  - R2-1 (bench), R2-2, R1-1 open.
- **I** Isolation: I1 pass (domains logic, PSE, field, DI×3, DO×2; no unintended bridges). I2: VO618A 5300 V_RMS ✓; SHIELD net and GND↔GND_FIELD Y-cap as in arch §11; barrier caps KEMET 3 kV MLCC, DWV 3.6 kV DC (I2-3 fixed); barrier ratings meet the arch §11 isolation requirements (1500 Vrms AC on barrier 1, I2-2 resolved). I3 pass.
- **M** MCU:
  - M1 pass.
  - M2 pass except USB.
  - M3 pass.
  - M4: SWD (FTSH-105 polarized) and ISP_N TP pass; USB open (M4-1).
- **X** Interfaces:
  - X1 pass.
  - X2 pass: NTK3134N fully enhanced from 3.3 V GPIOs (R3-2 fixed).
  - X3 pass (X3-3 Note).
  - X4 pass.
- **C** Converters:
  - Si3402 flyback per EVB 12 V row, including the DFLT30A-7 clamp: pass. SWO peak to be confirmed on the bench.
  - TPS563252, TPS54202H: pass.
  - SN6507 (CT full-wave, I_LIM 0.33 A, V·t): pass; C2-1 Note.
  - MCX DCDC: pass (L1 IHLP1212AEEZ1R0M1Z, 1.0 µH, per IHLP-1212-EZ-1Z DS p.1).
- **E** Protection: E3-1 fixed (SHIELD net). E1: E1-1 fixed (TPS26625 eFuse, wiring checked against the datasheet), E1-2 fixed (SMAJ33CA); E1-3 (OVP) and E1-4 (C_IN/C_OUT) fixed. E2: pin assignment and 5.08 mm pitch match arch §10; mating plugs in BOM (E2-1 fixed). E3 pass.
- **W** Power: W1 partial (MCU 18 mA, PHY 47 mA, LEDs; SN6507 limit keeps a field short within Class 2). W2 pass.
- **K** Clocks: K2 resolved (K2-1, firmware). 32 kHz external caps DNP. K1-1, K1-3, K1-4 open.
- **Q** Docs: Q1/Q3 partly fixed (DOC-1). Q2: inputs, output drive, fault architecture, shields/Y-cap, terminals, QSPI and field enable and bench header (J6) match the docs; Q-5 and Q-10 open.
- **H** Hygiene: H1: 0 errors; the 3 non-trivial warnings are tracked in H2-2. H2-1 partly fixed, H2-2/H2-3 open. H3/H4 open.
- **L** Lifecycle: IHLP-1212AE NRND replaced by the "-1Z" series (L1-2 fixed); not checked online otherwise.
