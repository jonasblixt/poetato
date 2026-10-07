---
name: schematic-review
description: Review the PoEtato KiCad schematic (hw/poetato/*.kicad_sch) against datasheets and the project's design docs - BOM fields, datasheet coverage, symbol pin correctness, test point coverage, DC/DC loop measurement access (Bode 100), ground test points and voltage divider maths. Use when asked to review, check, audit or sanity-check the schematic, a schematic sheet, or a circuit block before layout or ordering. Schematic only; never reviews PCB layout.
---

# Schematic review

Status: draft v0.5 (2026-10-04), scope still being iterated with Jonas. When a
check is added, changed or dropped, edit this file. v0.5: the report keeps
all findings with a Status column (see Report).

## Scope

**In:** the electrical design as drawn: `hw/poetato/*.kicad_sch`, the symbols
embedded in those files, project symbol libraries (`*.kicad_sym`), the
datasheets in `datasheets/`, and the design intent in `doc/`.

**Out: anything about layout.** Do not open or parse `*.kicad_pcb`, `*.step`
or `doc/mech/`. Do not comment on placement, routing, stack-up, copper,
creepage/clearance distances, thermal relief, footprint geometry or whether
a test point is physically reachable. If a schematic finding has a layout
consequence, state the schematic fact and stop ("TP on switch node" is in
scope, "TP too far from U4" is not). The Footprint *field* is not reviewed
unless a later scope revision adds it.

**Read-only.** KiCad is usually open on these files (`~*.lck`). Never edit
schematic, symbol or project files. Output is a report; Jonas makes the edits.

## Inputs

1. Design intent: read `doc/claude context.md` and `doc/hardware-architecture.md`
   first (rails, isolation domains, decided part choices) and run check Q1
   on them before looking at the schematic, so later checks know where the
   intent itself is contradictory. A deviation from a recorded decision is a
   finding; so is a doc that the schematic has outgrown.
2. Inventory: run
   `python3 .claude/skills/schematic-review/scripts/sch_inventory.py hw/poetato datasheets`
   (add `--json` for full per-symbol data including embedded library pins).
   It reads schematic files only.
3. Connectivity and ERC: run kicad-cli yourself, do not ask Jonas to export:
   `python3 .claude/skills/schematic-review/scripts/kicad_export.py hw/poetato/poetato.kicad_sch hw/poetato/.review`
   It finds kicad-cli (PATH, `C:\Program Files\KiCad\<ver>\bin`, or the
   Windows install from WSL) and writes the KiCad XML netlist, the ERC JSON
   and a PDF plot. `hw/poetato/.review/` is scratch output: keep it out of
   git. The script does not resolve nets itself, and the inventory script
   never does: take every net from the exported netlist, never from wire
   coordinates. If the script exits 2 (no kicad-cli in this environment, e.g.
   a sandboxed session without KiCad), say so, use an existing export in
   `hw/poetato/.review/` only if it is newer than every `*.kicad_sch`, and
   otherwise mark all net-dependent checks "not checked".
4. Datasheets: read the relevant pages of the PDF (pinout table, electrical
   characteristics, application circuit). Quote page numbers. Never check a
   pin or a threshold from memory.

The sheets `di.kicad_sch` and `do.kicad_sch` are instantiated several times;
report every reference designator of an instance, not only the first.

## Checks

Each check has an ID; use it in the report.

### F - Fields
- **F1** Every symbol has non-empty `Part Number` and `Manufacturer`.
  Exempt: power symbols, anything with a `#` reference, and symbols marked
  "exclude from BOM" (`in_bom no`, e.g. test points that are PCB pads).
  Otherwise `N/A` is accepted only for test points, fiducials, mounting holes,
  net ties and logos.
  DNP parts are not exempt.
- **F2** `Value` agrees with the part number (e.g. CRCW040288K7FKED is 88.7 kOhm,
  GRM voltage/dielectric codes) and the manufacturer name is spelled
  consistently across the design.

### D - Datasheets
- **D1** Each part number has its datasheet in `datasheets/` (any subfolder).
  Required for ICs, semiconductors, magnetics, connectors, protection,
  crystals and electromechanical parts. For chip resistors, MLCCs and beads a
  series datasheet is nice-to-have: list as info, not as a finding.
  The script only proposes candidates by file name and first-page text: open
  each candidate and confirm it covers the exact ordering code and package
  (a family datasheet must list the ordering code; an EVB guide is not a
  datasheet). Name files `<part or series>_<manufacturer>.pdf` (e.g.
  `ISO1211_ISO1212_TI.pdf`, `2N7002_NDS7002A_onsemi.pdf`) so the inventory
  script and a human can find them; propose a rename when a file does not
  follow this. Folders group by function: `mcu/`, `security/`, `memory/`,
  `ethernet/`, `power/{poe,regulators,field,backup}/`, `io/`, `discretes/`,
  `passives/` (e.g. safety capacitors), `protection/`, `magnetics/`, `crystals/`, `connectors/`, `mechanical/`,
  `external/`. Generic parts used on several sheets go by part type. Propose
  the folder for a new file.
  A URL in the `Datasheet` field does not replace the local file.
- **D2** List files in `datasheets/` that no placed part uses. Split into
  (a) reference material that is expected to stay: application notes,
  reference manuals, design-in checklists, EVK schematics, enclosure and
  external-device documents; (b) datasheets of parts no longer in the design
  (candidates to remove); (c) duplicates of the same datasheet. This is a
  note, never delete anything.

### S - Symbols
- **S1** For every non-generic symbol (everything except 2-pin passives),
  compare the embedded library symbol against the datasheet pinout for the
  ordered package: every pin number exists exactly once, exposed pad
  included; pin names match; no pin of the package is missing or hidden.
  Start with project-local and hand-drawn symbols (`MCXN247VKLT.kicad_sym`
  against the NXP pinout spreadsheet), then ICs, transistors (G/D/S, B/C/E
  vs package pin number), diodes (A/K), polarised capacitors, connectors,
  transformers (winding/dot/pin mapping against the datasheet drawing).
- **S2** Pin electrical type is right: supply pins `power_in`, regulator and
  reference outputs `power_out`, open-drain outputs `open_collector`, NC pins
  `no_connect` (and check the datasheet whether NC means "leave open" or
  "may be tied"), bidirectional vs input vs output. Wrong types matter
  because they silence or falsify ERC.
- **S3** Power symbols: the script lists power symbols whose value differs
  from the library symbol they were made from. Confirm each one shows the
  right graphic and net name (a ground-shaped symbol renamed to a supply rail
  is a finding). Check that ERC is clean or every violation is explained, and
  that no PWR_FLAG hides a rail that really has no driver.

### T - Test points
Record the net of each TP from the netlist and build a coverage table
(rail/signal, domain, TP ref or "missing").
- **T1** Every power rail has a TP: each converter/regulator input and
  output, each rail after a ferrite or load switch that makes it a separate
  net (e.g. P3V3_ETH_VDDA, 3V3_DO), in every isolation domain.
- **T2** Bring-up and debug signals have a TP or are on a header: reset,
  ISP/boot select, supervisor output, DO_EN and the 3V3_DO readback, power
  good/enable/fault pins, SPI and I2C buses, UARTs, RS-485 DE/RO/DI, PHY
  reset/interrupt/MDIO.
- **T3** No TP where it harms: crystal pins, RMII 50 MHz clock and data,
  USB HS D+/D-, MDI pairs. A TP on a switch node or FB/COMP node is allowed
  only if it is a deliberate measurement point and noted as such.
- **T4** TPs have meaningful net names (no `Net-(U4-Pad7)`), so the name can
  go on silkscreen and into a test spec.

### G - Ground test points
- **G1** Each isolation domain (cable/PSE side, logic GND, GND_FIELD) has its
  own ground TPs, referenced to that domain's return and never shared across
  a barrier. Output contacts are floating and need none.
- **G2** Enough ground TPs for good probe contact. Working rule until
  refined: at least 2 per domain, plus one dedicated ground TP for every
  DC/DC converter (for a short probe ground spring and for the Bode 100
  returns), plus roughly one per 5 signal TPs in the logic domain. Report the
  count per domain and per sheet against this rule.
- **G3** Ground TPs are a probe-able type (loop/hook or through-hole), which
  shows in the symbol/part number, not bare pads.

### B - DC/DC converters measurable with a Bode 100
For each converter: Si3402-B isolated flyback (TLVH431 + optocoupler),
TPS563252, TPS54202H, SN6507 push-pull, and any later addition.
- **B1** Closed-loop converters have an injection resistor (10 Ohm typical,
  much smaller than the top feedback resistor, fitted permanently) in series
  with the feedback path between the output and the top of the divider, with
  a TP on each side and a ground TP in the same domain. Nothing else may
  connect between the two TPs.
- **B2** The injection point breaks the loop in exactly one place, at a
  low-impedance-to-high-impedance boundary. For the TL431/optocoupler loop
  this means both the divider (slow path) and the optocoupler LED supply
  (fast path) are taken from the feedback side of the injection resistor,
  or the fast path is explicitly accounted for. Feed-forward capacitors go
  across the top divider resistor, not across the injection resistor.
  Remote/internal-feedback parts: inject at the VOUT/FB sense pin.
- **B3** Converters without a control loop (open-loop push-pull) are exempt
  from B1/B2; note them as "no loop" and check that output and return TPs
  exist for output impedance and load step measurements.
- **B4** Input and output of each converter are reachable (TPs from T1) so
  input/output impedance and PSRR can be measured.

### V - Voltage dividers
Find every divider: regulator feedback, TL431 reference, EN/UVLO thresholds,
supervisor inputs, ADC and GPIO sense inputs (e.g. 3V3_DO readback), PoE
classification/detection resistors, bias networks, RS-485 fail-safe bias.
- **V1** Nominal result: compute it from the placed values and the datasheet
  reference/threshold (quote page), compare with the target implied by the
  net name and the design docs (P3V3 = 3.3 V, P12V = 12 V, ...).
- **V2** Worst case: resistor tolerance plus reference tolerance (and
  hysteresis for thresholds); result stays inside what every load on that
  rail accepts.
- **V3** Divider impedance: bias/leakage current of the tapped pin causes
  negligible error, the divider current is within datasheet recommendations,
  and any ADC/GPIO tap stays below the pin's abs-max with the source at its
  maximum (and when the MCU is unpowered).
- **V4** Each resistor's voltage and power rating covers its worst case
  (notably on the 48 V PoE side: an 0402 is a 50 V part).
- **V5** Show the working: one table row per divider with refs, values,
  formula, nominal, min/max, target, verdict.

### P - Decoupling and supply pins
- **P1** Every supply pin of every IC has the decoupling the datasheet asks
  for (value, count, per-pin vs shared), including bulk capacitance, VDD_CORE /
  LDO output capacitors, analog and USB supplies, and reference pins.
- **P2** Effective capacitance after DC-bias derating still meets the
  datasheet minimum (e.g. 10 uF 0805 X7R at 12 V, 1 uF 0402 at 3.3 V); for
  regulator output capacitors this is a stability requirement, not cosmetics.
- **P3** Every supply pin is connected to the intended rail; rails behind a
  ferrite bead have their own local capacitor on the IC side.

### R - Ratings and derating
- **R1** Capacitor voltage rating vs worst-case rail: at least 2x for MLCCs
  on switching and field rails, 20 % margin for electrolytics; ripple current
  for the flyback and buck output capacitors.
- **R2** Diodes, FETs, TVS and optocouplers: V_RRM/V_DS/V_CEO, current and
  V_GS limits against worst case including flyback reflected voltage and
  leakage spike, PoE up to 57 V and field rail up to 30 V.
- **R3** Resistor power (worst case, 50 % derating as target) and LED,
  optocoupler and PhotoMOS LED currents against the datasheet range and the
  values recorded in the context doc.

### I - Isolation domains
- **I1** Build the net-to-domain map from the netlist (cable/PSE, logic,
  field 24 V, each output contact). No net, power symbol or passive bridges
  two domains except through a listed barrier part: magjack, flyback
  transformer and its optocoupler, push-pull transformer, ISO12xx, ISO3082,
  PhotoMOS, and the deliberate Y capacitors and bleed resistors.
- **I2** Every bridging part is rated for the barrier (Y-rated capacitor,
  high-voltage resistor, reinforced/basic isolation as intended) and both
  sides of each isolator are powered from their own domain's rail and return.
- **I3** Ground names are unambiguous per domain; no generic `GND` symbol
  inside a field-side or PSE-side circuit.

### M - MCU pin assignment
- **M1** Each used pin's function exists on that pin of the MCXN247 HLQFP100
  (`datasheets/mcu/MCXNP184M150F70_Pinout.xlsx`): alternate function
  number, same peripheral instance for all signals of a bus, RMII set, HS USB
  pins, LPUART RTS for RS-485 DE.
- **M2** Walk `MCX_N_Series_Design_In_checklist_v4.xlsx` and UG10092 line by
  line: supply scheme (LDO vs DCDC core), VDD_USB, VBAT/supercap, reset,
  ISP pin, SWD, crystal pins, unused pins.
- **M3** Reset-state behaviour: every pin that drives an actuator or enable
  (DO_EN, PhotoMOS sinks, RS-485 DE, PHY reset, SE05x ENA) is safe while the
  pin is hi-Z, during ROM boot and in ISP mode; external pulls define it.
- **M4** Boot/ISP and debug access: ISP pin reachable and not loaded, UART
  ISP header, SWD header pinout matches the standard for the chosen connector.

### X - Digital interfaces
- **X1** I2C and other open-drain lines have exactly one set of pull-ups to
  the right rail with a value suited to bus speed and capacitance.
- **X2** Logic levels and thresholds are compatible on both sides of every
  connection, including isolator supply-dependent thresholds; no input is
  driven above its rail when that rail is off (back-powering).
- **X3** No floating inputs: unused inputs, enables, address and strap pins
  are tied as the datasheet requires. Strap pins (PHY address/mode, boot
  config) resolve to the intended value with everything else attached.
- **X4** Series/termination resistors where the datasheet or the interface
  calls for them (RMII clock, SPI clock, RS-485 termination and fail-safe
  bias), chip selects have pull-ups, TX/RX and MOSI/MISO are not swapped.

### C - Converter design values
For each converter, recompute from the datasheet equations and compare with
the placed parts; show the working in a table.
- **C1** Inductor/transformer: inductance, ripple current, peak current vs
  saturation current at the current limit, turns ratio and reflected voltage.
- **C2** Output and input capacitance vs minimum for stability and ripple,
  compensation network, feed-forward capacitor, soft-start, bootstrap
  capacitor, snubber/clamp.
- **C3** Enable/UVLO, mode and frequency pins set as intended; current limit
  resistor; minimum load of unregulated outputs.
- **C4** PoE PD front end: detection signature and classification resistor
  match the intended class (Class 2), input capacitance within the
  802.3af limit, Si3402 pin strapping against the datasheet and AN956.

### E - External connections and protection
- **E1** Every connector pin has a defined protection path: TVS standoff
  above the maximum working voltage and clamp below the abs-max of what it
  protects, series impedance, PPTC hold/trip/voltage rating, polarity.
- **E2** Connector pinout matches the terminal plan in the context doc and
  signal naming (`+24V FLD` / `0V FLD`, never `COM`).
- **E3** Ethernet front end: Bob Smith termination, centre-tap handling, PoE
  taps, chassis/shield connection as designed. USB: ESD part pinout, VBUS
  handling, CC/ID if applicable.

### W - Power budget
- **W1** Sum the load per rail from datasheet typical and maximum figures and
  compare with each converter's capability and with the budget in the context
  doc (4.24 W total, Class 2 limit 6.49 W at the PD).
- **W2** Power sequencing and supervisor: reset threshold vs minimum
  operating voltage of every part on the rail, enable chains, inrush.

### K - Clocks
- **K1** Crystal load capacitors computed from the specified C_L and an
  assumed stray capacitance; drive level and ESR within the oscillator's
  limits; feedback/series resistors as the MCU and PHY datasheets require.
- **K2** Clock sources and directions are consistent (who generates the RMII
  50 MHz reference, PHY strap for it, 24 MHz for HS USB ISP).

### Q - Consistency of and with the design docs
- **Q1** Doc against doc, done first: compare `doc/hardware-architecture.md`
  with `doc/claude context.md` statement by statement and list every
  inconsistency: part numbers and variants, rail voltages and names, power
  budget figures, isolation domains, I/O counts, pin assignments, component
  values, fault architecture, terminal plan, and items one doc marks decided
  while the other marks open or rejected. Also flag a fact that appears in
  only one of the two when the other covers the same topic. Where they
  disagree, do not pick a winner silently: quote both (file, section, dated
  decision if any), say which one the schematic follows, and raise it as a
  Question. A newer dated decision is a hint, not proof. Check
  `doc/poe-verification.md` and `doc/security-requirements.md` the same way
  where they state hardware facts.
- **Q2** Schematic against docs: every decision in the two docs is either
  implemented as written or listed as a deviation: part choices, values,
  fault architecture (DO_EN gating, boot check divider), protection parts,
  interface choices. Where Q1 found a conflict, check against both versions.
- **Q3** List where the docs are stale relative to the schematic so they can
  be updated; do not edit them as part of the review.

### H - Hygiene
- **H1** ERC run with kicad-cli: zero errors, every warning explained.
- **H2** No auto-generated net names on nets that matter, hierarchical
  labels and sheet pins match in name and direction, no duplicate or
  near-duplicate net names (P3V3 vs +3V3), no unannotated references.
- **H3** DNP parts, 0 Ohm options and solder jumpers are annotated with what
  they select and their default; no-connect flags only on pins that the
  datasheet allows to float.
- **H4** Notes on the sheet state non-obvious design intent (thresholds,
  option tables, isolation boundary).

### L - Lifecycle and sourcing
- **L1** No part is NRND/obsolete; the manufacturer in the field is the
  current owner of the part number. Check the manufacturer's product page;
  say so when it could not be checked.
- **L2** Flag single-source parts on critical functions and note a
  pin-compatible alternative where one exists. Info level, not a finding.

## Report

The report is a **living document of all findings, each with a status**, not
a log of re-checks. It lives at `doc/review/schematic-review-YYYY-MM-DD.md`,
dated by when the review started (docs live in the repo). If one already exists
for the current review, update it in place; don't start a new file per re-check.
Give a short summary in chat.

Fixed findings stay in the tables with their status, so the record of what was
found remains visible.

Structure:

1. **Header.**
   - Date the review started.
   - The revision checked: file save time, and the git commit, or say it is
     uncommitted.
   - Sheets, ERC result, and what could not be checked and why (e.g. no
     netlist, datasheet missing).
   - The legend for severities and statuses.
2. **Findings**, one table per severity in this order: Errors, Warnings,
   Notes, Questions.
   - Columns: ID (check ID + running number, e.g. `K2-1`), **Status**, sheet,
     refs, finding, evidence (datasheet + page, or calculation), suggested fix
     or resolution. Notes and Questions can use a shorter table (ID, Status,
     refs, finding).
   - Within each table, list Open and Partly fixed rows first, then the closed
     ones.
   - Status values:
     - **Open**: not addressed.
     - **Partly fixed**: say what remains.
     - **Fixed**: verified fixed in the schematic. No revision times or
       timestamps in the status or fix text; just "Fixed".
     - **Resolved (decision)**: the schematic stays as is by decision, and the
       docs record it.
     - **Not an issue**: withdrawn after Jonas's input.
     - **Info**: verified, nothing to do.
     - **Merged**: tracked in another ID.
   - For a closed finding, keep the original finding text short and put what
     changed (new value, doc section) in the fix/resolution column.
   - Put the working needed to understand a finding (the calculation, the
     datasheet value) in the finding itself. Don't keep separate T/G/B/V5/C/W1
     tables in the report: use them as working while reviewing, then fold the
     results into findings or into the checks list.
   - Severities: **Error** (will not work or can damage), **Warning** (risk,
     margin or testability gap), **Note** (housekeeping), **Question** (intent
     unclear, ask instead of assuming).
3. **Checks performed.** One entry per check group (F, D, S, T, G, B, V, P, R,
   I, M, X, C, E, W, K, Q, H, L).
   - Say which items pass, with the key evidence (value, datasheet page), and
     which finding IDs are still open.

Re-checks after Jonas fixes things:

- Re-export with `kicad_export.py`. Keep a copy of the previous parsed netlist
  and diff component by component (value, part number, DNP, manufacturer,
  pin-to-net) so every change is seen, including unrelated ones and
  re-annotation.
- Re-verify **every** finding that is not closed against the new netlist and
  ERC, not only the ones Jonas mentions. Also check that a fix did not break
  something else (e.g. a symbol edit that disconnected pins).
- **Update the Status of each finding in place.** Never delete a finding. New
  findings get a new ID in the right severity table.
  - Do not append "re-check of revision X" sections or separate
    status-history tables. The Status column and the fix/resolution column are
    the history.
- When Jonas decides a finding is not a problem, or that the schematic stays as
  is:
  - Set the status to **Not an issue** or **Resolved (decision)**.
  - If the decision makes a design doc stale, record that under the doc Note.
    Edit the docs only when Jonas asks.
- Update the header (revision checked, ERC) and the checks-performed list.
- In chat, report what was fixed, what is still open, and anything new.

Only report what was verified against a file. If a datasheet is missing, the
affected S/V/B checks are "not checked", not "pass".
