#!/usr/bin/env python3
"""Schematic inventory for the schematic-review skill.

Reads KiCad *.kicad_sch files only (never the PCB) and prints the mechanical
part of the review: field completeness, datasheet coverage, unused datasheets,
test point list and a few symbol sanity checks. Connectivity is NOT derived
here - use a netlist exported by KiCad for anything net-related.

usage: sch_inventory.py <schematic dir> <datasheet dir> [--json]
"""
import collections, glob, json, os, re, subprocess, sys

REQUIRED = ("Part Number", "Manufacturer")
# Reference prefixes that must have a component datasheet in the folder.
# Chip R/C/ferrite beads come from series libraries; reported as info only.
DS_REQUIRED = re.compile(r"^(U|Q|D|T|L|K|F|J|P|X|Y|SW|RV|BT|IC)\d")
NO_PART = re.compile(r"^(TP|FID|H|MH|LOGO|NT)\d")  # N/A is acceptable here
TOK = re.compile(r'\s*(\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+)')


def parse(text):
    stack = [[]]
    for m in TOK.finditer(text):
        t = m.group(1)
        if t == "(":
            new = []
            stack[-1].append(new)
            stack.append(new)
        elif t == ")":
            stack.pop()
        elif t[0] == '"':
            stack[-1].append(t[1:-1])
        else:
            stack[-1].append(t)
    return stack[0][0]


def kids(node, name):
    return [x for x in node if isinstance(x, list) and x and x[0] == name]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def lcs(a, b):
    best, prev = 0, [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b):
            cur.append(prev[j] + 1 if ca == cb else 0)
        best = max(best, max(cur))
        prev = cur
    return best


def pdf_text(path):
    try:
        out = subprocess.run(["pdftotext", "-l", "3", path, "-"], capture_output=True, timeout=60)
        return norm(out.stdout.decode("utf8", "ignore"))
    except Exception:
        return ""


