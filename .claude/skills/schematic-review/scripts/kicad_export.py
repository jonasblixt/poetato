#!/usr/bin/env python3
"""Run kicad-cli on the root schematic: netlist (KiCad XML), ERC (JSON), PDF plot.

usage: kicad_export.py <root .kicad_sch> <output dir>
Exits 2 if kicad-cli cannot be found. Reads the schematic only.
"""
import glob, os, shutil, subprocess, sys

CANDIDATES = [
    r"C:\Program Files\KiCad\*\bin\kicad-cli.exe",
    "/mnt/c/Program Files/KiCad/*/bin/kicad-cli.exe",
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
]


def find_cli():
    for name in ("kicad-cli", "kicad-cli.exe"):
        p = shutil.which(name)
        if p:
            return p
    for pat in CANDIDATES:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sch, out = sys.argv[1], sys.argv[2]
    cli = find_cli()
    if not cli:
        print("kicad-cli not found on PATH or in the default install locations", file=sys.stderr)
        sys.exit(2)
    os.makedirs(out, exist_ok=True)
    base = os.path.splitext(os.path.basename(sch))[0]
    jobs = [
        ["sch", "export", "netlist", "--format", "kicadxml", "-o", os.path.join(out, base + ".xml"), sch],
        ["sch", "erc", "--format", "json", "--severity-all", "-o", os.path.join(out, base + "-erc.json"), sch],
        ["sch", "export", "pdf", "-o", os.path.join(out, base + ".pdf"), sch],
    ]
    print(subprocess.run([cli, "version"], capture_output=True, text=True).stdout.strip(), "at", cli)
    rc = 0
    for j in jobs:
        r = subprocess.run([cli] + j, capture_output=True, text=True)
        print(" ".join(j[:3]), "->", "ok" if r.returncode == 0 else f"FAILED ({r.returncode})")
        if r.returncode:
            rc = 1
            print(r.stdout + r.stderr)
    sys.exit(rc)


if __name__ == "__main__":
    main()
