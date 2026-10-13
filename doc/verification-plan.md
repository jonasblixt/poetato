# PoEtato — board verification plan, revision 1

Scope: the first board revision, built from schematic rev A (`hw/poetato`, working copy of 2026-10-09). It covers bring-up, every circuit block, isolation, the PoE flyback, thermal and climate-chamber tests, and the measurements outside the box that the design still depends on.

This document replaces `doc/poe-verification.md`. The PoE plan is now §6 (front end and flyback) and §15 (climate chamber). The schematic items that plan raised before layout are all closed, and the review tables record them (`doc/review/`).

Each test names the decision or review finding it checks, in brackets: arch §n is `doc/hardware-architecture.md`, review IDs (e.g. R2-1) are in `doc/review/schematic-review-2026-10-09.md`. The traceability table is in §17.

---

## 1. Conventions

- **Pass criteria are fixed before the test.** Write them down before measuring, and change them only up front, never after you have seen the data.
- **Record every result** in the results log at the end, with the board serial, date, conditions and instrument settings, including failures and re-runs.
- **Two boards.** Board A keeps its lifecycle open (secure boot not enforced, debug open) for development. Board B is the one that gets provisioned and closed (arch §4). Run the destructive tests (shorts, surge, hipot) on board A first.
- **Test points.** TP numbers refer to the schematic. Each rail has a TP, and each domain has its own ground TPs:
  - PSE: TP4 (VNEG), TP6 and TP69 (VSS2).
  - Logic: TP7, TP14, TP15, TP21, TP25, TP26, TP37, TP54, TP55, TP65, TP66, TP68.
  - Field: TP27, TP32, TP67.

  Never use a ground TP from another domain as the probe reference.
- **Ambient** is 23 ± 5 °C unless the test says otherwise.

## 2. Equipment and safety

**Instruments**
- Lab supplies: 0–60 V / 0.5 A for PoE (applied to VPOS/VNEG or through the pairs), 0–15 V / 1 A for the J6 bench header, 0–30 V / 3 A for output and input tests.
- 802.3af PSEs: the actual UPS-backed switch, one other switch and a midspan.
- Scope with a differential probe for the primary side, a current probe, and a tip-and-barrel adapter for ripple.
- Bode 100 with injection transformer. Picotest J2111A, or a DIY MOSFET plus resistor injector, for Zout and load steps.
- Electronic load.
- Frequency counter, or a scope with an external 10 MHz reference, good to ≤ 1 ppm.
- AC hipot tester, 50 Hz, adjustable trip current.
- Thermocouples and an IR camera.
- Climate chamber, −30 … +70 °C.
- USB–RS-485 dongle and an XY-MD02 sensor.
- USB–UART cable (3.3 V) for J4, SWD probe for J3.
- Curve tracer or SMU, or a lab supply with a series resistor, for TVS breakdown screening.

**Safety and setup**
- Use a differential probe on the primary side. Never connect scope grounds on both sides of a barrier.
- Current-limit every supply. J6 is unkeyed and has no reverse-polarity protection (arch §3 *Notes*), so use a marked cable.
- A bare flyback needs at least 250 mW of load to avoid switcher pulsing. Fit a load resistor for tests without the rest of the board.
- The hipot tester is the only test in this plan with dangerous voltage. Use an interlocked fixture for it.

## 3. Bring-up order

Power the board in stages, so a fault in one block cannot take out the next:

1. Unpowered checks (§4).
2. Logic power from the J6 bench header at 12 V, current-limited to 300 mA, with PoE disconnected (§5). The flyback output is reached through R28 (0 Ω).
3. MCU and debug: SWD, clocks, flash (§7).
4. Field supply, enabled by firmware (§9).
5. PoE through a lab supply on VPOS/VNEG, then through the pairs, then through a real PSE (§6).
6. Everything else (§8, §10–§13).

If the flyback needs to be tested alone, lift R28 to separate it from `P12V0` and put a load on TP8 (review Q-3).

The 3V3 buck starts at ≈ 8.6 V and stops at ≈ 7.2 V on `P12V0` (R23/R87), so a bench supply on J6 must be ≥ 9 V.

**If the MCU fails to boot or behaves oddly after a cold start**, suspect the VDD_BAT ramp first (§5.2, review W2-1): with an empty supercap VDD_BAT trails 3V3 by one diode drop. Raise R50 220 Ω → 2.2 kΩ and retry.

---

## 4. Unpowered checks

### 4.1 Assembly and rail resistance

