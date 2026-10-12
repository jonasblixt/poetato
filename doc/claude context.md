# PoEtato — hardware context (condensed)

PoE-powered PLC-like controller for garage: controls Crawford/Normstahl Magic 600 door opener, reads sensors, Home Assistant over Ethernet. Educational; industrial-grade I/O is the point.

## Documentation
- All design docs (decisions, requirements, research write-ups) live in the git repo under `doc/` as Markdown, not in the Claude project. New or updated docs go there.
- Docs: `doc/hardware-architecture.md`, `doc/verification-plan.md` (board verification plan, includes the PoE flyback tests), `doc/security-requirements.md`, `doc/mqtt-broker.md`, this file.

## Summary
- MCU (decided 2026-09-29): **MCXN247VKLT** (MCX N24, 1× Cortex-M33 150 MHz, HLQFP100 exposed pad, 2 MB dual-bank flash, 512 KB SRAM, EdgeLock Secure Enclave Core Profile, TrustZone, RMII Ethernet, HS USB w/ PHY, −40…+125 °C). In mass production (orderable from Mouser, 2026-09). Not yet PSA certified (accepted risk, hobby project). Pin-compatible certified fallback: **MCXN547VKLT**. Replaces i.MX RT1021. Details: `doc/security-requirements.md` §6.
- PHY: KSZ8081RNB, RMII. MCX N HLQFP100: RMII only; MDC/MDIO on P1_2/P1_3 (P1_20/21 not bonded, unlike FRDM-MCXN947).
- Power: PoE only, 802.3af Type 1, Class 2 (~4.1 W of 12.95 W). No mains in box.
- I/O: 3 isolated DI (ISO1211 ×3, each channel isolated separately), 2 PhotoMOS DO (AQY212GS), 1 isolated RS-485 (ISO3082 class).
- Field supply: 24 V isolated, 3 W.
- Security: MCX N ROM secure boot → **punchboot** (to be ported to MCX N; MCUboot used only initially to explore) → Zephyr; NXP SE051C2 on I²C (kept for v1). CRA: default category (generic DIN-rail PoE I/O controller).
- FW: Zephyr — Modbus RTU master, RTU↔TCP gateway, MQTT w/ HA discovery. Existing code in `app/`.
- Enclosure: Italtronic 35.0807000.BL, 8M DIN, 142×90×32.2 mm. (Layout/mechanical placement is out of scope for these docs.)

## Principles
- No mains inside; mains loads external.
- Box is convenience actuator, not safety. Opener's photocell/force limit are the safety. On fault, box must disappear cleanly.
- Strictly parallel to wall button and remote; never interrupts them.
- Every value carries validity flag (range, field-supply state, commanded output state).
- Real isolation: each barrier has floating supply; no shared ground across barrier.

## Isolation domains
1. Cable/PSE: RJ45, magjack CTs, PD bridge, Si3402-B primary.
2. Logic: MCXN247, PHY, QSPI flash, SE051, supervisor, output LED drive.
3. Field 24 V: RS-485 field side, 5 V buck, field/sensor supply +24V FLD (ref field 0 V).
4. Inputs: each ISO1211 field side floating, referenced to its own DIn−.
5. Outputs: each AQY212GS pair floating (dry contacts).