def load(sch_dir):
    parts, lib_pins = [], {}
    for f in sorted(glob.glob(os.path.join(sch_dir, "*.kicad_sch"))):
        tree = parse(open(f, encoding="utf8").read())
        sheet = os.path.basename(f)
        for ls in kids(tree, "lib_symbols"):
            for sym in kids(ls, "symbol"):
                pins = []
                def walk(n):
                    for x in n:
                        if isinstance(x, list):
                            if x and x[0] == "pin" and len(x) > 2 and not isinstance(x[1], list):
                                nm = kids(x, "name"); nu = kids(x, "number")
                                pins.append({"number": nu[0][1] if nu else "", "name": nm[0][1] if nm else "",
                                             "type": x[1], "hidden": any(k == ["hide", "yes"] or k == "hide" for k in x)})
                            else:
                                walk(x)
                walk(sym)
                lib_pins[sym[1]] = pins
        for s in kids(tree, "symbol"):
            lib = kids(s, "lib_id")
            if not lib:
                continue
            props = {p[1]: p[2] for p in kids(s, "property")}
            refs = [r[1] for i in kids(s, "instances") for pr in kids(i, "project")
                    for pa in kids(pr, "path") for r in kids(pa, "reference")]
            flag = lambda k: (kids(s, k) or [[k, "no"]])[0][1] == "yes"
            parts.append({"sheet": sheet, "refs": sorted(set(refs)) or [props.get("Reference", "?")],
                          "lib_id": lib[0][1], "props": props, "dnp": flag("dnp"),
                          "in_bom": (kids(s, "in_bom") or [[0, "yes"]])[0][1] == "yes",
                          "unit": (kids(s, "unit") or [[0, "1"]])[0][1]})
    return parts, lib_pins


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sch_dir, ds_dir = sys.argv[1], sys.argv[2]
    parts, lib_pins = load(sch_dir)
    real = [p for p in parts if not p["refs"][0].startswith("#")]
    power = [p for p in parts if p["refs"][0].startswith("#")]

    # 1. required fields
    missing = []
    for p in real:
        na_ok = bool(NO_PART.match(p["refs"][0]))
        for k in REQUIRED:
            v = p["props"].get(k, "").strip()
            if not v or (v.upper() in ("N/A", "NA", "-", "~", "?", "TBD") and not na_ok):
                missing.append((p["sheet"], ",".join(p["refs"]), k, v or "<absent>"))

    # 2. datasheets: group by part number
    pdfs = [f for f in glob.glob(os.path.join(ds_dir, "**", "*"), recursive=True) if os.path.isfile(f)]
    texts = {f: pdf_text(f) for f in pdfs if f.lower().endswith(".pdf")}
    by_pn = collections.OrderedDict()
    for p in real:
        pn = p["props"].get("Part Number", "").strip()
        if not pn or pn.upper() == "N/A":
            continue
        e = by_pn.setdefault(pn, {"mfr": p["props"].get("Manufacturer", ""), "refs": [], "url": p["props"].get("Datasheet", ""), "lib_id": p["lib_id"]})
        e["refs"] += p["refs"]
    used = set()
    for pn, e in by_pn.items():
        n, hits = norm(pn), []
        for f in pdfs:
            raw = os.path.splitext(os.path.basename(f))[0]
            # files are named <part or series>[_<part>...]_<manufacturer>; compare the
            # whole stem and each "_" segment, so the manufacturer suffix does not dilute it
            by_name = False
            for seg in [raw] + raw.split("_"):
                stem = norm(seg)
                if len(stem) >= 4 and lcs(n, stem) >= max(5, int(0.6 * min(len(n), len(stem)))):
                    by_name = True
                    break
            by_text = any(n[:k] in texts.get(f, "") for k in (len(n), max(6, len(n) - 3)) if len(n) >= 6)
            if by_name or by_text:
                hits.append((os.path.relpath(f, ds_dir), "name" if by_name else "text"))
        e["datasheets"] = hits
        used.update(h[0] for h in hits)
        e["required"] = bool(DS_REQUIRED.match(sorted(e["refs"])[0]))
    unused = sorted(os.path.relpath(f, ds_dir) for f in pdfs if os.path.relpath(f, ds_dir) not in used)

    # 3. test points, 4. power symbol sanity
    tps = [(p["sheet"], ",".join(p["refs"]), p["props"].get("Value", "")) for p in real if p["refs"][0].startswith("TP")]
    odd_power = [(p["sheet"], p["refs"][0], p["lib_id"], p["props"].get("Value", "")) for p in power
                 if p["lib_id"].split(":")[-1] != p["props"].get("Value", "") and "PxVx" not in p["lib_id"]]

    if "--json" in sys.argv:
        json.dump({"parts": parts, "lib_pins": lib_pins, "missing_fields": missing, "by_part_number": by_pn,
                   "unused_datasheets": unused, "test_points": tps, "odd_power_symbols": odd_power}, sys.stdout, indent=1)
        return
    print(f"# Schematic inventory: {len(real)} symbols, {len(by_pn)} unique part numbers, {len(tps)} test points\n")
    print("## Missing or placeholder required fields")
    for m in missing or [("none", "", "", "")]:
        print("- " + " | ".join(m))
    print("\n## Part numbers WITHOUT a datasheet candidate (required categories)")
    for pn, e in by_pn.items():
        if e["required"] and not e["datasheets"]:
            print(f"- {pn} ({e['mfr']}) refs {','.join(sorted(set(e['refs'])))} url:{e['url'] or '-'}")
    print("\n## Part numbers without a datasheet candidate (passives, info only)")
    print(", ".join(pn for pn, e in by_pn.items() if not e["required"] and not e["datasheets"]) or "none")
    print("\n## Datasheet candidates (verify the match is the right part and package)")
    for pn, e in by_pn.items():
        if e["datasheets"]:
            print(f"- {pn}: " + "; ".join(f"{h[0]} [{h[1]}]" for h in e["datasheets"]))
    print("\n## Files in datasheet folder not matched to any part")
    for u in unused:
        print("- " + u)
    print("\n## Test points (net must come from the netlist)")
    for t in tps:
        print("- " + " | ".join(t))
    print("\n## Power symbols whose value differs from the library symbol")
    for o in odd_power or [("none", "", "", "")]:
        print("- " + " | ".join(o))


if __name__ == "__main__":
    main()