- Visual inspection: polarised parts (C9, C50, C57, C72, D4, D6, D12/D20/D21, D17, all LEDs) and pin 1 of every IC.
- **Screen D1 before fitting** (R2-1). Measure the DFLT30A-7's V_BR at 1 mA, using a lab supply and a series resistor. Record the value and the board it goes on. The cold-margin estimate in §6.6 uses it.
- Resistance from each rail to its own ground, with every supply off:
  - `P12V0`, P3V3, VDD_CORE (TP17), VDD_SYS (TP13), VDD_BAT (TP16).
  - `P24V0_FIELD` (TP33), `P5V_RS485` (TP29), POE_VPOS (TP2).

  Pass: no rail below ≈ 100 Ω. Record the values; the large capacitors make the reading drift as they charge.
- Continuity: each ground domain to its ground TPs. No continuity between domains: GND, GND_FIELD, VNEG/VSS2, SHIELD, each DIn−, each DO pair.

### 4.2 Transformers (Bode 100, impedance mode)

| Part | Measure | Compare with |
|---|---|---|
| T2 FA2672 | Primary inductance (2–3); leakage inductance with all secondaries shorted; primary-to-secondary capacitance | 40 µH ± 10 %, ≤ 0.34 µH leakage (Coilcraft Doc 560). The capacitance feeds the surge reasoning (arch §11) |
| T1 750319693 | Inductance N1+N2; leakage inductance; interwinding capacitance | ≥ 100 µH, 210 nH typ., 16 pF typ. (Würth p.1) |

### 4.3 Isolation (hipot)

These are the requirements in arch §11 *Isolation requirements*.

| Barrier | Test | Pass |
|---|---|---|
| Cable/PoE ↔ everything else | **1500 Vrms, 50 Hz, 60 s.** All cable and PoE conductors tied together on the high side: RJ45 pins, POE_VPOS, POE_VNEG, POE_VSS2. Everything else on the low side: GND, GND_FIELD, SHIELD (magjack shell and J2-4), all J1/J2 terminals | No breakdown or flash-over. Leakage ≈ 1.4 mA: C90 + C91 (KEMET 1 nF / 3 kV) ≈ 0.9 mA, plus ≈ 0.47 mA through the magjack's internal Bob Smith 1 nF / 2 kV to the shell. Set the trip to 3 mA. |
| Logic ↔ field 24 V domain | 500 Vrms, 60 s, GND against GND_FIELD | No breakdown; ≈ 0.16 mA through C92 |
| Logic ↔ each digital input | 500 Vrms, 60 s, GND against each DIn+/DIn− pair | No breakdown |
| Logic ↔ each output contact | 500 Vrms, 60 s, GND against each DO A/B pair | No breakdown |

- C90 to C92 are DC-rated MLCCs, not AC-qualified parts, so this first hipot is also their AC-withstand check.
- Repeat the 1500 Vrms test after the climate-chamber condensation run (§15.4).

---

## 5. Logic power (from J6, PoE off)

### 5.1 12 V rail and 3V3 buck (TPS563252, U18)

| Test | How | Pass |
|---|---|---|
| Start and stop threshold (review Q-4) | Ramp J6 slowly from 0 to 12 V and back; watch P3V3 (TP23) | Starts at ≈ 3.9 V and stops at ≈ 3.3 V (EN 1.19 V rising / 1.00 V falling), no oscillation at the threshold. Record the values; this is the evidence for Q-4. |
| Regulation | 12 V in, P3V3 load 50 mA and 500 mA (e-load on TP23/TP24 plus the board) | 3.21–3.42 V, nominal 3.31 V |
| Ripple | Tip-and-barrel at C85, 20 MHz bandwidth limit on and off | Record; expect < 30 mV pk-pk |
| Loop gain | Inject across R88 (51 Ω): TP24 (output) to TP22 (feedback side), ground TP7. 10, 50 and 100 % load | Phase margin ≥ 45°, gain margin ≥ 10 dB |
| Load step | 10 % ↔ 90 % | Dip stays above 3.10 V, so the LP3470 never releases and re-asserts |

### 5.2 MCU supplies and reset

