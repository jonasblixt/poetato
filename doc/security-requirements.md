# PoEtato — security requirements (CRA-oriented)

Draft 2026-09-29. Assumes PoEtato is sold as a real product on the EU market: Ethernet/PoE only (no radio), MQTT over mTLS to a broker, local HTTPS UI with device certificates, Modbus TCP/RTU, OTA updates.

---

## 1. Regulatory frame

| Regulation | Applies? | Notes |
|---|---|---|
| **Cyber Resilience Act (EU) 2024/2847** | **Yes** | Reporting obligations (Art. 14) apply since **11 Sep 2026**. All essential requirements + CE marking apply to products placed on the market from **11 Dec 2027**. |
| RED Delegated Act / EN 18031-1 | No — while there is no radio | Adding Wi-Fi/BLE/Thread pulls in RED + EN 18031 immediately. Keep the product wired. |
| LVD | No | PoE 44–57 V DC is below the 75 V DC threshold. |
| EMC, GPSR, RoHS/REACH/WEEE | Yes | Not security, listed for completeness. |
| Data Act (EU) 2023/2854 | Yes | Connected products placed on the market after 12 Sep 2026 must make user-generated data accessible by design. MQTT/Modbus access largely covers this — document it. |

### CRA classification — DECIDED 2026-09-29: default category

PoEtato is positioned as a **generic DIN-rail PoE I/O controller / Modbus–MQTT gateway**, so it falls in the default category and uses Module A self-assessment. The garage door is an *example application*, not the intended purpose. Keep datasheet and marketing wording consistent with this. The background for the decision follows.

Implementing Regulation (EU) 2025/2392 describes Annex III Class I item 17, *smart home products with security functionalities*, as products that "protect the physical security of consumers in a residential setting and which can be controlled or managed remotely". Its examples are door locks, alarms and cameras; the list is not exhaustive.

- **Marketed as a remote garage-door controller for homes → plausibly Class I.** Then self-assessment (Module A) is allowed only if a cited harmonised standard is applied in full. Otherwise a notified body is required (Module B+C or H).
- **Marketed as a generic DIN-rail PoE I/O controller / Modbus–MQTT gateway → default category.** Self-assessment (Module A).
- As of mid-2026, **no CRA harmonised standard is cited in the OJEU**; the first citations are expected in 2027. A Class I product launching before then effectively needs a notified body.
- Intended purpose, datasheet and marketing wording decide the class. Write the intended-use statement early and keep it consistent.
- Integrating an important/critical component (SE051, MCU with security functions) does not change our class. We still owe due diligence on components (Art. 13(5)), including Zephyr, mbedTLS and Plug & Trust.

---

## 2. Standards basis (until CRA hENs are cited)

| Standard | Role for PoEtato |
|---|---|
| **prEN 40000-1-2** (principles), **-1-3** (vulnerability handling), **-1-4** (generic security requirements) | The future CRA horizontal hENs. Structure the technical file around them now. -1-3 is expected to be cited first. |
| **IEC 62443-4-2, SL2**, Embedded Device requirements | Best fit for a PLC-like device; it gives concrete component requirements (CR 1.x auth, CR 3.x integrity, CR 7.x availability). |
| **IEC 62443-4-1** (lightweight) | Secure development lifecycle evidence: threat model, reviews, testing, patch management. |
| **ETSI EN 303 645** | Consumer IoT baseline with 13 provisions. A cheap gap checklist, and relevant if positioned for consumers. |
| **EN 18031-1** | Not applicable (no radio), but its decision trees for access control, secure update and crypto are a useful template. |
| ECCG *Agreed Cryptographic Mechanisms* / BSI TR-02102 | Justify algorithm and key-length choices. |

None of these gives presumption of conformity under the CRA today. They count as "state of the art" evidence behind a documented risk assessment.

---

## 3. Product requirements (CRA Annex I Part I)

