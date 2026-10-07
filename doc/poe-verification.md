# PoE flyback — verification plan

Scope: PD front end + Si3402-B isolated flyback (U4, T2 FA2672-ALD, D4 PDS5100, VO618A opto) → 12 V logic rail.
Reference design: Si3402BISO-EVB, 12 V configuration.
Instruments: Bode 100 (+ injection transformer), scope with differential probe, lab supplies, electronic load, climate chamber.

## Safety and setup (all powered tests)

- Use a 48–57 V lab supply with a current limit of about 0.5 A, applied directly to VPOS/VNEG (or through the pairs).
- Use a differential probe on the primary side. Never connect scope grounds on both sides of the barrier.
- A bare flyback needs at least 250 mW of load to avoid switcher pulsing. Fit a load resistor for tests without the rest of the board.

---

## Open items found in schematic review (fix before layout)

- [ ] **R5 = 48.7 Ω sets Class 3, not Class 2.** Si3402-B datasheet Table 7: Class 2 = 75.0 Ω, Class 3 = 48.7 Ω. The architecture doc says Class 2.
- [ ] **Secondary feedback looks unfinished.** No TLV431 and no output divider found in `ethernet_poe.kicad_sch`. EVB 12 V: higher-voltage TLV431 (e.g. TLV431ASNT1G), divider 88.7k/10.2k, compensation 10 nF/15 nF. (Only placed parts were checked, not nets.)
- [ ] **Output filter differs from the EVB.** 330 µF OSCON + L2 (1 µH) vs the EVB's low-ESR aluminium cap. The OSCON's much lower ESR moves the ESR zero up, so the EVB compensation won't carry over. Skyworks warns against substitutions in the filter/feedback path. Decide whether feedback senses before or after L2.
- [ ] **Add test hooks:**
  - a 0 Ω footprint (swap for 10 Ω) where the output feeds both the opto LED resistor and the divider, for loop injection
  - test points on SWO, VPOS, VNEG, HSO, and 12 V with GND next to it
  - a pad for a load resistor
- [x] **Datasheet mismatch.** The EP13 datasheet was the wrong one; the EP10 FA2672 is covered by `datasheets/power/poe/FA2671_FA2672_FA2732_Coilcraft.pdf` (Coilcraft Doc 560: 1:0.4, Ipk 1.3 A).

---

## 0. Unpowered checks

- **Transformer (Bode 100, impedance mode):**
  - primary inductance (Lp)
  - leakage inductance with the secondary shorted
  - primary-to-secondary capacitance, which also feeds the surge/ground-potential-rise reasoning

  Compare with the datasheet.
- **Isolation:** AC hipot at **1500 Vrms, 50 Hz, 60 s** across barrier 1: all cable/PoE leads tied together against all other conductors, including the field terminals. This is the requirement in arch §11 *Isolation requirements* (IEEE 802.3 PD isolation). The barrier caps C90/C91 (KEMET 1 nF / 3 kV DC MLCC) let through ≈ 0.9 mA at 1500 Vrms, so set the trip limit around 3 mA. They are DC-rated parts, not AC-qualified, so this first hipot is also their AC-withstand check. Pass: no breakdown or flash-over, and leakage within the expected cap current.

## 1. PD signature (low voltage, switcher off)

| Test | How | Pass |
|---|---|---|
| Detection | Two points between 2.7 and 10 V; ΔV/ΔI | 23.75–26.25 kΩ |
| Classification | 15.5 V and 20.5 V | 17–20 mA (Class 2) |
| UVLO | Ramp slowly up, then down | On at ≤42 V (typ 37), off at ≥30 V (typ 32), no chatter |
| Inrush | Current probe at turn-on | About 140 mA limit, then the switcher starts |

## 2. Startup and shutdown

- **Conditions:** Vin 37, 48 and 57 V, into no load, full load (about 0.36 A at 12 V) and full load plus the real downstream capacitance.
- **Pass:** 12 V rises monotonically with little overshoot, and the downstream bucks don't cycle.
- **Brown-out:** slow ramp down, then back up. Check for a clean off and a clean restart.

## 3. Steady state

- **Grid:** Vin 37, 44, 48, 57 V × load 0, 10, 50, 100 %, plus about 150 % overload.
- **Record:** Vout (regulation), input current, efficiency. Target about 85 %, which is what the 0.64 W loss budget assumes.
- **Ripple:** at the output, before and after L2, with a tip-and-barrel probe connection, 20 MHz bandwidth limit on and off.

## 4. Switching stress (worst case: 57 V, full load, output short, startup)

- **SWO peak:** absolute maximum is 100 V, and the D2 + SMAJ30A clamp sits on top of a 57 V input. Target ≤ about 90 V. This is the margin most likely to be too thin.
- **Clamp TVS:** power and temperature.
- **D4 (PDS5100):** reverse voltage spike against its 100 V rating.
- **Snubbers:** dissipation in R9 (secondary snubber) and in the clamp.
- **Conduction mode:** note where the converter moves between CCM and DCM (relevant to the loop measurement).

## 5. Loop gain (Bode 100 + injection transformer)

- **Where to inject:** at the 10 Ω injection resistor, placed so both the opto "fast lane" and the TLV431 divider are inside the loop. If only the divider is inside, the reading looks good but is wrong.
- **Settings:** start at 20–50 mV injection, check the result doesn't change when you vary the level, and use a shaped level profile if the low end gets noisy.
- **Test grid:** 37, 48, 57 V × 10, 50, 100 % load.
- **Pass:** phase margin ≥45°, gain margin ≥10 dB, crossover well below about 1/5 of the right-half-plane zero at 37 V and full load.
- **Opto spread:** if you can, test two opto parts or boards, because the VO618A bins vary.
- **Temperature:** see section 11.