| Test | How | Pass |
|---|---|---|
| VDD_CORE (DCDC) | TP17, under load at 150 MHz | 1.2 V default (0.85–1.21 V range); ripple ≈ 1 % (MCX N DS Table 15) |
| DCDC switch node | TP18, a deliberate measurement point (review T3-1) | Clean switching at 3–8 MHz, no gross ringing |
| VDD_SYS | TP13 | 1.71–1.98 V |
| Supervisor | Ramp P3V3 slowly by ramping J6 near the buck threshold; watch `RESET_N` on J3 pin 10 | Asserts at 2.89–2.97 V, releases ≤ 3.10 V, after ≈ 62 ms (C8 100 nF) |
| **VDD_BAT sequencing (review W2-1)** | Discharge C9 fully (short TP36 to GND through 10 Ω). Power up from J6 with a fast edge, then with a slow 50 ms ramp. Capture VDD_BAT (TP16), VDD_SYS (TP13) and P3V3 together | Record how far VDD_BAT lags P3V3 and VDD_SYS, and how long VDD_BAT stays below 1.71 V while VDD_SYS is up. Expected: one BAS70 drop (≈ 0.7 V) during the ramp, VDD_BAT ≈ 2.2 V when `RESET_N` releases. Accepted by design (W2-1, 2026-10-12), so this is a record, not a gate. The MCU must start normally and the RTC domain must report a clean POR. **If boot problems show up anywhere (hangs after cold start, bad RTC/VBAT state, ROM not starting), try this first:** raise R50 220 Ω → 2.2 kΩ (≈ 1.2 mA charge current, ≈ 0.4 V lag) and repeat. |
| PHY brown-out window (arch §13, LP3470 row) | Hold P3V3 at 3.0–3.1 V (between the PHY's 3.135 V minimum and the supervisor's release threshold), then return it to 3.3 V | Firmware detects the PHY fault and resets it; the link comes back without a power cycle |

---

## 6. PoE PD front end and flyback

Scope: PD front end and the Si3402-B isolated flyback (U4, T2 FA2672-ALD, D4 PDS5100, VO618A opto) feeding the 12 V logic rail. The reference design is the Si3402BISO-EVB in its 12 V configuration; the schematic matches that row (review C4-1).

Carried over from the PoE plan as an open item: the output filter differs from the EVB. It uses a 470 µF EMZL aluminium electrolytic (C57) with L2 1 µH, where the EVB uses a standard-ESR 470 µF. The compensation is therefore confirmed by measurement in §6.5, not assumed.

### 6.1 PD signature (low voltage, switcher off)

| Test | How | Pass |
|---|---|---|
| Detection | Two points between 2.7 and 10 V; ΔV/ΔI | 23.75–26.25 kΩ |
| Classification | 15.5 V and 20.5 V | 17–20 mA (Class 2, R5 75 Ω) |
| UVLO | Ramp slowly up, then down | On at ≤ 42 V (typ. 37 V), off at ≥ 30 V (typ. 32 V), no chatter |
| Inrush | Current probe at turn-on | About 140 mA limit, then the switcher starts |

### 6.2 Start-up and shutdown

- **Conditions:** Vin 37, 48 and 57 V, into no load, full load (about 0.36 A at 12 V) and full load plus the real downstream capacitance.
- **Pass:** 12 V rises monotonically with little overshoot, and the downstream bucks don't cycle.
- **Brown-out:** slow ramp down, then back up. Check for a clean off and a clean restart.

### 6.3 Steady state

- **Grid:** Vin 37, 44, 48 and 57 V × load 0, 10, 50 and 100 %, plus about 150 % overload.
- **Record:** Vout (regulation), input current, efficiency. Target about 85 %, which is what the 0.64 W loss budget assumes.
- **Pass:** Vout 11.57–12.49 V over the grid.
- **Ripple:** at the output, before and after L2, with a tip-and-barrel connection, 20 MHz bandwidth limit on and off.

### 6.4 Switching stress

Worst case is 57 V, full load, output short and start-up.

- **SWO peak** at TP1, referenced to VSS2 at TP69, with a differential probe:
  - Absolute maximum 100 V.
  - Target ≤ 95 V, which leaves 5 V margin. The expected value is ≈ 98 V hot (review R2-1), so this is the test most likely to fail.
  - The hot case is in §15.
- **D4 (PDS5100):** reverse voltage spike against its 100 V rating.
- **Snubbers:** dissipation in R9 (secondary snubber) and in the clamp.
- **Conduction mode:** note where the converter moves between CCM and DCM. This matters for the loop measurement.

### 6.5 Loop gain (Bode 100 + injection transformer)

- **Where to inject:** across R16 (10 Ω), TP8 (output side) to TP9 (feedback side), as noted on the Ethernet sheet. Both the opto "fast lane" (R14) and the TLVH431 divider (R12/R13) sit on the feedback side, so both are inside the loop. If only the divider were inside, the reading would look good but be wrong.
- **Settings:** start at 20–50 mV injection, check the result doesn't change when you vary the level, and use a shaped level profile if the low end gets noisy.
- **Test grid:** 37, 48 and 57 V × 10, 50 and 100 % load.
- **Pass:** phase margin ≥ 45°, gain margin ≥ 10 dB, crossover well below about 1/5 of the right-half-plane zero at 37 V and full load.
- **Opto spread:** if possible, test two opto parts or boards, because the VO618A CTR bins vary.
- **Temperature:** see §15.