| ID | Requirement | CRA Annex I | Notes |
|---|---|---|---|
| SEC-01 | Unbroken secure boot chain: ROM → bootloader → application, all signature-verified. **No unsigned path, including USB recovery.** | (2)(f) integrity | Recovery may re-flash only signed images. |
| SEC-02 | Anti-rollback: fuse/OTP-backed security version counter checked by the bootloader. | (2)(f) | |
| SEC-03 | Signed A/B OTA with automatic fallback on a failed boot. Power loss at any point never bricks the device. | (2)(c) | Signing key offline, ideally in an HSM (Nitrokey HSM, YubiHSM). |
| SEC-04 | Security updates **automatic by default with user opt-out**. Install window configurable, with notification. Security fixes can ship separately from feature updates. | (2)(c), Part II(8) | For a control device, allow "notify only" mode, documented as the opt-out. |
| SEC-05 | Unique per-device identity: key generated inside the SE and never exported; IDevID-style cert (IEEE 802.1AR) from the product CA. **No fleet-wide secrets anywhere.** | (2)(d),(e) | Existing SE051 provisioning flow. |
| SEC-06 | No default passwords. First-use claim via unique per-device credential on the label, or a physical button press within a time window. | (2)(b),(d) | |
| SEC-07 | TLS 1.3 preferred, 1.2 minimum, ECDHE + AEAD only. Full chain validation against the configured trust anchor. mTLS to the broker. Trust store updatable OTA. | (2)(e) | |
| SEC-08 | Local HTTPS: the factory cert (product CA) is not browser-trusted, so the operator can install their own cert/CA (LDevID). HTTP only redirects to HTTPS. | (2)(e) | |
| SEC-09 | **Modbus TCP has no authentication** → off by default. When enabled: IP allowlist, read-only by default, output writes need a separate explicit enable, rate-limited. Later option: Modbus/TCP Security (TLS, port 802). | (2)(b),(d),(j) | Otherwise anyone on the LAN can open the garage door. |
| SEC-10 | Minimal attack surface: only enabled services listen. Shell/RTT/debug logging compiled out of production builds. JTAG/SWD disabled or authenticated debug. | (2)(j),(k) | |
| SEC-11 | Availability under network abuse (storms, floods, malformed frames): I/O logic, watchdog and fail-safe keep working; outputs go to a defined state on comms loss. | (2)(h),(i) | IEC 62443-4-2 CR 7.1/7.2. Fits the existing fault architecture. |
| SEC-12 | Security event log (boot/verification result, updates, auth failures, config changes) in a RAM/flash ring buffer, exportable via syslog/MQTT. User can opt out. | (2)(l) | |
| SEC-13 | Factory reset securely erases user config and credentials; device identity is kept. | (2)(m) | |
| SEC-14 | Secrets at rest (broker creds, local UI/API creds) encrypted or held in the SE. No telemetry to the vendor by default. | (2)(e),(g) | Data minimisation. |
| SEC-15 | Crypto agility / PQC readiness: bootloader is field-updatable; image format supports more than one signature algorithm (hybrid ECDSA + LMS or ML-DSA); flash/RAM headroom reserved. | state of the art | EU PQC roadmap: high-risk use cases quantum-safe by end of 2030, medium by 2035. A product sold in 2028 with a 10-year life crosses both dates. |
| SEC-16 | Time: certificate validation needs a sane clock. Use NTP with plausibility checks (monotonic floor = build date). NTS optional. | (2)(e) | |

---

## 4. Process requirements (Annex I Part II, Art. 13–14)

- **Risk assessment / threat model** (STRIDE on the data-flow diagram). Kept in the technical file and updated each release.
- **SBOM** per release (SPDX via `west spdx`, at least the top-level dependencies). Archived with the build.
- **Vulnerability monitoring**: Zephyr, mbedTLS, SE05x Plug & Trust, NXP ROM/SoC security bulletins. Automated SBOM → OSV/NVD scan weekly.
- **Coordinated vulnerability disclosure**: published CVD policy, `security.txt`, security contact, advisories.
- **Support period** declared on the product (CRA minimum 5 years; expected PLC-like lifetime is 10+). Security updates free of charge.
- **Reporting via the ENISA Single Reporting Platform**:
  - actively exploited vulnerability: early warning within 24 h, notification within 72 h, final report within 14 days after a fix is available
  - severe incident: 24 h, 72 h, final report within 1 month
- **Technical documentation + EU Declaration of Conformity** kept for 10 years.
- **Key management**: documented signing-key ceremony, offline product CA, HSM-held signing keys, revocation and rotation plan.
- **Reproducible release builds** (pinned `west.yml`, recorded toolchain).

---

## 5. Verification plan