## 6. Output impedance and how it interacts with downstream converters

- **Zout:** Bode 100 with a current injector (Picotest J2111A, or a DIY MOSFET plus resistor). Look for peaking, especially the L2/downstream-ceramic resonance.
- **Zin of the loads:** measure or estimate the input impedance of the 3V3 buck and the SN6507.
- **Check (Middlebrook's criterion):** the flyback's Zout must stay well below each converter's input impedance, which behaves like a negative resistance.

## 7. Transients

- **Load step:** 10 % to 90 % and back with a MOSFET switch.
  - **Pass:** the 12 V dip stays clear of the downstream bucks' UVLO and doesn't trip the 3V3 supervisor (LP3470) or cause a WWDT reset.
- **Line step:** 44 ↔ 57 V.
- **Response vs. loop data:** the ringing frequency and damping should match the phase margin from section 5.

## 8. Faults

- **Output short:** hold it, then release. Check for hiccup or foldback, clean recovery, and the SWO peak during the short.
- **Hot-plug:** about 100 plug-in cycles on a real switch.
- **Bench header:** run with the 12 V bench supply and PoE connected together. With the rail held above setpoint, the flyback should idle safely and hand over cleanly when either source is removed.

## 9. Thermal (room ambient)

- **Soak:** at 57 V and at 37 V with full load, inside the closed enclosure, about 2 h until temperatures stop rising.
- **Thermocouples:** Si3402 (check the thermal vias), T2, D4, clamp TVS, OSCON.
- **Extrapolate:** scale the results to the worst-case summer temperature in the garage (see section 11 for the chamber run).

## 10. System and compatibility

- **PSEs:** test the actual UPS-backed switch plus one or two others and a midspan, using both Mode A and Mode B. Confirm the switch reports Class 2.
- **Noise on the data link:** run iperf at full load and read the KSZ8081's error counters.
- **Common-mode noise:** clamp-on current probe on the cable, as a rough emissions check.

---

## 11. Temperature (climate chamber)

### Temperatures to test

The box is sealed and runs 10–17 K above the garage air.

- **Cold:** winter cold start, board at garage temperature (about −25 °C).
- **Hot:** summer garage (35–40 °C) plus self-heating, about 55 °C around the parts.

**Setpoints: −30, −10, +25, +55, +70 °C.** The −30 and +70 points are margin.

- Run most tests on the **open board** at those board temperatures: it settles faster and you can reach the probe points.
- Then do one run with the **board in the closed enclosure at maximum garage temperature** to confirm the assumed rise.
- Dwell until readings stop drifting (about 20–30 min open, longer in the enclosure).
- Log a thermocouple on T2 and one on the Si3402.

### What to measure at each temperature

| Test | Why it changes with temperature |
|---|---|
| **Loop gain** at 37 V/100 % and 57 V/10 % | The opto's CTR falls when cold and when hot, which moves crossover. The ceramics lose capacitance at the extremes. Main reason for the chamber. |
| **SWO peak** at 57 V, full load | TVS breakdown voltage rises with temperature (about +0.1 %/K), so the clamp is weakest when hot. Smallest 100 V margin at +70 °C. |
| **Cold start** at 37 V, full load, after a cold soak with power off | C50 is an ordinary aluminium electrolytic whose ESR rises a lot when cold. Worst case for hot-swap and switcher startup. Repeat about 10 times. |
| **UVLO, detection, class current** | Must stay inside the 802.3af limits. A PSE rejecting the board in winter is a nasty field failure. |
| **Load step** 10↔90 % | Confirms the phase margin, and that the dip stays clear of the downstream UVLO and supervisor thresholds. |
| **Vout, efficiency** at 10, 50, 100 % | Drift and losses. Losses rise when hot, which feeds back into the thermal budget. |
| **iperf + PHY error counters** (system test) | Link margin and noise coupling at temperature. |

**Pass:** same criteria as at room temperature, with phase margin ≥45° at every temperature. If you want a looser limit at the extremes, decide it up front (e.g. ≥40° at −30 °C only), not after you see the data.

### Temperature cycling

- **About 50 cycles between −25 and +60 °C**, with power cycled at each end.
- At every cycle, check that it starts and that Vout is within limits.
- Finds solder joints and marginal starts. It matters for the heavy parts (T2, OSCON).

### Condensation (if the chamber controls humidity)

Cold soak, then a quick change to warm, humid air, with the board powered. Realistic for a garage, and it tests whether the conformal coat protects the barriers.

### Practical notes

- **Bode 100:** keep the injection transformer outside the chamber and run twisted leads through the port to the injection resistor. Cable capacitance doesn't matter at loop frequencies of a few kHz. Recheck the calibration once the cables are in place.
- **Probes:** only the leads go inside. Most probe specs stop at about +50 °C, so keep scope probe heads outside or use the chamber feed-through.
- **Automation:** script the sweep so it runs overnight. The Bode 100 can be scripted through OmicronLab's automation interface, and the chamber and lab supply over SCPI or serial. Each step: set temperature → wait until it settles → loop-gain sweep → static measurements → log.

---

## Results log

| Date | Board | Section | Conditions | Result | Pass/Fail | Notes |
|---|---|---|---|---|---|---|
| | | | | | | |