## Power
PSE 48 V (UPS-backed) → PD bridge/class (Class 2 resistor) → Si3402-B isolated flyback → 12 V logic rail:
- buck 3V3: MCU, PHY, flash, SE051 (MCU ~20 mA @150 MHz), OptoMOS LEDs (low-side NTK3134N per channel).
- SN6507 (not SN6505B: 2.25–5.5 V only, can't run from 12 V; changed 2026-10-03) + push-pull transformer ≈1:2 (candidate Würth 750319693, 1:2.29) → 24 V field 3 W: digital inputs (via contacts), buck 5V→ISO3082 (LMR51420XDDCR, 36 V, 500 kHz PFM, replaced TPS54202H 2026-10-07: 28 V rating too close to the ≈ 27.5 V light-load rail; UVLO 13.5 V via 1 MΩ/100 kΩ), +24V FLD terminal via TPS26625 eFuse
- Field supply switched by FW (decided 2026-10-06): P24V_FIELD_EN (P3_16) → SN6507 EN, 2.2 kΩ pull-down → field rail (+24V FLD, inputs, RS-485 5 V) off in reset/boot; FW enables when the app runs; inputs/RS-485 valid only once enabled and settled.
- Field output protection (decided 2026-10-07): TPS26625 eFuse (auto-retry, output reverse-polarity) between P24V0_FIELD and the +24V FLD terminal; RS-485 buck stays on the unprotected rail. R_ILIM 100 kΩ → 66 mA, ≈ 60–73 mA (terminal rated 50 mA incl. inputs; stays below the SN6507 limit ≈ 92–106 mA min on the 24 V side, so RS-485 stays up in a short); UVLO 200 kΩ / 14.0 kΩ (0603 thick film, low impedance for humidity) → 18.3 V rising / 16.8 V falling; OVP tied to RTN (disabled; option 6.19 kΩ + 7.87 kΩ → 32.6 V); C_dVdT 1 µF → 0.49 s ramp, handles 1000 µF load; C_IN/C_OUT 1 µF 100 V; output clamp D24 SMAJ28CA (D18/D19 on the outputs are SMAJ33CA); SHDN open; FLT not connected (no fault indication); RTN island not tied to GND. FW waits ≥ 1 s after P24V_FIELD_EN before inputs are valid. Dead short: ≈ 1.6 W, Tj ≈ 127 °C at 55 °C ambient, cycles on the ≈ 2.2 s timer. Full load fits the 1.5 W sensor allocation in the 4.07 W budget. Details: `doc/hardware-architecture.md` §3.
- 12 V secondary chosen so field converter is 1:2 not 1:5.
- Field rail unregulated (open-loop push-pull): ≈ 27–28 V unloaded (no preload, removed 2026-10-08; rail sits at the rectified peak), 22.5–23.5 V at 3 W; the inputs load only when closed; inside IEC 61131-2 19.2–30 V, no post-regulator. Settled: fixed duty (DC open), 1 MHz, R_ILIM 75 kΩ, C_SS 4.7 µF, RC snubbers, L5 choke input. Bench: open-circuit terminal voltage ≤ 30 V (Zener or small preload if not).
- Budget: logic 1.05 W, digital inputs 0.18 (3 closed), RS-485 0.15, sensor supply 1.5, OptoMOS 0.05, iso conv loss 0.5, flyback loss 0.64 → 4.07 W (Class 2 limit 6.49 W).
- Heavy 24 V loads need own supply (documented limit).

## Boot / flash (MCX N247)
- ROM secure boot (ECDSA, RoT key hash in CMPA/fuses, debug authentication) → **punchboot** → Zephyr app (signed bpak, A/B, rollback). Intention: port punchboot to MCX N. MCUboot may be used first to explore the MCX N boot flow; not the target.
- punchboot port: verify with PKC (HW ECDSA) + ELS SHA; anti-rollback in OTP/CFPA monotonic counters; HS USB recovery via punchboot-tools (MCX N USB1 HS is NXP EHCI, same IP family as i.MX RT, so the existing USB driver is likely largely reusable, verify); UUID from MCX N unique ID.
- Internal 2 MB dual-bank flash: punchboot + A/B slots (one app slot per bank; bank swap/remap to be checked in RM). The i.MX FlexSPI remap problem is gone. External QSPI S25FL064L (8 MB) fitted as standard (decided 2026-10-06): filesystem for config, logs and data; never code, nothing secret (keys/credentials stay in SE051).
- HW crypto: ELS (AES/SHA/keystore), PKC (ECC/RSA), PUF, TRNG.
- USB1 HS is the recovery/ISP interface: pins 40/41 D+/D−; pin 42 USB1_VBUS directly to 5 V VBUS (only 5 V tolerant pin); pin 43 VSS_USB. N247 has no USB FS controller (USB0 pins 45/46 unused; VDD_USB still powered 3.3 V).
- HF crystal **24 MHz** (needed for HS USB ISP with factory fuses; also HS USB PLL): Epson TSX-3225 `X1E0000210048` (−40…+105 °C, ±10 + ±10 ppm, C_L 9 pF, ESR 40 Ω; C1/C2 10 pF). Its ±20 ppm leaves ≈ ±30 ppm of the KSZ8081 ±50 ppm RMII budget for pulling and aging; measure the frequency on the first board. RTC crystal Epson FC-135R `X1A0001410006` (6 pF, ≤ 50 kΩ, ±20 ppm; meets OSC32K low-power-mode limits, gain 01). Decided 2026-10-08. ISP boot pin reachable. USB1 HS is the only ROM ISP interface; no UART ISP header (decided 2026-10-04).
- Keep one board with lifecycle not advanced (open) for development.
- Zephyr: no MCXN247 SoC upstream yet (2026-09-29). Port = new SoC variant modeled on MCXN547 (single core, no NPU/PowerQuad/USB FS), HLQFP100 pinctrl. Early FW dev on FRDM-MCXN947.
- Order VKLT (VNLT replaced, PCN 202502004F01). Choose LDO vs DCDC core supply (UG10092 §3.2).

## Secure element (SE051C2HQ1/Z01XDZ)
- 3.3 V, I²C addr 0x48, up to 1 MHz, HX2QFN20 3×3 mm 0.4 pitch, ENA tied to 3V3 (always on), no reset pin in I²C mode (RST_N is ISO 7816, tied to GND), recovery by soft reset or board power cycle, −40…+105 °C (suffix 2).
- Dedicated I²C bus, 2.2 kΩ pull-ups.
- Purpose: private-key custody (generated on-die, never leaves) + trustworthy CSR/cert provisioning for mTLS. Replaces key in `app/src/tls_config/cert.h`. Identity = public cert; SE051 holds proving key.
- Does not protect firmware; that's ROM secure boot/punchboot. Without secure boot, SE051 is moot.
- Provisioning: keygen in SE → CSR → sign with offline local CA (subject derived from MCX N unique ID) → store cert in SE → mTLS to broker.
- SW: NXP Plug & Trust; nano-package `feature/zephyr-integration` branch; mbedTLS ALT hooks; AN13013.
- Secondary: broker/Modbus credentials, update signature verification.

## Digital inputs — ISO1211 ×3 (decided 2026-10-04)
- 3 channels, one single-channel ISO1211 (SOIC-8) each. Each input is isolated from logic and from the other inputs: own FGND, brought out as a `DIn+`/`DIn−` terminal pair. The field side is powered by the input current (no field supply pin).
- IEC 61131-2 Type 3, sinking: R_THR 1 kΩ MELF, R_SENSE 562 Ω → 2.25 mA typ (2.2–2.47 mA) current limit.
- Wiring with the on-board supply: +24V FLD → contact → DIn+; DIn− → 0V FLD. Silkscreen `+24V FLD` / `0V FLD` / `DIn+` / `DIn−`, never `COM`.
- Per channel: SMF36A TVS and 10 nF C0G C_IN from SENSE to FGND; SUB on a floating pour; OUT → GPIO (P3_13–P3_15) with 2.2 kΩ pull-down; shared `DI_EN` (P3_12); logic-side status LED via NTK3134N.
- No hardware debounce (10 µs): debounce ~10 ms in FW.
- No wire-break, field-supply or CRC diagnostics. A dead +24V FLD reads as all inputs open, so FW marks the inputs valid only while the field supply (`P24V_FIELD_EN`) is enabled and settled. End-of-line resistors stay a deferred option.
- Usage: door open reed, door closed reed, wall-button sense (no spare). Sensors are sealed reeds (low wetting need).

## Digital outputs — AQY212GS ×2
- PhotoMOS 60 V / 1 A AC/DC, true bidirectional dry contact (opener input polarity unknown); can drive small relay coil. **Output rating: ≤ 30 V AC/DC, ≤ 100 mA** (signal contact, not power output).
- Drive (as in schematic, 2026-10-04): 3V3 → 220 Ω (R62/R96) → AQY LED → NTK3134NT1G low-side (Q1/Q12) → GND (logic-level FET for 3.3 V gate drive). Gate = DO1_ON (P2_6) / DO2_ON (P2_7) with 2.2 kΩ pull-down. Plain GPIO, no PWM. Logic-side status LED (464 Ω) on the same FET shows the commanded state.
- LED current (3V3, not 5 V): ≈9.9 mA nominal, ≥7.8 mA worst case (3V3 3.21 V, V_F 1.5 V max), ≈10.5 mA high. AQY212GS IFon 1.1 typ / 3 max, recommended 5–30 mA. ≥2× typical for aging.
- Per channel (decided 2026-10-02): 10 Ω Vishay CRCW251210R0FKEGHP (2512 pulse-proof, 1.5 W at 70 °C; 2 W Bourns CRS2512 is fallback) + Bel 0ZCJ0016FF2E PPTC (1206, 0.16 A hold / 0.45 A trip, 48 V, 1.1–5 Ω) in series, PPTC next to resistor on shared copper, bidirectional TVS (standoff after measuring opener idle voltage), ferrite/CM choke, field-side status LED if possible.
- Design constraint: AQY212GS peak 3 A / 100 ms one shot → short must stay < 3 A and trip < 100 ms. Short across 24 V: 1.5–2.1 A (30 V: 1.9–2.6 A), trip ~20–40 ms average (datasheet guarantees only 0.3 s at 1 A), resistor pulse ≤ 44 W / 1–2 J. Sustained sub-trip overload sizes the resistor: 1.0 W at 60 °C, 2.0 W at 23 °C (0.45 A; over 1.5 W rating, accepted), 3.5 W at −20 °C (relies on resistor heat tripping the adjacent PPTC). 100 mA rating from hold derating (110 mA at 60 °C). Series path 11–16 Ω. Relay coil needs own flyback diode.
- Rejected: 22 Ω (short only ~1 A, slow trip; 4.5 W at trip current); 0ZCJ0035AF2E (needs ~2.8 A to trip in 100 ms, no margin to 3 A; 30 V only); resistor alone; PPTC alone (peak > 3 A). Open: bench-test short across 24/30 V, warm and cold.
- Accepted risk: shorted PhotoMOS = stuck button (opener tolerates).

## Fault architecture
- Decided 2026-09-30: **no external watchdog, no latch** (TPS3436 + 74AHC1G74 dropped). Job: when FW is not in control, outputs disappear. Cannot fix door state; only working FW can.
- Off-path = pin reset state. DO1_ON/DO2_ON hi-Z → 2.2 kΩ gate pull-down holds each FET off → outputs open. Every reset (LP3470 power-up/brown-out, WWDT, lockup, SW, SWD; WWDT drives RESET_b low, RM §32.5.2) → outputs open. LED anode on 3V3, so no back-powering when 3V3 down.
- No hardware interlock (decided 2026-10-04, single FET per channel; DO_EN rail gate and boot check removed). A GPIO stuck high or a shorted FET holds one output on = stuck button, same as an accepted shorted PhotoMOS.
- **WWDT only**: enabled early in punchboot, windowed, MOD[LOCK], timeout ~1 s (below any Magic 600 long-press behaviour). Warning IRQ logs missing task flag to retained RAM; reset cause recorded.
- Feed: all task flags set → one supervisor thread feeds WWDT → clear. Thread only, never timer ISR.
- Residual accepted: core hangs with output on AND WWDT fails → stuck button until PoE power-cycle; never door motion.
- Re-arm policy (replaces "never re-arm after WDT reset"): never pulse during boot; arm only when app up + reeds valid. Consecutive abnormal resets (WWDT/lockup/hard fault) counted in retained RAM, cleared after ~10 min clean run or power cycle. ≥3 → stay disarmed, report, re-arm by command/power cycle. Auto-correction = one pulse, verify reeds after travel time, no blind retry (toggle input).
- WDT = liveness only. "Alive but wrong" bounded by SW max on-time per channel with overrun flag over Modbus, plus opener's own safety.

## RS-485
- ISO3082 class, field side 5 V via buck from 24 V (not LDO; not ADM2587E — avoids second iso domain).
- 120 Ω termination jumper, fail-safe bias, TVS on A/B. LPUART hardware RTS for DE.
- Devices: XY-MD02 (SHT20) or own SHT45 satellite (datasheets in `datasheets/`). Mount on interior wall, away from door/motor.
- Derived: dew point. γ = ln(RH/100) + 17.62T/(243.12+T); Td = 243.12γ/(17.62−γ).
- Expansion (analog, 0–10 V): separate Modbus RTU slave nodes, not a bigger board.

## Terminals / enclosure
- 5.08 mm pluggable, Phoenix COMBICON MSTB 2,5 (decided 2026-10-06): headers MSTBA 2,5/..-G-5,08 (J1 1757349, J2 1757268) + matching MSTB 2,5/..-ST-5,08 plugs (order separately, in BOM). 16 positions in two blocks:
  - J1, 12-pos: +24V FLD, 0V FLD (also the sensor supply), DO1 A/B, DO2 A/B, DI1−/+, DI2−/+, DI3−/+.
  - J2, 4-pos: RS-485 A, B, 0V FLD, shield.
- Thermal: ~3.5–4 W inside, 10–17 K rise; sealed, no vents.

## Magic 600 interface
- External impulse input: potential-free momentary contact, terminals 18/19 (Magic 1000 uses 14/15). Toggles open→stop→close→stop.
- No status output → door state only from reeds.
- RTC backup (decided 2026-10-01): Eaton KW-5R5C334H-R 0.33 F supercap on VDD_BAT via BAS70 + 220 Ω, no coin cell; ≥ 8 h worst case. Port 5 runs at VDD_BAT (~3.1 V).
- Bench power (decided 2026-10-06): J6 2-pin 2.54 mm header directly on P12V0, no series diode (D4 blocks backfeed), no reverse-polarity protection.
- Opener motor on garage mains: control dies in power cut; monitoring survives (UPS PoE).

## Protection / surge
- ~2 m underground inter-building Ethernet; threat is ground potential rise. Verify garage/house earths bonded (PE).
- Run Ethernet alongside mains feed; S/FTP shield bonded both ends (installation requirement; UTP tolerated with less margin).
- On-board: Bob Smith (75 Ω per CT → 1000 pF/2 kV to chassis), SMAJ58A on 48 V after bridge. No PTC/fuse in PD path and no GDT (dropped 2026-10-05, judged unnecessary).
- Field wiring to opener is the larger exposure (TVS + PhotoMOS isolation).
- Isolation requirement (decided 2026-10-05): all circuits SELV/ES1, no safety insulation needed. Cable/PoE ↔ rest (incl. field terminals): 1500 Vrms 60 s (802.3), verified by AC hipot. Barrier caps: KEMET C1808C102KHRACTU 1 nF / 3 kV DC (C89–C92); Y2 not required since all circuits are SELV. Logic ↔ field/DI/DO: functional (weakest AQY212GS 1500 Vrms), 500 Vrms bench check. Assumes the opener input is SELV (to confirm).
- Isolation: no shared ground across barriers; cap 1 nF / 3 kV (C92) GND↔GND_FIELD at T1 for push-pull CM return; low inter-winding-C transformer; conformal coat.
- Shields (decided 2026-10-05): one SHIELD net = magjack shield + RS-485 shield (J2-4, bonded at box end only). SHIELD → GND via 1 nF / 3 kV (C89) ∥ 12 MΩ. No shield to GND_FIELD. UTP: SHIELD held by Y-cap + magjack Bob Smith, CM leaves via pairs; works, less margin. Optional functional-earth terminal / DIN-rail earth clip on SHIELD (recommended, not required).

## Key parts
MCXN247VKLT (fallback MCXN547VKLT) · Epson TSX-3225 24 MHz · Epson FC-135R 32.768 kHz · KSZ8081RNB · QSPI S25FL064L 8 MB (filesystem) · Si3402-B (or Silvertel module) · ISO1211 ×3 · AQY212GS ×2 · DO 10 Ω anti-surge + 0ZCJ0016FF2E PPTC · SN6507 + push-pull xfmr (Würth 750319693 candidate) · TPS26625 eFuse (field output) · ISO3082 · LP3470A293 (supervisor) · NTK3134N low-side LED drive · SE051C2/SE051C2 · XY-MD02/SHT45 · Italtronic 35.0807000.BL