| Test | Tooling | When |
|---|---|---|
| Threat model review | STRIDE, DFD | Each design milestone |
| Static analysis | clang-tidy, cppcheck / CodeChecker, compiler hardening flags | CI |
| SCA / CVE scan | SBOM → osv-scanner / grype | CI + weekly |
| Fuzzing | libFuzzer on `native_sim`: Modbus TCP/RTU parsers, MQTT/HA payloads, HTTP handlers, bootloader image-header parser | CI (nightly) |
| TLS configuration | testssl.sh / sslyze on local HTTPS; mTLS negative cases (expired, wrong CA, revoked, wrong CN) | Per release |
| Network robustness | nmap (only expected ports), hping3 floods, scapy malformed frames, broadcast storm. **I/O cycle and watchdog must stay intact.** Optional accredited lab (Achilles/Defensics class). | Per release |
| Secure boot / update negatives | Tampered image, wrong key, rollback attempt, power cut during every update phase, corrupted slot | Per release + HIL |
| Hardware | Verify fuse state (secure boot closed, debug locked), attempt debug attach, dump QSPI with a clip → no secrets or credentials | Production sample |
| Third-party pentest | External lab | Before launch; mandatory in practice if Class I |

---

## 6. MCU implications

CRA is outcome-based and mandates no silicon feature. The MCU decides how cheaply and credibly the requirements above can be met.

### Features to look for

**Must**

- Immutable ROM root of trust with asymmetric secure boot; key hash in OTP; multiple revocable keys.
- OTP monotonic counter(s) for anti-rollback.
- Debug lock **with authenticated re-open** (RMA/failure analysis without a permanently open part).
- Certified TRNG (SP 800-90B / AIS-31 class).
- AES-GCM + SHA-2 acceleration.
- Enough RAM for TLS 1.3 + MQTT + HTTPS server concurrently (≥256 KB, better ≥512 KB).
- Flash/layout that supports A/B cleanly.
- Ethernet MAC.
- Long vendor longevity and a working vendor PSIRT with published bulletins.

**Should**

- Arm TrustZone-M (or equivalent isolation), so keys, update and output-safety logic sit outside the network stack's reach.
- ECC public-key accelerator (boot verify, TLS, side-channel-hardened).
- Internal flash, or on-the-fly decryption for external XiP.
- PUF / hardware-unique key for wrapping secrets.
- Voltage/clock glitch detectors.

**Nice**

- PSA Certified L2/L3 or SESIP certification: ready-made evidence for the technical file.
- Headroom for PQC signature verification (ML-DSA public key ~1.3 KB, signature ~2.4 KB, tens of KB of stack/RAM; LMS is cheaper to verify).

### Selection constraints (2026-09-29)

- Ethernet MAC required.
- LQFP100 preferred; other packages acceptable.
- USB nice to have.
- Any vendor.
- PSA Certified / SESIP is a strong plus.

### Shortlist

The only parts found that meet Ethernet + 100-pin QFP + PSA Certified Level 3 are these three:

| | **NXP MCX N947** | **ST STM32H573** | **Renesas RA8M1** |
|---|---|---|---|
| 100-pin part | MCXN947VKLT (HLQFP100, exposed pad; VNLT suffix deprecated) | **STM32H573VIT6** (LQFP100, LDO). ⚠ The SMPS variant VIT3Q has **no Ethernet** (RXD0/1 not bonded). | R7FA8M1A…CFP (LQFP100) |
| Ethernet on 100-pin | Yes, RMII only. MDC/MDIO on P1_2/P1_3 (P1_20/21 not bonded). | Yes (LDO variants) | Yes, 1 ch 10/100 |
| USB on 100-pin | **FS only**. USB1 HS pins are GPIO on N94x HLQFP100 (UG10092 Fig. 10); corrected 2026-09-29. | FS only (+ UCPD) | FS |
| Core | 2× Cortex-M33 150 MHz | Cortex-M33 250 MHz | Cortex-M85 480 MHz |
| Flash / RAM | 2 MB dual bank / 512 KB | 2 MB dual bank / 640 KB | 1–2 MB / 1 MB |
| Crypto / key storage | EdgeLock Secure Subsystem: ELS (AES/SHA/keystore), PKC, PUF, TRNG | SAES + PKA (DPA-resistant), HASH, DHUK, TRNG | RSIP-E51A (AES/SHA/ECC/RSA), TRNG |
| Root of trust | ROM secure boot, debug authentication, OTP anti-rollback | STiRoT (immutable) or OEMiRoT, debug authentication, product states | Immutable boot + RSIP, key injection (DLM) |
| **Certification** | **PSA Certified Level 3** (v2.0 beta, Riscure, Oct 2024), covers N94x/N54x | **PSA Certified Level 3** (SGS Brightsight, Mar 2026) + **SESIP 3** | **PSA Certified Level 3 RoT Component** (Applus+, Feb 2025): RoT only, not full-chip PSA L3 |
| Zephyr | `frdm_mcxn947` upstream, ENET QoS, USB HS/FS, TRNG, `…/cpu0/ns` TF-M target | `stm32h573i_dk`, `nucleo_h563zi`; Ethernet, USB, AES; TF-M platform exists | `ek_ra8m1`; Ethernet, USB, RSIP TRNG. Security/crypto integration less mature. |
| Fit with current design | Same vendor as SE051 / MCUXpresso. EdgeLock 2GO provisioning (AN14544). | Vendor change, strong docs. | Vendor change. |