### 6.6 SWO clamp margin (review R2-1, option a)

Decided 2026-10-09: keep the EVB parts (FA2672, DFLT30A-7 + 1N4148W) and verify the margin on the bench.

**Why.** During the off-time the primary sits at 2.5 × (V_out + V_F) ≈ 31.4 V, or ≈ 32.7 V with the 12 V rail at its 12.49 V limit. The clamp starts at V_BR(D1) + V_F(D2), which is ≈ 33.9 V for a minimum part at 25 °C. With the typical +0.1 %/K of an avalanche TVS, it falls to ≈ 32.2 V at −30 °C. The DFLT datasheet gives no temperature coefficient, so the +0.1 %/K is an assumption.

**Measure:**

| Test | How | Pass |
|---|---|---|
| Predicted margin | From D1's measured V_BR (§4.1) and the measured 12 V: margin = V_BR × (1 − 0.0055) + 0.7 − 2.5 × (V_out + 0.6), the cold case at −30 °C | ≥ 0.5 V, or flag the board for the cold test first |
| Clamp conduction, room temperature | SWO at TP1 (ref TP69) at 37 V and 57 V in, full load. Check whether the off-time plateau is flat at the clamp level for the whole secondary conduction interval (clamp conducting), or only clips the leading spike (correct). D1 case temperature with a thermocouple | Plateau ≥ 1 V below the clamp level; D1 rise < 20 K |
| **Clamp conduction, cold** | The same at −30 °C board temperature, 37 V and 57 V, full load (§15) | Same pass criteria. Efficiency within 2 percentage points of the 25 °C value at the same input and load |
| SWO peak, hot | +70 °C, 57 V, full load, output short and start-up (§15) | ≤ 95 V target, < 100 V absolute |

If either cold or hot fails, the fallback is the 1:1 FA2732 with a lower-voltage clamp (e.g. DFLT20A), which needs §6.5 to be redone (review R2-1, option b).

### 6.7 Output impedance and downstream converters

