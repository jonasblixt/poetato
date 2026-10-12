# PoEtato schematic review

This is a living document that lists **every finding raised in this review**, each with a status. Rows are updated in place when the schematic or the docs change. Fixed findings stay in the tables, so the history of what was found is visible.

This is a fresh pass over the whole design, started after the 2026-10-04 review was closed out. Items still open from that review were re-checked and are carried over here under new IDs (old ID in brackets); the 2026-10-04 file keeps their history.

| | |
|---|---|
| Review started | 2026-10-09 |
| Revision checked | Working copy saved 2026-10-09 12:32 (KiCad local history `2411b13`), uncommitted on top of git `0790a1d`. |
| Tools | No `kicad-cli` in this session (the shell on Jonas's PC is a Linux VM and cannot reach the Windows KiCad install), so nothing was re-exported. Netlist and ERC come from the `kicad-cli` 10.0.6 export in `hw/poetato/.review/` made at 10:10, which reads the 08:42 save (history `941b45f`). The 08:42 → 12:32 changes were diffed in KiCad's local history (`hw/poetato/.history`). They change no connectivity: the DO sub-sheet label `EN` → `ON` (with the matching sheet pins), the LP3470 `RESET_N` pin type → open collector, and sheet notes on the Ethernet, MCU, IO and RS-485 sheets. |
| Sheets | root `poetato`, `ethernet_poe`, `mcu`, `io` (= /IO/) with sub-sheets `rs485` (/IO/RS485/), `di` ×3 and `do` ×2. `power.kicad_sch` is empty and not instantiated. |
| ERC | 10:10 export: 0 errors, 1 warning (`isolated_pin_label` on the ISO1211 `COOL_POUR`, expected, ISO121x p.3). Not re-run on the 12:32 save. |
| Not checked | ERC and netlist of the 12:32 save (see Tools). Lifecycle on manufacturer pages (not repeated; Jonas's check stands). DC-bias derating is estimated, not read from Murata curves. Anything about layout. |
| Status update | 2026-10-12: netlist re-exported with `kicad-cli` 10.0 on the Windows install; ERC 0 errors, 0 warnings. Items closed or fixed per Jonas; schematic released for layout. Remaining open items are notes only (T4-1 TP63, T3-1, H2-1, S1-1, S2-1, F2-1, D1-1, D2-1, DOC-1). |

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
- **Merged**: tracked in another ID.

Open and partly fixed items are listed first in each table.

## Findings

### Errors

No errors found in this pass. Every net, pin assignment and value checked below is consistent with its datasheet.

### Warnings

| ID | Status | Sheet | Refs | Finding | Evidence | Suggested fix / resolution |
|---|---|---|---|---|---|---|
| E1-1 | Fixed | DO, IO | D18, D19, F1, F2, K1, K2 | **"≤ 30 V AC/DC" output rating does not fit the TVS.** If 30 V AC means 30 V rms, the peak is 42.4 V. That is above the SMAJ33CA breakdown (36.7 V min at 25 °C, ≈ 34.7 V at −30 °C), so D18/D19 conduct on every half-cycle and will fail short, which leaves the output stuck closed. A bigger TVS does not fit under the PhotoMOS: SMAJ36CA clamps at 58.1 V and SMAJ40CA at 64.5 V, against the AQY212GS 60 V absolute and 48 V recommended peak load voltage. **The PPTC is the tighter limit on AC:** Bel allows AC only while the peak-to-peak voltage stays ≤ V_max = 48 V. That is ≈ 17 V rms, and 30 V rms is 85 V peak-to-peak. A tripped F1/F2 on AC above that is outside its rating. The rating appears in arch §7 and §13, the context doc and the IO sheet note. | SMAJ p.2 (SMAJ33CA: V_RWM 33 V, V_BR 36.7–40.6 V, V_C 53.3 V; SMAJ36CA V_C 58.1 V; SMAJ40CA V_C 64.5 V); AQY21xGS p.3–4 (absolute 60 V peak AC; recommended V_L ≤ 48 V peak); 0ZCJ p.1 (V_max 48 V DC), p.3 note 5 (AC: peak-to-peak ≤ V_max) | Rate the outputs **≤ 30 V DC, ≤ 17 V AC rms (≤ 48 V peak-to-peak)**, and say rms or peak wherever an AC figure appears. Inside that the TVS is fine too: 24 V peak, under the 33 V standoff. A 24 V AC relay coil is then outside the rating; if that matters, it needs a PPTC rated ≥ 70 V and a part rated above 60 V instead of the AQY212GS. Update arch §7, §13, context and the IO sheet note (H4-1). **Fixed 2026-10-12:** rating is now ≤ 30 V DC only. IO sheet note reads "≤ 30 V DC, 100mA"; arch §7 and the context doc updated. No hardware change. |
| Q2-1 | Resolved (decision) | RS-485 | U16, J2, J5, R3 | **No fail-safe bias resistors on A/B**, while arch §9 ("Fail-safe biasing resistors") and the context doc ("fail-safe bias") call for them. The ISO3082 itself is fine without them: its receiver is fail-safe for open, shorted and idle terminated buses. The other nodes may not be. An idle, terminated bus sits at 0 V differential, and a slave with a plain MAX485-class receiver (the XY-MD02's transceiver is not documented) can then see framing noise between master frames. | ISO3082 p.1 ("Fail-safe receiver for bus open, short, idle"), p.20 Table 8-3; netlist (A/B nets: U16, R84/R90, D27, J5/R3, J2 only) | Add bias footprints: A → `P5V_RS485` and B → `GND_FIELD`, 680 Ω 0603 each. That gives ≥ 200 mV with 120 Ω at both ends (5 V × 60 Ω / (60 Ω + 2 × 680 Ω) ≈ 0.21 V) for ≈ 3.5 mA from the 5 V rail. Fit or DNP them by decision, and record which in arch §9. Otherwise change the docs to "relies on the ISO3082's internal fail-safe; slaves must be fail-safe too". **Decision 2026-10-12:** no bias resistors. The bus relies on fail-safe receivers (ISO3082 p.1, §8.1 p.19, Table 8-3 p.20); slaves must be fail-safe too. Update arch §9 and the context doc to say so. |
| W2-1 | Resolved (decision) | MCU | D17, R50, C9, C33, U1 pin 47 | **VDD_BAT trails the system supplies on a cold start with an empty supercap.** The MCX N requires VDD_BAT to ramp before or with VDD_SYS. With C9 empty, R50 (220 Ω) loads `VDD_BAT` with ≈ 6–11 mA during the ramp, so it sits a full BAS70 drop below P3V3: ≤ 0.75 V at 10 mA. When P3V3 reaches ≈ 2.0 V and VDD_SYS (LDO_SYS output) is already at 1.8 V, `VDD_BAT` is only ≈ 1.3 V; it passes 1.8 V at P3V3 ≈ 2.5–2.6 V. Arch §3 says "the diode also makes VDD_BAT ramp with VDD_SYS on a cold start with an empty cap", and that only holds within a diode drop. This happens on the first power-up and after every outage longer than the holdup. RESET_b is held by the LP3470 until P3V3 > 2.93 V plus 62 ms, but the datasheet rule is about supply ramps, not reset. | MCX N DS §2.5 p.14 ("VDD_BAT must ramp before or with VDD_SYS"); UG10092 Table 1 p.4 ("This rail is required and must ramp before or with the system domain"); BAS70 (Nexperia) p.3 (V_F ≤ 410 mV at 1 mA, ≤ 750 mV at 10 mA, ≤ 1 V at 15 mA) | Options: (a) raise R50 to 1–2.2 kΩ. Charging current drops to ≤ 3 / ≤ 1.3 mA, so the lag shrinks to ≈ 0.45 V, and C9 still charges in ≈ 30–60 min (τ = R·C), well inside the ≥ 24 h before the holdup matters. The outage-side drop through R50 at ≈ 1 µA stays negligible. (b) Ask NXP whether a lag of one Schottky drop during the ramp is acceptable; FRDM-MCXN947 feeds VDD_BAT directly from LDO1_OUT (SCH-55277, MCU_PWR). (c) Measure VDD_BAT against VDD_SYS (TP16, TP13) at power-up on the first board (verification-plan §5.2). Correct the arch §3 sentence either way. **Decision 2026-10-12:** accepted as is. The rule (DS p.14, UG10092 p.22) sets an order, not a voltage relationship; VDD_BAT ramps together with P3V3, one BAS70 drop lower, and its range is 1.71–3.6 V (DS p.15). Residual: VDD_BAT is below 1.71 V while P3V3 is ≈ 1.9–2.4 V and VDD_SYS may already be at 1.8 V; RESET_b is held until P3V3 > 2.93 V, when VDD_BAT ≈ 2.2 V. With a charged supercap VDD_BAT is up first anyway. Keep the TP16/TP13 power-up measurement (verification-plan §5.2); fix the arch §3 wording. Bring-up note and fallback (R50 → 2.2 kΩ) added to verification-plan §3 and §5.2; arch §3 reworded. |
| R2-1 | Resolved (decision) | Eth | T2, D1, D2, U4 | **The flyback's SWO clamp has almost no window at 12 V.** FA2672 is 1:0.4 (N_p/N_s = 2.5), so during the off-time the primary sees 2.5 × (V_out + V_F) ≈ 2.5 × (12.02 + 0.55) ≈ 31.4 V, and ≈ 32.7 V at the top of the 12 V tolerance (12.49 V). The clamp D2 + D1 starts conducting at V_BR(DFLT30A) + V_F(1N4148W): ≈ 33.3 + 0.6 ≈ 33.9 V for a minimum part at 25 °C. D1 itself sees ≈ 30.8 V every cycle, already above its 30 V standoff. The DFLT datasheet gives no temperature coefficient; with the typical +0.1 %/K of avalanche TVS (Littelfuse), onset drops to ≈ 31.5 + 0.7 ≈ 32.2 V at −30 °C. A low-V_BR part on a cold board with the 12 V rail at the high end then clamps on every cycle: energy goes into D1 instead of the output, D1 heats, efficiency and regulation shift. At the other end, SWO = VPOS + V_clamp + 0.7 V must stay ≤ 100 V, so the clamp may not exceed ≈ 42.3 V at 57 V input. The clamp carries at most the primary peak current (≤ 1.3 A, Doc 560), so it sits near ≈ 40 V rather than the 48.4 V it reaches at 4.65 A: SWO ≈ 98 V hot, about 2 V under the limit. One TVS's spread over temperature and current is wider than the ≈ 33–42 V window. D1's cathode is on SWO: the symbol draws the bar at pin 1, and `D_PowerDI-123` pad 1 is the cathode. The schematic matches the Si3402BISO-EVB 12 V row exactly, so this is inherited from the reference, not a wiring error. Coilcraft lists FA2672 as the 5 V / 2 A part and FA2732 (1:1) as the 12 V / 0.83 A part. | Coilcraft Doc 560 p.1 (FA2672 1:0.4 "5.0 V, 2.0 A"; FA2732 1:1 "12.0 V, 0.83 A"); Si3402BISO-EVB Table 2 p.9 (12 V: FA2672, PDS5100, DFLT30A); DFLT p.2 (DFLT30A: V_RWM 30 V, V_BR 33.3–36.8 V at 1 mA, I_R 1 µA, V_C 48.4 V at 4.65 A); SMAJ p.1 (α_T 0.1 %/K typ.); Si3402-B p.4 (SWO −0.7…100 V, referenced to VSS2) | Either (a) keep the EVB parts and add to poe-verification §4/§11: D1 current and temperature at −30 °C with 37 V and 57 V in and the 12 V rail trimmed high, and SWO peak at +70 °C, 57 V, full load and output short; or (b) evaluate FA2732: the reflected voltage drops to ≈ 12.6–13.1 V, and a DFLT20A (V_BR 22.2 V min, V_C 32.4 V) would hold SWO ≤ ≈ 90 V with ≈ 8 V of margin above the reflected voltage. With (b), D4 sees ≈ 57 + 12.5 ≈ 70 V plus ringing (PDS5100 is 100 V), and the loop must be re-measured at R16 because it leaves the EVB row. **Decision 2026-10-09: option (a).** The EVB parts stay. D1 V_BR screening is in `doc/verification-plan.md` §4.1, the clamp-margin tests in §6.6 (cold conduction, hot SWO peak), and the chamber points in §15.2. Option (b) is the fallback if they fail. |

### Notes

| ID | Status | Refs | Finding |
|---|---|---|---|
| X3-1 | Fixed | U16, Q7, U1 P1_8 | `RS485_RXD` floats whenever the receiver is disabled. ISO3082 R is high-impedance with RE high or open (Table 8-3 p.20), and `RS485_RE_N` is a plain GPIO with no external pull, so this is the state through reset, ROM boot and any time firmware disables RX. The floating node is the gate of the activity-LED FET Q7 (FDV304P, V_GS(th) −0.65…−1.5 V, p.2) and the MCU's LPUART RX, which is also the ROM UART-ISP RXD pin. Add a 100 kΩ pull-up to P3V3 on `RS485_RXD`, or document that firmware enables the P1_8 pull-up before anything else. **2026-10-12:** R8 100 kΩ 0402 from `RS485_RXD` to P3V3 (netlist re-exported, ERC clean). |
| X2-1 | Fixed | J4, R42, U9 | Debug UART back-powering: a USB-UART cable left on J4 while the board is unpowered drives `LPUART1_RXD` high through R42 (330 Ω) into an unpowered MCU, ≈ 8 mA through the pin's ESD diode and U9 into P3V3 (design-in checklist 5.7). Harmless for a bench port. Either note it on the sheet ("connect J4 cable only with board powered") or raise R42 to 1–4.7 kΩ. **Fixed 2026-10-12:** R42 1 kΩ (CRCW04021K00FKED); back-feed ≈ 1.7 mA. |
| T4-1 | Partly fixed | 14 TPs | TPs on auto-named nets: TP5, TP8 (`Net-(C57-Pad1)`, the flyback's 12 V output), TP9, TP10 (Si3402 VDD), TP11, TP13 (VDD_SYS), TP16 (VDD_BAT), TP17 (VDD_CORE), TP18 (DCDC_LX), TP22, TP28, TP30, TP36 (supercap), TP63 (`Net-(U3-TXD0)`). Several of these are real rails, so they also fall under H2: name them, e.g. `P12V0_FLY`, `VDD_CORE`, `VDD_SYS`, `VDD_BAT`, `VBAT_CAP`, `POE_VDD5`, `ETH_TXD0_PHY`, and give the injection nodes names like `INJ_FLY`, `INJ_3V3`, `INJ_5V`. **2026-10-12:** all named (`P12V0_FILTER`, `P12V0_FB_1`, `POE_VDD`, `POE_EROUT`, `VDD_SYS`, `VDD_BAT`, `VDD_CORE`, `DCDC_LX`, `P3V3_FB_1`, `P5V_RS485_FB_1`, `P5V_RS485_LX`, `V_SUPERCAP`) except TP63 on `Net-(U3-TXD0)`. |
| T3-1 | Open (was T3-1) | TP18, TP30 | Switch-node TPs (MCX DCDC_LX, LMR51420 SW) are not marked as deliberate measurement points on the sheet. TP1 (SWO) is covered by verification-plan §6.4. Add a sheet note, or remove them. |
| T2-1 | Resolved (decision) | U18, U17 | No TP on the TPS563252 EN (`Net-(U18-EN)`) or the LMR51420 EN (`Net-(U17-EN)`). Both can be probed at R87 / R97 pads, so low priority. **Closed 2026-10-12:** probe at the R87 / R97 pads. |
| H3-1 | Resolved (decision) | C78, R11, R28, R30 | Now noted on the sheets: C3/C4 ("backup if we need more"), J5 ("Short to enable 120Ohm termination"), R16 (injection point). Remaining: the RS-485 sheet note that explained **C78 DNP** (feed-forward option for loop tuning at R80) and the LMR51420 design values was deleted in the 12:31 save; R11 and R30 (0 Ω EVB compensation positions R8/R12) and R28 (0 Ω between the flyback output and `P12V0`) have no note saying what they are for. See Q-3. **Closed 2026-10-12:** remaining notes not needed. |
| H4-1 | Fixed | IO, DO sheets | The IO and MCU notes now match the docs (3 W supply, ≥ 8 h backup). Remaining: IO "Output 1 - 2: <= 30 AC/DC" has no unit and needs the AC wording from E1-1. The DO notes "2.4A peak @ 24V short" and "< 20ms TtT @ 2.4A" disagree with arch §7, which gives 1.5–2.1 A at 24 V (10 Ω plus PPTC 1.1–5 Ω plus R_on); 2.4 A is 24 V / 10 Ω alone. **Fixed 2026-10-12:** IO note "≤ 30 V DC, 100mA"; DO notes "1.5-2.1 A peak @ 24V short", "< 20ms TtT @ 2A". |
| H2-1 | Partly fixed (was H2-1) | — | Orphan `power.kicad_sch` is still in the project, and the `power` library still holds non-power parts (LP3470A293DBVR, TLVH431AQDBVR, TPS26625DRCR, TP, BOM_Entry). Rail auto-names: see T4-1. |
| S1-1 | Partly fixed (was S1-1) | D17, U4 | The BAS70-04 symbol still lacks pin 2 (cathode of the unused second diode; wiring is correct), and Si3402 pin 5 is still named `NC`, although it is PLOSS (Si3402-B Table 8 p.16). The DFLT30A, SMF36A and SMAJ58A symbols are drawn as unidirectional TVS with pin 1 at the cathode, which is correct, but the pins are named `A1`/`A2` as for a bidirectional part; `K`/`A` would remove the doubt. |
| S2-1 | Open | U11, U15, U3, U19 | Pin types that silence ERC supply checks: U11 S25FL064L has every pin passive, including Vcc and GND; U15 SN6507 GND pins 2/9/11 passive; U3 KSZ8081 VDD_1.2 (internal regulator output) passive; U19 TPS26625 GND/RTN passive. The LP3470 RESET_N fix from the old S2-1 is in (open collector since 12:31). |
| F2-1 | Partly fixed (was F2-1) | D12/D20/D21, J4–J6, J8, M10, LEDs, M15/M16, Q7/Q8, Q1–Q13 | Manufacturer spelling: "Littlefuse" (D12/D20/D21) vs "Littelfuse"; "Wurth" (15 parts) vs "Wurth Elektronik" (T1, T3); "Phoenix" (M15, M16) vs "Phoenix Contact" (J1, J2); "Fairchild" on FDV304P (now onsemi), and "ON Semi" on NTK3134N. Value fields mix conventions: SMAJ parts show V_BR (36.7V, 31.1V, 64.4V) while D1 shows its standoff (30V) and D12 shows 36V. |
| D1-1 | Open | D17, Y1, Y3 | D17 is Vishay `BAS70-04-G3-08`, but `discretes/BAS70-04_Nexperia.pdf` is Nexperia's datasheet and does not list the Vishay ordering code; add the Vishay sheet (`discretes/BAS70-04_Vishay.pdf`). Crystals: `FC-135R_Epson.pdf` lists C_L 7/9/12.5 pF and the code only as `X1A000141xxxx00`, and `TSX-3225_FA-238_Epson.pdf` does not decode `X1E0000210048`. The 6 pF and 9 pF come from distributor data. Ask Epson for the spec sheets of the exact codes. The inventory script cannot match either crystal by file name. |
| D2-1 | Open | `datasheets/` | Reference files that do not follow the naming rule: `mcu/UG10092.pdf` → `UG10092_MCX-N-hardware-design-guide_NXP.pdf`, `mcu/SCH-55277.pdf` → `FRDM-MCXN947_schematic_SCH-55277_NXP.pdf`, `mcu/AN14544.pdf` → `AN14544_EdgeLock-2GO_NXP.pdf`. The unused files from the old D2-3 (NX3215SA, NX3225SA, IHLP-1212AE-11, GA352QR7GF102KW01, TPS54202H, `power/field/lmr51420.pdf`) are deleted in the working tree but not yet committed. |
| R1-1 | Resolved (decision) | C80, C93, C42 | MLCC voltage below the 2× rule: C80/C93 (4.7 µF 50 V X7R 1206) on `P24V0_FIELD`, which sits at ≈ 27–28 V unloaded (1.8×); C42 (22 µF 6.3 V) on P3V3 (1.9×). Effective capacitance is still adequate, with C72 22 µF electrolytic on the same rail as the LMR51420 input. Accept, or move C80/C93 to 100 V parts (4.7 µF 100 V exists in 1210, e.g. Murata GRM32DC72A475KE01) and C42 to 10 V. **Decision 2026-10-12:** keep C80/C93 50 V and C42 6.3 V; effective capacitance is adequate. |
| DOC-1 | Open | docs | Docs stale or inconsistent (Q1/Q3): <br>• Arch §3 VDD_BAT sketch says "100 nF at pin"; the schematic has C33 1 µF (fine, UG10092 asks for ≥ 0.1 µF). The "ramps with VDD_SYS" claim: W2-1. <br>• Arch §9 and context: fail-safe bias resistors (Q2-1). <br>• Context DO section still lists "ferrite/CM choke, field-side status LED if possible"; arch §7 and the schematic have no choke and a logic-side LED. <br>• Output AC rating wording in arch §7, §13, context and the IO note (E1-1). <br>• ~~poe-verification §0~~ Done 2026-10-09 in `doc/verification-plan.md` §4.3/§6.6, which replaces poe-verification: §0 expected ≈ 0.9 mA hipot leakage from C90/C91. If SHIELD (magjack shell, J2-4) is on the "other conductors" side, the magjack's internal Bob Smith 1 nF / 2 kV (7499511440 p.2) adds ≈ 0.47 mA: ≈ 1.4 mA in total, still under the 3 mA trip. Add the clamp-current check from R2-1 to §4/§11. <br>• security-requirements §6: "USB0 (FS) pins 44–46"; pin 44 is VDD_USB, USB0 is 45/46. <br>• Arch §10 thermal: "real draw is about 4.2 W" against the 4.07 W budget. <br>• Context key parts: "SE051C2/SE051C2". <br>• The `claude context.md` copy in the Claude project is older than `doc/claude context.md` (NDK crystals, R8 preload, 4.14 W budget). |
| L2-1 | Info | — | Single-source parts on critical functions: Si3402-B (Silvertel module is the documented alternative), MCXN247 (MCXN547VKLT drop-in), KSZ8081RNB, SE051C2, ISO1211, ISO3082, SN6507, TPS26625, LMR51420, TPS563252, FA2672, 750319693, 7499511440 magjack. No action; for the record. |
| C4-1 | Info | U4, T2, D4, U5, U6, R5–R16, C38–C57 | PoE front end and flyback re-checked against the Si3402BISO-EVB 12 V row: R5 75 Ω (Class 2, EVB Table 3 p.10), R6 24.3 kΩ 0805, divider 88.7 k / 10.2 k → 12.02 V, R14 3 k opto series, C39 10 nF / C54 15 nF, R11/R30 0 Ω, snubber 20 Ω + 68 pF, PDS5100, 22 µF + 1 µH + 470 µF, DFLT30A + 1N4148W clamp, C90 VPOS↔12 V and C91 VNEG↔GND as EVB C19/C20. HSO tied to VSS2 and FB to VPOS as the pin table requires (Si3402-B Table 8 p.16). FA2672 secondaries 5–7 and 6–8 are paralleled by tying 5+6 (→ D4) and 7+8 (→ GND), and the dot polarity is right for a flyback (Doc 560 p.1). Magjack V1/V2 → CT1/CT2 (pairs 1-2/3-6), V3/V4 → SP1/SP2 (4-5/7-8), with the Bob Smith network inside (7499511440 p.2). |
| K2-1 | Info | U1 P1_4, U3 XI | RMII clock: the MCU drives 50 MHz out of P1_4 (ENET0_TX_CLK, ENETRMIICLKSEL ≠ 0), as UG10092 §8.5.1 p.34 describes; the PHY takes it on XI in 50 MHz mode (KSZ8081 p.20, Fig. 7-15 p.57). Firmware step (Reg 1Fh.7) is recorded in arch §4. |
| P3-1 | Info | P3V3, U18 | TPS563252 output capacitance: P3V3 carries 19 × 1 µF + 2 × 10 µF + 2 × 22 µF ≈ 83 µF nominal (≈ 40–55 µF after DC bias, plus 21 µF behind FB5), inside the 22–88 µF range for 3.3 V in TPS563252 Table 8-2 p.16, with L4 2.2 µH and C84 33 pF as listed there. |

### Questions

| ID | Status | Question / answer |
|---|---|---|
| Q-1 | Answered | Output rating: is "30 V AC" meant as rms or peak? Decides E1-1 (rating text only, or a hardware change). **2026-10-12:** DC only, ≤ 30 V (E1-1). |
| Q-2 | Answered | RS-485 bias: fit bias resistors, footprints only, or rely on fail-safe receivers everywhere (Q2-1)? Is there a 120 Ω terminator at the sensor end too? **2026-10-12:** no bias resistors, rely on fail-safe receivers (Q2-1). |
| Q-3 | Answered | What is R28 (0 Ω 0805, flyback output → `P12V0`) for: isolating the flyback for bench tests, or a placeholder for something else? Was the C78/LMR51420 note removed on purpose (H3-1)? **2026-10-12:** R28 is a debug link to disconnect the flyback from `P12V0` completely. The feedback (R16, divider, opto) senses on the flyback side of R28, so with R28 out the flyback still regulates, unloaded. Add a sheet note (H3-1). |
| Q-4 | Fixed | TPS563252 enable: R86/R87 (47 k / 20.5 k) start the 3V3 buck at ≈ 3.9 V of the 12 V rail and stop it at ≈ 3.3 V (EN 1.19 V rising / 1.00 V falling, TPS563252 p.5). Intended? A threshold of ≈ 8–9 V would keep the buck off the flyback during its soft-start and give a cleaner brown-out. The EN pin stays under 5.5 V at any rail up to ≈ 18 V, so there is no rating problem either way. **2026-10-12:** move the threshold to ≈ 8.6 V: R86 47 k → 127 k (CRCW0402127KFKED), R87 20.5 k stays. On 8.3–9.0 V (8.64 V typ incl. the 2 MΩ internal pull-down), off 6.5–7.9 V; EN 1.74 V at 12.49 V. Pending schematic change. **Fixed 2026-10-12:** R23 127 kΩ (CRCW0402127KFKED) replaces R86, R87 20.5 kΩ. |

## Checks performed

Last run against the revision in the header. "Pass" means verified against the cited source; findings are listed above.

- **F** Fields: F1 pass: every symbol except the 68 BOM-excluded TPs has Part Number and Manufacturer; DNP parts are C3, C4, C78. F2: every CRCW resistor and Murata capacitor value decoded from its part number matches the Value field; naming conventions still mixed (F2-1).
- **D** Datasheets: D1 pass for every required part except the Vishay BAS70-04 and the exact Epson crystal codes (D1-1). D2: unused reference files remain by design; naming (D2-1).
- **S** Symbols:
  - S1 pass: MCXN247VKLT, all 101 pins against `MCXNP184M150F70_Pinout.xlsx` (100HLQFP N24 column, EP = VSS).
  - S1 pass: KSZ8081RNB (Table 2-3 p.10–12), Si3402-B (Table 8 p.16; S1-1), SE051 (Table 3 p.12–13), TLVH431 DBV (1 NC, 2 substrate, 3 K, 4 REF, 5 A; p.3), LP3470A (p.4), ISO1211, ISO3082 (p.4), TPS26625 (p.4), FDV304P (1 G, 2 S, 3 D), USBLC6-4, FA2672 (Doc 560), magjack 7499511440 (p.2), polarised capacitors (pin 1 = +).
  - S1 pass: TVS orientation (cathode on pin 1, toward the positive node) for D1, D6, D12/D20/D21.
  - S2: open items in S2-1. S3: pass; supply symbols correct; GND_FIELD and SHIELD drawn with the ground graphic.
- **T** Test points:
  - T1 pass: every rail has a TP (`P24V0_FIELD_PROT` only via J1-1; USB_VBUS via J8).
  - T2 pass, apart from the U17/U18 EN pins (T2-1).
  - T3: RMII TP63/TP64 deliberate (noted on the sheets); switch nodes open (T3-1).
  - T4 open (T4-1).
- **G** Ground TPs: G1 pass, each domain on its own return. G2 pass: PSE 3 (TP4 VNEG, TP6 and TP69 VSS2), field 3 (TP27, TP32, TP67), logic 12, against the rule's 3 / 3 / ≈ 10. G3 resolved by decision in the 2026-10-04 review (pads, hand-soldered loops).
- **B** Bode access:
  - Flyback: R16 10 Ω, TP8 ↔ TP9; divider and opto LED both on the feedback side. Pass.
  - TPS563252: R88 51 Ω, TP24 ↔ TP22. Pass.
  - LMR51420: R80 49.9 Ω, TP29/TP31 ↔ TP28. Pass.
  - SN6507: no loop; TP33 and GND_FIELD TPs. Pass.
  - MCX N DCDC: internal loop, not measurable (N/A).
- **V** Dividers:
  - Flyback 1.24 × (1 + 88.7/10.2) = 12.02 V. Pass.
  - TPS563252 0.6 × (1 + 133/29.4) = 3.31 V. Pass.
  - TPS563252 EN 3.9 V on / 3.3 V off (Q-4).
  - LMR51420 0.6 × (1 + 100/13.7) = 4.98 V; EN 13.5 V on. Pass.
  - TPS26625 UVLO 1.2 × 214/14 = 18.3 V; UVLO pin 1.96 V at a 30 V rail, against 5 V absolute. Pass.
  - ISO1211 thresholds with R_THR 1 kΩ: V_IH ≤ 10.95 V, V_IL ≥ 8.7 V, Type 3 (ISO121x p.11). Pass.
  - PoE R5/R6. Pass.
  - LED currents: ETH ≈ 4 mA, status ≈ 2.8 mA, AQY 7.8–10.5 mA. Pass.
  - V4 pass.
- **P** Decoupling, against UG10092 Table 2 p.19–20:
  - VDD_CORE: 2 × 10 µF + 2 × 1 µF = 22 µF, inside 6–30 µF (DS Table 15 p.20).
  - VDD_SYS: 2.2 µF. VDD_DCDC on P3V3 with 10 µF parts. VDD/VDD_Px/VDD_USB/VREFH: shared 1 µF and 10 µF parts.
  - KSZ8081: VDD_1.2 2.2 µF + 100 nF; VDDA via FB5 with 21 µF; VDDIO 22 µF + 1 µF. CT caps separate 100 nF each (p.58).
  - TPS563252 output capacitance: see P3-1.
  - Pass.
- **R** Ratings:
  - SWO clamp margin: R2-1.
  - PDS5100 reverse ≈ 35 V at 57 V. PNE20020ER 200 V. SMAJ58A/58CA (V_BR 64.4 V min) above 57 V PoE. SMF36A standoff 36 V against 30 V. D24 SMAJ28CA standoff 28 V, the unloaded rail ≤ 28 V. Pass.
  - Output TVS against an AC rating: E1-1.
  - MLCC voltage ratios: R1-1.
- **I** Isolation: I1 pass. Union of all nets through non-barrier parts gives exactly seven islands: logic (186 nets, incl. P12V0), PSE (24), field (25), DI1, DI2, DI3, DO1, DO2. They are joined only by T1, T2, T3, U5, U12–U14, U16, K1/K2, C89–C92 and R15. I2/I3 unchanged since the 2026-10-04 review (KEMET 3 kV barrier caps, SHIELD net). Pass.
- **M** MCU:
  - M1 pass, all from the pinout xlsx:
    - FC4 on P1_8–P1_11 (RXD/TXD/RTS → DE/CTS pin as GPIO for RE_N).
    - FC1 on P0_20/P0_21 (debug UART); FC0 on P0_16/P0_17 (SE051 I²C, MED+I2C pads).
    - FlexSPI0 A on P3_0/P3_7–P3_11.
    - ENET0 on P1_2–P1_7/P1_13–P1_15.
    - CLKOUT on P2_2, ISPMODE_N on P0_6, SWD on P0_0–P0_2.
  - M2 pass, design-in checklist:
    - EP to GND.
    - RESET_b with 100 nF + 100 Ω (UG10092 §10.1.2 p.39).
    - ISP pin internal pull-up (p.40).
    - USB1 VBUS direct to pin 42, no inline resistors.
    - USB0 unused.
    - VBAT_WAKEUP_b (P5_2) unconnected.
    - GPIO back-powering via J4: X2-1.
    - Sequencing: W2-1.
  - M3 pass:
    - DO1/DO2_ON and P24V_FIELD_EN pins default DIS, with 2.2 kΩ pull-downs.
    - ETH_RST_N held low by R41.
    - ISO3082 DE internal pull-down.
    - RS485_RXD floats (X3-1).
  - M4 pass: SWD FTSH-105 pinout (1 VTref via 100 Ω, 2 SWDIO, 4 SWCLK, 6 SWO, 10 nRESET; pin 7 keyed), USB1 HS ISP, TP19 ISP.
- **X** Interfaces:
  - X1 pass: SE051 2.2 kΩ to 3V3, single set; MDIO 1 kΩ (KSZ8081 Table 2-3 p.10); INTRP 4.7 kΩ.
  - X2 pass, apart from X2-1.
  - X3:
    - KSZ8081 straps: PHYAD = 001, CONFIG[2:0] = 001 (RMII), NWAYEN = 1, SPEED = 1. Pass.
    - SE051 ENA/RST_N/LA/LB tied. Pass.
    - QSPI CS#/WP#/IO3 pulled up. Pass.
    - TPS26625 SHDN open (internal pull-up) and SN6507 DC open. Pass.
    - RS485_RXD: X3-1.
  - X4 pass:
    - 33 Ω on RMII and REF_CLK, and on QSPI SCK.
    - UART and RS-485 TX/RX not swapped.
    - Termination by jumper.
    - Fail-safe bias: Q2-1.
- **C** Converters:
  - Flyback per EVB (C4-1), clamp margin R2-1.
  - TPS563252: L 2.2 µH, C_OUT, C_FF 33 pF per Table 8-2. Pass.
  - LMR51420, SN6507 and TPS26625: unchanged since the 2026-10-04 review (C2-1, C3-2, C5-1 there), re-checked pinout and divider values. Pass.
  - MCX DCDC: L1 1 µH (DS Table 15: 1–1.5 µH recommended). Pass.
- **E** Protection:
  - E1: every connector pin has a protection path:
    - J1-1 eFuse + SMAJ28CA.
    - J1-3…6 10 Ω + PPTC + SMAJ33CA (AC: E1-1).
    - J1-7…12 1 kΩ MELF + SMF36A.
    - J2 SM712 + 10 Ω.
    - J3 U8, J4 U9, J8 U20.
    - RJ45: magjack, U7, D3/D5/D6.
    - J6 none by decision.
  - E2 pass: J1/J2 pin order matches arch §10.
  - E3 pass:
    - Bob Smith inside the magjack.
    - PHY-side centre taps separate 100 nF.
    - J8 shell to GND, which the checklist requires; it is a bench service port, so the SHIELD rule does not apply.
- **W** Power: W1 unchanged since the 2026-10-04 review. W2: LP3470A293 with 62 ms (C8 100 nF, t_D = 619 × C, LP3470A p.4); VDD_BAT ramp: W2-1.
- **K** Clocks:
  - Y3 TSX-3225 9 pF with C1/C2 10 pF; measure the frequency on the first board.
  - Y1 FC-135R 6 pF on the internal caps, C3/C4 DNP (now noted).
  - Exact crystal spec sheets: D1-1.
  - K2 pass (K2-1).
- **Q** Docs: Q1/Q3 in DOC-1; Q2 deviations: Q2-1 (fail-safe bias) and W2-1 (VDD_BAT claim).
- **H** Hygiene: H1 per the 10:10 export (0 errors, 1 expected warning). H2-1, H3-1, H4-1 partly fixed. The old H2-3 is fixed: the DO sub-sheet labels are now `ON`, matching `DO1_ON`/`DO2_ON`.
- **L** Lifecycle: not re-checked online in this pass. L2 single-source list in L2-1.