**Excluded:**

- STM32H7S3: PSA L3, but only 64 KB internal flash and M7 without TrustZone.
- STM32U5: no Ethernet.
- i.MX RT1180: BGA only.
- Microchip PIC32CK SG: TQFP100 + Ethernet + HSM, but no PSA/SESIP certificate found.
- i.MX RT1021: no certification, no TrustZone.

### DECIDED 2026-09-29: NXP MCX N24 (MCXN247VKLT), with MCXN547VKLT as the certified drop-in

Rationale: early in the design; single core is right-sized; HS USB recovery/ISP in HLQFP100; Zephyr port is small; PSA certification is not required for a hobby project (accepted risk).

**MCX N24 facts** (from the MCX N9xx/N5xx/N24x datasheet, Rev. 8.2, June 2026):

- Same datasheet and same mask set as N94x/N54x, i.e. the same die with features disabled.
- Single Cortex-M33 at 150 MHz, 2 MB dual-bank flash, 512 KB SRAM.
- Same security subsystem: ELS, PUF, PKC, TrustZone.
- No NPU, no PowerQuad, no USB FS controller.
- −40…+125 °C.

**HLQFP100 pinout** (UG10092 Fig. 10, Zephyr hal_nxp pinctrl for the VNL variants):

- The N54x/53x/52x/24x columns are identical to each other.
- RMII Ethernet is available: TX_CLK P1_4, TXEN P1_5, TXD0/1 P1_6/7, RXDV P1_13, RXD0/1 P1_14/15.
- **MDC/MDIO must use P1_2/P1_3.** FRDM-MCXN947 uses P1_20/21, which are not bonded in HLQFP100.
- MII-only signals are not available.
- USB1 HS with on-chip PHY is on pins 40–42 (USB1_DP/DM/VBUS). On N94x these pins are GPIO, so **N947 in HLQFP100 has no HS USB**.

**Why N24:**

- Right-sized: single core, cheaper.
- HS USB in the 100-pin package.
- Same security hardware as the certified N94x/N54x.

**Open issues (certification is not the only one):**

1. **Certification.** The PSA L3 certificate covers N94x/54x A1 and N23x A0; N24/N52/N53 are not listed. N24 sharing the die and ROM makes an extension plausible, and N54x set the precedent of certifying a derivative. It is not guaranteed. Ask NXP whether the N247 silicon revision and ROM match the certified TOE, and whether an extension is planned.
2. **Zephyr support.** There is no MCXN247 SoC in Zephyr main or hal_nxp as of 2026-09-29 (only N947/946/547/546/236/235). The port should be small: model it on the MCXN547 variant, disable cpu1/NPU/PowerQuad/USB FS, and add HLQFP100 pinctrl. Develop on FRDM-MCXN947 until then.
3. **Maturity.** Resolved: MCXN247VKLT is in mass production and orderable from Mouser as of 2026-09. Still worth checking the NXP longevity-programme listing.
4. USB is HS-only (the HS controller also runs at FS). This is not a problem.

**N247 vs N947 (HLQFP100)** — from datasheet Rev. 8.2, Table 4:

- Identical:
  - one M33 @150 MHz usable (the second N947 core is extra)
  - 2 MB dual-bank flash, 480 KB + 32 KB ECC SRAM
  - EdgeLock Secure Enclave Core Profile (ELS/PUF/PKC/TRNG), TrustZone
  - dual secure boot (asymmetric + symmetric/PQ-safe)
  - 8 tamper pins, voltage/clock/temperature/light glitch and tamper detection
  - RMII Ethernet, FlexSPI, 2× CAN-FD, 2× I3C, FlexIO, 2× FlexPWM/QDC, SINC
  - −40…+125 °C