- **Zout:** Bode 100 with a current injector. Look for peaking, especially the L2/downstream-ceramic resonance.
- **Zin of the loads:** measure or estimate the input impedance of the 3V3 buck and the SN6507.
- **Check (Middlebrook's criterion):** the flyback's Zout must stay well below each converter's input impedance, which behaves like a negative resistance.

### 6.8 Transients

- **Load step:** 10 % to 90 % and back with a MOSFET switch.
  - Pass: the 12 V dip stays clear of the downstream bucks' UVLO (TPS563252 ≈ 3.3 V, SN6507 2.67 V) and doesn't trip the LP3470 or cause a WWDT reset.
- **Line step:** 44 ↔ 57 V.
- **Response vs. loop data:** the ringing frequency and damping should match the phase margin from §6.5.

### 6.9 Faults

- **Output short:** hold it, then release. Check for hiccup or foldback, clean recovery, and the SWO peak during the short.
- **Hot-plug:** about 100 plug-in cycles on a real switch.
- **Bench header:** run with the 12 V bench supply on J6 and PoE connected together. With the rail held above setpoint, the flyback should idle safely and hand over cleanly when either source is removed (arch §3 *Notes*).

### 6.10 Thermal (room ambient)

- **Soak:** at 57 V and at 37 V with full load, inside the closed enclosure, about 2 h until temperatures stop rising.
- **Thermocouples:** Si3402 (check the thermal vias), T2, D4, D1, output capacitor C57.
- **Extrapolate** to the worst-case summer garage temperature; the chamber run is §15.

### 6.11 System and compatibility

- **PSEs:** the actual UPS-backed switch plus one or two others and a midspan, in both Mode A and Mode B. Confirm the switch reports Class 2.
- **Noise on the data link:** iperf at full load while reading the KSZ8081's error counters (§8).
- **Common-mode noise:** clamp-on current probe on the cable, as a rough emissions check.

---

## 7. MCU, clocks, debug and memory

| Test | How | Pass |
|---|---|---|
| SWD | Connect through J3, read the IDs, flash a test image | Connects at the default clock; `RESET_N` from the probe resets the MCU |
| 24 MHz crystal (review K1, arch §4) | Route the 24 MHz clock to CLKOUT (P2_2, TP20), or measure the 50 MHz at the PHY side of R26. Use a counter with a ≤ 1 ppm reference | 25 °C: within ± 25 ppm of nominal. Over −30 … +70 °C (§15): within ± 45 ppm, which keeps the 50 MHz RMII clock inside the KSZ8081's ± 50 ppm. If 25 °C is off by more than ± 15 ppm, trim C1/C2 (8.2 or 12 pF) |
| 32.768 kHz oscillator | Route the 32 kHz clock to CLKOUT. Start-up time at room temperature and at −30 °C, at the low-power gain setting and at gain 01, with VDD_BAT at 1.8 V and at 3.1 V | Starts every time in < 1 s at both settings. RTC drift over 24 h < 2 s at room temperature (± 20 ppm) |
| USB ROM ISP | Short TP19 (ISP_N) to GND, power from J6, reset, and connect USB to J8 | Enumerates as the NXP ROM ISP device in High-Speed mode; `blhost get-property` answers |
| USB VBUS | VBUS present, board unpowered | No current into P3V3 from VBUS; the board stays off |
| QSPI (U11) | Read the JEDEC ID and SFDP; write, read back and erase a sector in 1-1-1 and 1-4-4 modes | ID matches the S25FL064L datasheet; data intact; `#RESET/SIO3` held high by R47 when idle |
| SE051 (U10) | I²C at 400 kHz and 1 MHz: read the version, generate a key, sign, verify. Soft reset over T=1 | All operations pass. The bus recovers after a soft reset without a power cycle (arch §5) |
| Debug UART (review X2-1) | J4 at 115200 | Console works. With the board unpowered and the cable fitted: measure P3V3 and record (back-power check) |

---

## 8. Ethernet

| Test | How | Pass |
|---|---|---|
| PHY clock mode (arch §4) | Firmware writes Reg 1Fh bit 7 after every PHY reset. Read it back after power-up, after a soft reset (Reg 0h.15) and after a WWDT reset | Bit 7 set every time before the MAC is enabled |
| Straps | Read the PHY registers | PHY address 1, RMII mode, auto-negotiation on, 100 Mbit advertised |
| Link | 100BASE-TX full duplex to the PSE switch, and to a non-PoE switch through a midspan | Link in < 3 s; auto-MDIX works with a crossover cable |
| Throughput | iperf both directions for 10 min, with PoE and the field supply at full load | ≥ 90 Mbit/s; KSZ8081 receive-error counter does not increase |
| Cable diagnostics | LinkMD on an open and a shorted cable | Reports the fault and an approximate distance |
| Controlled impedance (pcb-stackup §3) | Read JLCPCB's impedance test report for the order: 50 Ω SE, 90 Ω and 100 Ω differential | Every class within the ordered tolerance. Stackup on the report is JLC06161H-2116A |

---

## 9. Field supply

### 9.1 SN6507 push-pull (U15, T1)

| Test | How | Pass |
|---|---|---|
| Enable (arch §3 *Field supply enable*) | `P24V_FIELD_EN` (TP50) low, high, low; also hold the MCU in reset | Rail off in reset and at boot; on within ≈ 20 ms of EN (≈ 18 ms soft-start); D22 follows |
| Unloaded rail (arch §3) | Open terminal, RS-485 idle, 12 V rail at its high end (PoE 57 V). TP33 and J1-1 | `P24V0_FIELD` ≤ 28 V; terminal ≤ 30 V. If not, add the Zener clamp or a small preload |
| Load line | 0, 10, 50 and 100 % of 3 W (125 mA) on `P24V0_FIELD` (bypassing the eFuse) | 22.5–26 V across the range, inside IEC 61131-2 19.2–30 V |
| Switch nodes | SW1/SW2 at T1 pins 1/3, rectifier anodes | Break-before-make visible; ringing damped by the RC snubbers; peak < 36 V (SN6507 rating) |
| T1 temperature (review C2-2 in the 2026-10-04 review) | Full load, 1 MHz, closed enclosure | T1 rise < 40 K |
| Current limit | Short `P24V0_FIELD` through the e-load in CR mode | Primary current limit ≈ 0.32 A typ. (0.23–0.49 A); the logic side stays up; recovers when the short is removed |
| Common-mode noise | Clamp-on probe on the field cable with the supply running | Record; compare with and without C92 if it is ever in doubt |

### 9.2 Terminal eFuse (TPS26625, U19)

These are the bench tests in arch §15.

| Test | How | Pass |
|---|---|---|
| Current limit | Ramp the load on J1-1/J1-2 | Limits at 60–73 mA (66 mA nominal) |
| UVLO | Ramp `P24V0_FIELD` from a lab supply (SN6507 disabled) | On at ≈ 18.3 V, off at ≈ 16.8 V |
| Start into 1000 µF | With and without ≈ 40 mA of resistive load | Terminal reaches 24 V in ≤ 0.7 s; no fault retry; RS-485 stays up |
| Dead short | Short J1-1 to J1-2, warm and cold | Cycles on the ≈ 2.2 s timer with 512 ms retry; U19 case below ≈ 100 °C at 23 °C ambient; RS-485 stays up |
| Reverse voltage | Apply −24 V to the terminal from a current-limited supply | No damage; output recovers when it is removed |
| OVP decision | From the unloaded rail measurement in §9.1 | Confirms OVP can stay disabled (arch §3) |

### 9.3 RS-485 5 V buck (LMR51420, U17)

| Test | How | Pass |
|---|---|---|
| Regulation | TP29/TP31; RS-485 idle and transmitting into 54 Ω | 4.82–5.14 V |
| UVLO | Ramp `P24V0_FIELD` from a lab supply | On at ≈ 13.5 V, off at ≈ 11.9 V |
| Loop gain | Inject across R80 (49.9 Ω): TP29 to TP28, ground TP32. Measure under load, because the PFM variant skips cycles at light load | Phase margin ≥ 45°, gain margin ≥ 10 dB. If it fails, fit C78 (feed-forward) and remeasure |
| Switch node | TP30 (a deliberate measurement point, review T3-1) | Clean switching; no ringing beyond the SW rating |

---

## 10. Digital inputs (ISO1211 ×3)

Lab supply on DIn+/DIn− for each channel, with the field supply off so only the lab supply drives the input.

| Test | How | Pass |
|---|---|---|
| Thresholds | Sweep 0 → 30 V → 0 V | Turns on at ≤ 10.95 V, off at ≥ 8.7 V, hysteresis 1–1.2 V (IEC 61131-2 Type 3) |
| Current limit | Current at 11, 24 and 30 V | 2.2–2.47 mA above threshold |
| Reverse polarity | −30 V | Reads off, no damage |
| Enable | `DI_EN` (TP42) low | OUT reads 0 through the 2.2 kΩ pull-down |
| With the on-board supply | +24V FLD → contact → DIn+, DIn− → 0V FLD | Logic-side LED and GPIO follow the contact |
| Bounce | Real reed switch, door vibration simulated | Firmware debounce (~10 ms) gives one transition per operation |
| Validity | Turn the field supply off and on | Inputs are reported invalid while it is off and for ≥ 1 s after it is enabled (arch §3, §10) |

---

## 11. Digital outputs and fault architecture

### 11.1 Drive

| Test | How | Pass |
|---|---|---|
| LED current | Voltage across R62/R96 with the output on | 7.8–10.5 mA |
| Contact resistance | 10 mA through the closed contact | 11–16 Ω (the series R and the PPTC dominate) |
| Off leakage | 30 V DC across the open contact | < 1 µA |

### 11.2 Output protection

These are the bench tests in arch §15.

| Test | How | Pass |
|---|---|---|
| Short across a stiff supply | Output closed across a 24 V and a 30 V / 3 A lab supply, warm (+55 °C) and cold (−20 °C). Scope the current | Peak < 3 A; PPTC trips in < 100 ms; the resistor, PPTC and AQY212GS survive and recover |
| Sustained overload just under trip | Hold a load just below the trip current | Resistor temperature stays within its rating, or the PPTC trips first because it shares copper with the resistor |
| AC rating (review E1-1) | Only if an AC rating is kept: AC at the decided rating | TVS D18/D19 do not conduct (no heating); PPTC within its peak-to-peak V_max |

### 11.3 Every reset opens the outputs (arch §8)

With an output commanded on and an ohmmeter (or the opener input) on the contact, trigger each reset in turn:

- Power cycle, PoE and J6.
- Brown-out: ramp P3V3 below 2.93 V.
- WWDT: stop feeding.
- Lockup and hard fault: test firmware.
- Software reset.
- SWD reset.
- ROM ISP entry.

| Test | Pass |
|---|---|
| Each reset type | Contact opens; LED off; it stays open through boot until firmware arms it |
| WWDT timing | Output opens within the configured timeout (~1 s) after the induced hang |
| Debug halt (arch §15) | Record whether the WWDT counter runs or is frozen while halted at a breakpoint, with an output on |
| Re-arm policy | After 3 consecutive abnormal resets the outputs stay disarmed and the fault is reported; a power cycle clears it |

---

## 12. RS-485

| Test | How | Pass |
|---|---|---|
| Communication | Modbus RTU to the XY-MD02 at 9600 baud, 1 h | No CRC errors |
| Direction control | Scope DE (TP48) against TXD (TP49) | DE rises before the first start bit and falls after the last stop bit, from LPUART hardware RTS |
| Termination | J5 on and off; measure A–B resistance unpowered | ≈ 120 Ω with J5 on |
| Idle bus (review Q2-1) | Bus idle between master frames, terminated at both ends; capture the XY-MD02's reaction and the A–B differential | No framing errors or spurious replies at the sensor. If there are, fit the bias resistors (Q2-1) |
| Receiver disabled (review X3-1) | `RS485_RE_N` high | `RS485_RXD` held high (pull-up or firmware pull-up), and Q7/D13 off |
| Field supply off | Disable the field supply | Transceiver bus side is high-impedance; bus not loaded |

---

## 13. RTC and retained RAM backup (arch §3)

| Test | How | Pass |
|---|---|---|
| Charge | Empty C9, power the board, log the TP36 voltage | Reaches ≈ 3.0 V; record the time constant |
| Holdup | After ≥ 24 h powered, remove all power for 24 h; then check the retained-RAM CRC and the RTC against NTP | CRC good; RTC error < 2 s. If it fails, repeat for 8 h, the worst-case requirement |
| Low-voltage behaviour | Discharge C9 to 1.8 V, then 1.6 V (below the 1.71 V minimum); power up | At 1.8 V the data is retained; below 1.71 V firmware detects the CRC failure and treats the time as unknown |

---

## 14. Thermal, closed enclosure

- **Worst case:**
  - PoE at 37 V.
  - Field supply at 3 W.
  - Both outputs on.
  - RS-485 transmitting at 10 % duty.
  - Ethernet iperf.
  - MCU at 150 MHz.
- **Soak** in the closed enclosure, about 2 h, until temperatures stop rising.
- **Thermocouples:** U4, T2, D4, D1, C57, U15, T1, U19, U17, U1, R52/R53, the inside air.
- **Pass:** extrapolated to 35 °C garage air (≈ 55 °C inside), every part stays ≥ 10 K below its rating. The enclosure rise matches the 10–17 K estimate (arch §10).

---

## 15. Climate chamber

### 15.1 Temperatures

The box is sealed and runs 10–17 K above the garage air.

- **Cold:** winter cold start, board at garage temperature (about −25 °C).
- **Hot:** summer garage (35–40 °C) plus self-heating, about 55 °C around the parts.
- **Setpoints:** −30, −10, +25, +55 and +70 °C. The −30 and +70 °C points are margin.
- Run most tests on the **open board** at those board temperatures: it settles faster and the probe points are reachable.
- Then do one run with the **board in the closed enclosure at maximum garage temperature** to confirm the assumed rise.
- Dwell until readings stop drifting: about 20–30 min open, longer in the enclosure.
- Log a thermocouple on T2 and one on the Si3402.

### 15.2 What to measure at each temperature

| Test | Why it changes with temperature |
|---|---|
| **Flyback loop gain** at 37 V/100 % and 57 V/10 % (§6.5) | The opto's CTR falls when cold and when hot, which moves crossover. The ceramics lose capacitance at the extremes. Main reason for the chamber. |
| **SWO peak** at 57 V, full load (§6.4, §6.6) | TVS breakdown voltage rises with temperature (about +0.1 %/K), so the clamp is weakest when hot. Smallest 100 V margin at +70 °C. |
| **SWO clamp conduction** at 37 V and 57 V, full load, −30 °C (§6.6, review R2-1) | The clamp's breakdown voltage falls when cold and approaches the reflected voltage. |
| **Cold start** at 37 V, full load, after a cold soak with power off; repeat about 10 times | C50 is an ordinary aluminium electrolytic whose ESR rises a lot when cold. Worst case for hot-swap and switcher start-up. Also covers the 3V3 buck, DCDC, supervisor and crystal start-up. |
| **UVLO, detection, class current** (§6.1) | Must stay inside the 802.3af limits. A PSE rejecting the board in winter is a nasty field failure. |
| **Load step** 10 ↔ 90 % (§6.8) | Confirms the phase margin, and that the dip stays clear of the downstream UVLO and supervisor thresholds. |
| **Vout, efficiency** at 10, 50 and 100 % (§6.3) | Drift and losses. Losses rise when hot, which feeds back into the thermal budget. |
| **24 MHz frequency** (§7) | Crystal ±10 ppm over temperature on top of the 25 °C tolerance; sets the RMII ppm budget. |
| **32 kHz start-up** at −30 °C (§7) | Oscillator margin is lowest cold. |
| **Field rail unloaded and at full load** (§9.1) | Rectifier and leakage behaviour; the terminal must stay ≤ 30 V. |
| **eFuse dead short** at +55 °C (§9.2) | Least thermal margin to shutdown. |
| **DI thresholds** at −30 and +70 °C (§10) | Threshold drift. |
| **Output short** warm and cold (§11.2) | PPTC trip time changes strongly with temperature. |
| **iperf + PHY error counters** (§8) | Link margin and noise coupling at temperature. |
| **RS-485 communication** (§12) | Transceiver and 5 V buck over temperature. |

**Pass:** the same criteria as at room temperature, with phase margin ≥ 45° at every temperature. If a looser limit is wanted at the extremes, decide it up front (e.g. ≥ 40° at −30 °C only), not after seeing the data.

### 15.3 Temperature cycling

- **About 50 cycles between −25 and +60 °C**, with power cycled at each end.
- At every cycle, check that the board starts, Vout is within limits, Ethernet links and the inputs read correctly.
- This finds solder joints and marginal starts. It matters for the heavy parts (T2, C57, C9, the terminal headers).

### 15.4 Condensation (if the chamber controls humidity)

- Cold soak, then a quick change to warm, humid air, with the board powered.
- Realistic for a garage, and it tests whether the conformal coat protects the barriers and the high-impedance nodes: the eFuse dVdT and UVLO nodes, and the LMR51420 UVLO divider.
- Repeat the 1500 Vrms hipot afterwards (§4.3).

### 15.5 Practical notes

- **Bode 100:** keep the injection transformer outside the chamber and run twisted leads through the port to the injection resistor. Cable capacitance doesn't matter at loop frequencies of a few kHz. Recheck the calibration once the cables are in place.
- **Probes:** only the leads go inside. Most probe specs stop at about +50 °C, so keep scope probe heads outside or use the chamber feed-through.
- **Automation:** script the sweep so it runs overnight. The Bode 100 can be scripted through OmicronLab's automation interface, and the chamber and lab supply over SCPI or serial. Each step: set temperature → wait until it settles → loop-gain sweep → static measurements → log.

---

## 16. Measurements outside the box

These are open items in arch §15. The output stage and its rating depend on them.

| Measurement | How | Decides |
|---|---|---|
| Magic 600 terminals 18/19 | Open-circuit voltage (DC or AC, with polarity), short-circuit current, and whether it is SELV (not mains-referenced). Hold a contact closed for 30 s and watch what the operator does | TVS standoff (D18/D19); the output rating (review E1-1, Q-1); the isolation assumption (arch §11); the WWDT timeout |
| Garage and house earth bonding | Continuity of PE between the buildings | Surge assumptions (arch §11) |
| Installed shield | S/FTP shield bonded at both ends, or UTP | Margin (arch §11 *Shields*) |

---

## 17. Traceability

| Source | Test |
|---|---|
| Review R2-1 (SWO clamp, option a) | §4.1 D1 screening, §6.4, §6.6, §15.2 |
| Review W2-1 (VDD_BAT sequencing) | §5.2 |
| Review Q-4 (3V3 buck start threshold) | §5.1 |
| Review Q2-1 (RS-485 bias) | §12 idle bus |
| Review X3-1 (RS485_RXD floating) | §12 receiver disabled |
| Review X2-1 (J4 back-powering) | §7 debug UART |
| Review E1-1, Q-1 (output AC rating) | §11.2, §16 |
| Review T3-1 (switch-node TPs) | §5.2 DCDC, §9.3 switch node |
| Review C4-1 (flyback vs EVB, output filter) | §6.3, §6.5, §6.7 |
| Review K1 (crystal load, 2026-10-04) | §7, §15.2 |
| Arch §3 field enable, unloaded rail, eFuse | §9.1, §9.2 |
| Arch §3 RTC holdup | §13 |
| Arch §3 bench header J6 | §3, §6.9 |
| Arch §4 PHY 50 MHz mode | §8 |
| Arch §4 USB ISP, SWD | §7 |
| Arch §6 inputs | §10 |
| Arch §7 output protection | §11.1, §11.2 |
| Arch §8 fault architecture, WWDT, re-arm | §11.3 |
| Arch §10 thermal | §14 |
| Arch §11 isolation requirements | §4.3, §15.4 |
| Arch §13 LP3470 / PHY brown-out window | §5.2 |
| Arch §15 open items (opener terminals, earths, eFuse, output protection, WWDT under halt) | §9.2, §11.2, §11.3, §16 |
| pcb-stackup §3 impedance classes | §8 controlled impedance |
| security-requirements §4 hardware tests (fuses, debug lock, QSPI dump) | Board B, after provisioning; see that document |

---

## Results log

| Date | Board | Section | Conditions | Result | Pass/Fail | Notes |
|---|---|---|---|---|---|---|
| | | | | | | |