- N947 only: second core, NPU, PowerQuad, SAI, MICFIL, TSI, USB FS controller, 10 vs 8 Flexcomm, 78 vs 74 GPIO.
- N247 only (in HLQFP100): USB1 HS with PHY. On the N947 these pins are GPIO.
- For PoEtato, the N247 loses nothing needed:
  - Flexcomm: I²C for the SE051, UART with RTS for RS-485 (digital inputs are plain GPIOs)
  - it gains HS USB
- The N947's remaining advantages are the certificate, Zephyr support and production status.

**HLQFP100 pin-level difference (UG10092 Fig. 10):** only pins 40–43 differ.

| Pins 40–43 | MCXN947VKLT | MCXN247VKLT |
|---|---|---|
| Signals | P4_19, P4_20, P4_21/ANA_22, P4_23 (GPIO/analog) | USB1_DP, USB1_DM, USB1_VBUS, VSS_USB (HS USB) |

- This accounts exactly for the 78 vs 74 GPIO.
- All other 96 pins are identical, including Ethernet, FlexSPI A/B, tamper (P5_2/P5_3), DCDC and USB0 pins.
- USB0 (FS) pins 44–46 are bonded on both, but the N247 has no FS controller behind them.
- VKLT vs VNLT (PCN 202502004F01, effective 2025-06-07) is only an enlarged exposed ground pad. It is not a die change. **Use the VKLT package outline for the footprint/stencil.**

**N947VKLT ↔ N247VKLT footprint compatibility: not adopted.** The board is laid out for MCXN247VKLT only (USB1 HS on pins 40–43, no 0 Ω option links, no UART ISP header; USB1 HS is the only ROM ISP interface, decided 2026-10-04). Firmware development starts on the FRDM-MCXN947 board instead. The rules below are kept as reference in case an N947 build is ever wanted:

- **Pin 42** is USB1_VBUS on N247 (5 V tolerant, route VBUS directly) but **P4_21/ANA_22 on N947, which is not 5 V tolerant**. Put a 0 Ω link between VBUS and pin 42: DNP on N947 builds, fitted on N247 builds.
- **Pin 43** is VSS_USB on N247 and P4_23 GPIO on N947. Grounding it is OK on N947 as long as firmware leaves P4_23 at MUX=0 and never drives it.
- **Pins 40/41** (USB1 D+/D−) and **45/46** (USB0 FS D+/D−): select the connector path with 0 Ω pairs (N247 → 40/41 HS, N947 → 45/46 FS). Avoid stubs. FS VBUS detect on N947 needs a divider (not 5 V tolerant).
- VDD_USB (3.3 V) is powered on both.
- An HF crystal from the USB-legal list is needed; **24 MHz** is required for HS USB ISP with factory fuses.
- An N947 build would have no ROM ISP path on this board (no UART ISP header, USB1 not bonded), only SWD.
- Firmware: a different SoC target and USB pinctrl, otherwise identical (same die, ROM, flash map, secure boot/fuse provisioning flow). Record the part and certificate status per build in the technical file.

**Hedge:** lay out for MCXN247VKLT. **MCXN547VKLT** has the same package and the same relevant pins (Ethernet RMII + USB1 HS, no USB FS), and it is **PSA L3 certified**. If N24 certification or availability slips, populate N547 with firmware unchanged except the SoC target; its second core and NPU simply stay off.

Other consequences and to-dos (apply to either part):

- HAB → MCX N ROM secure boot → **punchboot** (ported to MCX N; MCUboot only as an initial exploration). Dual bank A/B, OTP anti-rollback.
- The QSPI stays, fitted as standard, but only for the filesystem (configuration, logs, data): never code, nothing secret (decided 2026-10-06).
- Keep the SE051 for v1.
- The HLQFP100 exposed pad must be stitched to GND. Choose the LDO or DCDC core-supply configuration (UG10092 §3.2).

**Runner-up: STM32H573VIT6.** It has the strongest evidence package (PSA L3 + SESIP 3, recent 2026 certificate) and more CPU. Its only drawback here is FS-only USB and a vendor switch. Watch the VIT6 vs VIT3Q trap.

**Note:** a certified MCU is evidence for the PoEtato technical file ("state of the art" RoT). It does not certify PoEtato. The certificate applies only to the certified hardware revision and ROM/RoT firmware versions, so record the ones used.
