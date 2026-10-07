#!/usr/bin/env python3
"""BOM availability and price check against the DigiKey Product Information API (v4).

Reads the KiCad schematic files (hw/poetato/*.kicad_sch), takes the
`Manufacturer` and `Part Number` fields of every placed symbol, groups them
into unique part numbers and looks each one up at DigiKey. Prints:

  1. one line per unique part number: value, quantity, DigiKey stock, status, price
  2. the total BOM price (and what the order actually costs once minimum
     order quantities are applied)
  3. the total BOM price at several build volumes (--volumes, default
     1, 100, 1000 and 10000 boards), using the price breaks of each volume,
     plus an "estimated real price": the DigiKey price scaled by a rule-of-
     thumb factor per part category (REAL_FACTOR at the top of this file)

Credentials (https://developer.digikey.com -> create a *production* app with
the "Product Information V4" API, client-credentials flow):

    DIGIKEY_CLIENT_ID, DIGIKEY_CLIENT_SECRET

as environment variables, as KEY=value lines in doc/scripts/.env
(git-ignored), or on the command line with --client-id / --client-secret
(these win over the other two).

    python doc/scripts/bom_digikey.py                  # 1 board, SE site, SEK
    python doc/scripts/bom_digikey.py --client-id ID --client-secret SECRET
    python doc/scripts/bom_digikey.py -n 5             # price 5 boards
    python doc/scripts/bom_digikey.py --md doc/bom.md --csv doc/bom.csv
    python doc/scripts/bom_digikey.py --dry-run        # only list the parts

Standard library only. Answers are cached for 24 h in
doc/scripts/.digikey_cache.json (the API allows 1000 calls per day);
--refresh ignores the cache. Schematic files are only read, never written.
"""
import argparse, csv, glob, json, os, re, sys, time
import urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SCH = os.path.normpath(os.path.join(HERE, "..", "..", "hw", "poetato"))
CACHE = os.path.join(HERE, ".digikey_cache.json")
API = "https://api.digikey.com"
NO_PN = {"", "N/A", "NA", "-", "~", "?", "TBD", "DNP"}

# Schematic manufacturer name (normalised) -> fragment of DigiKey's name.
MFR_ALIAS = {
    "ti": "texasinstruments", "st": "stmicro", "onsemi": "onsemi", "on": "onsemi",
    "littlefuse": "littelfuse", "diodesinc": "diodesincorporated", "chemicon": "chemicon",
    "wurthelektronik": "wurth", "wurth": "wurth", "nxp": "nxp", "rohm": "rohm",
    "skyworkssolutionsinc": "skyworks", "microchip": "microchip", "infineon": "infineon",
    "belfuse": "bel", "smcdiodesolutions": "smc", "panasonic": "panasonic",
}

# "Estimated real price": what a quoted/contract price is likely to be,
# as a fraction of DigiKey's volume price. Rule-of-thumb numbers, edit freely.
REAL_FACTOR = {
    "passive": 0.30,     # chip resistors, MLCCs, ferrite beads
    "discrete": 0.40,    # diodes, TVS, small FETs, LEDs
    "standard": 0.60,    # broad-line ICs, power inductors
    "specialty": 0.80,   # single-source ICs, magnetics, connectors, relays, crystals, fuses
}
REAL_MIN_BOARDS = 1000   # below this volume you pay catalog prices: factor 1.0
REAL_PREFIX = {"R": "passive", "C": "passive", "FB": "passive", "D": "discrete", "Q": "discrete",
               "U": "standard", "L": "standard"}          # any other reference prefix: specialty
SPECIALTY_PN = ("MCXN", "SE05", "SI3402", "KSZ8081")       # single-source ICs (part number starts with)
SPECIALTY_MFR = ("chemicon", "eaton")                      # electrolytics, supercap: not chip passives

# ---------------------------------------------------------------- schematic

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
            stack[-1].append(t[1:-1].replace('\\"', '"').replace("\\\\", "\\"))
        else:
            stack[-1].append(t)
    return stack[0][0]


def kids(node, name):
    return [x for x in node if isinstance(x, list) and x and x[0] == name]


def refkey(r):
    m = re.match(r"([^\d]*)(\d*)", r)
    return (m.group(1), int(m.group(2) or 0), r)


def clean_pn(pn):
    """'SN6507DGQR  ' -> 'SN6507DGQR', 'GA352QR7GF102KW01#' -> 'GA352QR7GF102KW01'."""
    return pn.strip().rstrip("#").strip()


def load_bom(sch_dir, include_dnp=False):
    """Return (lines, skipped). lines: {pn: {mfr, refs, value, desc, mfrs}}."""
    pro = glob.glob(os.path.join(sch_dir, "*.kicad_pro"))
    project = os.path.splitext(os.path.basename(pro[0]))[0] if len(pro) == 1 else None
    seen, lines, skipped = {}, {}, []
    files = sorted(glob.glob(os.path.join(sch_dir, "*.kicad_sch")))
    if not files:
        sys.exit(f"no *.kicad_sch files in {sch_dir}")
    for f in files:
        tree = parse(open(f, encoding="utf8").read())
        for s in kids(tree, "symbol"):
            if not kids(s, "lib_id"):
                continue
            props = {p[1]: p[2] for p in kids(s, "property") if len(p) > 2}
            # A sheet that is used several times has one reference per instance.
            inst = [(pr[1], r[1]) for i in kids(s, "instances") for pr in kids(i, "project")
                    for pa in kids(pr, "path") for r in kids(pa, "reference")]
            refs = {r for p, r in inst if p == project} or {r for _, r in inst} or {props.get("Reference", "?")}
            flag = lambda k, d: (kids(s, k) or [[k, d]])[0][1] == "yes"
            for ref in refs:
                if ref.startswith("#") or ref in seen:      # power symbol / other unit of same part
                    continue
                seen[ref] = True
                pn = clean_pn(props.get("Part Number", ""))
                mfr = props.get("Manufacturer", "").strip()
                if not flag("in_bom", "yes"):
                    skipped.append((ref, "not in BOM"))
                elif flag("dnp", "no") and not include_dnp:
                    skipped.append((ref, f"DNP ({pn or 'no part number'})"))
                elif pn.upper() in NO_PN:
                    if not re.match(r"(TP|FID|H|MH|NT|LOGO)\d", ref):
                        skipped.append((ref, "no part number"))
                else:
                    value = re.sub(r"\$\{([^}]+)\}", lambda m: props.get(m.group(1), m.group(0)), props.get("Value", ""))
                    e = lines.setdefault(pn, {"mfr": mfr, "mfrs": set(), "refs": [], "value": value,
                                              "desc": props.get("Description", "")})
                    e["refs"].append(ref)
                    e["mfrs"].add(mfr)
    for e in lines.values():
        e["refs"].sort(key=refkey)
    return lines, skipped


# ------------------------------------------------------------------ DigiKey

def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def mfr_match(sch, dk):
    a, b = norm(sch), norm(dk)
    if not a or not b:
        return False
    a = MFR_ALIAS.get(a, a)
    return a in b or b in a


class DigiKey:
    def __init__(self, cid, secret, site, currency, language):
        self.cid, self.secret = cid, secret
        self.locale = {"X-DIGIKEY-Locale-Site": site, "X-DIGIKEY-Locale-Currency": currency,
                       "X-DIGIKEY-Locale-Language": language}
        self.token = None

    def _open(self, req):
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf8", "replace")[:300]
                wait = int(e.headers.get("Retry-After") or 0)
                if e.code == 429 and wait <= 90 and attempt < 3:
                    print(f"  rate limited, waiting {wait or 5} s", file=sys.stderr)
                    time.sleep(wait or 5)
                    continue
                if e.code in (500, 502, 503, 504) and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"HTTP {e.code} from DigiKey: {body}") from None
            except urllib.error.URLError as e:
                if attempt == 3:
                    raise RuntimeError(f"cannot reach DigiKey: {e.reason}") from None
                time.sleep(2)

    def login(self):
        data = urllib.parse.urlencode({"client_id": self.cid, "client_secret": self.secret,
                                       "grant_type": "client_credentials"}).encode()
        self.token = self._open(urllib.request.Request(API + "/v1/oauth2/token", data=data))["access_token"]

    def search(self, pn):
        if not self.token:
            self.login()
        body = json.dumps({"Keywords": pn, "Limit": 20, "Offset": 0}).encode()
        hdr = {"Authorization": "Bearer " + self.token, "X-DIGIKEY-Client-Id": self.cid,
               "Content-Type": "application/json", "Accept": "application/json", **self.locale}
        return self._open(urllib.request.Request(API + "/products/v4/search/keyword", data=body, headers=hdr))


def slim(resp):
    """Keep only what the report needs (this is what goes into the cache)."""
    out, seen = [], set()
    for p in (resp.get("ExactMatches") or []) + (resp.get("Products") or []):
        key = (p.get("ManufacturerProductNumber"), (p.get("Manufacturer") or {}).get("Name"))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "mpn": p.get("ManufacturerProductNumber") or "",
            "mfr": (p.get("Manufacturer") or {}).get("Name") or "",
            "desc": (p.get("Description") or {}).get("ProductDescription") or "",
            "stock": p.get("QuantityAvailable") or 0,
            "status": (p.get("ProductStatus") or {}).get("Status") or "",
            "lead_weeks": p.get("ManufacturerLeadWeeks") or "",
            "url": p.get("ProductUrl") or "",
            "variations": [{
                "dkpn": v.get("DigiKeyProductNumber") or "",
                "package": (v.get("PackageType") or {}).get("Name") or "",
                "moq": v.get("MinimumOrderQuantity") or 1,
                "stock": v.get("QuantityAvailableforPackageType") or 0,
                "breaks": [(b["BreakQuantity"], b["UnitPrice"]) for b in v.get("StandardPricing") or []],
            } for v in p.get("ProductVariations") or []],
        })
    return out


def pick_product(pn, mfr, products):
    """Exact manufacturer part number first, then 'starts with' (packaging
    suffix not in the schematic, e.g. GRM155R71E104KE14 -> ...KE14D)."""
    n, cands = norm(pn), []
    for p in products:
        m = norm(p["mpn"])
        rank = 2 if m == n else 1 if m.startswith(n) else 0
        if rank:
            priced = any(v["breaks"] for v in p["variations"])
            cands.append((rank, mfr_match(mfr, p["mfr"]), priced, p["stock"] > 0, p["stock"], p))
    if not cands:
        return None, "not found"
    cands.sort(key=lambda c: c[:5], reverse=True)
    rank, mok, _, _, _, p = cands[0]
    notes = []
    if rank == 1:
        notes.append("matched " + p["mpn"])
    if not mok:
        notes.append(f"manufacturer differs ({p['mfr']})")
    return p, "; ".join(notes)


def pick_price(product, need):
    """Cheapest way to buy `need` pieces. Returns dict or None."""
    best = None
    for v in product["variations"]:
        if not v["breaks"] or "digi-reel" in v["package"].lower():   # re-reeling fee, never cheapest
            continue
        breaks = sorted(v["breaks"])
        qty = max(need, v["moq"], breaks[0][0])
        unit = [u for q, u in breaks if q <= qty][-1]
        o = {"dkpn": v["dkpn"], "package": v["package"], "order_qty": qty, "unit": unit,
             "order_cost": qty * unit, "in_stock": v["stock"] >= qty}
        if best is None or (not o["in_stock"], o["order_cost"]) < (not best["in_stock"], best["order_cost"]):
            best = o
    return best


def real_category(pn, e):
    """Discount category of a BOM line, a key of REAL_FACTOR."""
    if pn.upper().startswith(SPECIALTY_PN) or norm(e["mfr"]) in SPECIALTY_MFR:
        return "specialty"
    return REAL_PREFIX.get(re.match(r"[A-Za-z]*", e["refs"][0]).group(0).upper(), "specialty")


def volume_pricing(lines, cache, site, currency, volumes):
    """Total BOM price when building 1, 100, 1000 ... boards.

    Every part is re-priced at (quantity per board x boards), so the price
    breaks and reel packaging of the larger volumes are used. Returns one
    dict per volume: boards, per_board, total (qty x unit price), order
    (with minimum order quantities), real / real_per_board (estimated
    negotiated price: total scaled per part by REAL_FACTOR from
    REAL_MIN_BOARDS boards and up), unpriced and short (part numbers
    without a price / with less DigiKey stock than needed).
    """
    out = []
    for boards in volumes:
        r = {"boards": boards, "total": 0.0, "order": 0.0, "real": 0.0, "unpriced": [], "short": []}
        for pn, e in lines.items():
            need = len(e["refs"]) * boards
            hit = cache.get(f"{site}/{currency}/{pn}")
            p = pick_product(pn, e["mfr"], hit["products"])[0] if hit else None
            price = pick_price(p, need) if p else None
            if not price:
                r["unpriced"].append(pn)
                continue
            r["total"] += need * price["unit"]
            r["real"] += need * price["unit"] * (REAL_FACTOR[real_category(pn, e)] if boards >= REAL_MIN_BOARDS else 1.0)
            r["order"] += price["order_cost"]
            if p["stock"] < need:
                r["short"].append(pn)
        r["per_board"] = r["total"] / boards
        r["real_per_board"] = r["real"] / boards
        out.append(r)
    return out


# ------------------------------------------------------------------- output

def refs_short(refs, n=6):
    return ",".join(refs) if len(refs) <= n else ",".join(refs[:n]) + f",+{len(refs) - n}"


def money(x):
    return "" if x is None else f"{x:,.2f}".replace(",", " ")


def table(rows, head, right=()):
    w = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
    fmt = lambda r: "  ".join(str(c).rjust(w[i]) if i in right else str(c).ljust(w[i]) for i, c in enumerate(r)).rstrip()
    return "\n".join([fmt(head), "  ".join("-" * x for x in w)] + [fmt(r) for r in rows])


def load_env():
    for path in (os.path.join(HERE, ".env"), os.path.join(HERE, "..", "..", ".env")):
        if os.path.isfile(path):
            for line in open(path, encoding="utf8"):
                m = re.match(r"\s*(?:export\s+)?([A-Z_]+)\s*=\s*(.*?)\s*$", line)
                if m:
                    os.environ.setdefault(m.group(1), m.group(2).strip("\"'"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("schematic_dir", nargs="?", default=DEFAULT_SCH, help="folder with *.kicad_sch (default: hw/poetato)")
    ap.add_argument("-n", "--boards", type=int, default=1, help="number of boards to price (default 1)")
    ap.add_argument("--volumes", default="1,100,1000,10000", metavar="LIST",
                    help="board volumes for the volume price table (default 1,100,1000,10000; '' to skip)")
    ap.add_argument("--site", default="SE", help="DigiKey site, sets stock/price region (default SE)")
    ap.add_argument("--currency", default="SEK")
    ap.add_argument("--language", default="en")
    ap.add_argument("--client-id", metavar="ID", help="DigiKey API client id (default: DIGIKEY_CLIENT_ID)")
    ap.add_argument("--client-secret", metavar="SECRET", help="DigiKey API client secret (default: DIGIKEY_CLIENT_SECRET)")
    ap.add_argument("--include-dnp", action="store_true", help="also price parts marked do-not-populate")
    ap.add_argument("--csv", metavar="FILE", help="write the summary as CSV")
    ap.add_argument("--md", metavar="FILE", help="write the summary as Markdown")
    ap.add_argument("--refresh", action="store_true", help="ignore cached DigiKey answers")
    ap.add_argument("--dry-run", action="store_true", help="list the extracted parts, do not call DigiKey")
    a = ap.parse_args()
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf8", errors="replace")

    lines, skipped = load_bom(a.schematic_dir, a.include_dnp)
    total_parts = sum(len(e["refs"]) for e in lines.values())
    print(f"{total_parts} parts, {len(lines)} unique part numbers in {a.schematic_dir}")
    for pn, e in lines.items():
        if len(e["mfrs"]) > 1:
            print(f"  warning: {pn} has several manufacturer spellings: {sorted(e['mfrs'])}")
    if skipped:
        by = {}
        for ref, why in skipped:
            by.setdefault(why, []).append(ref)
        for why, refs in by.items():
            print(f"  skipped, {why}: {refs_short(sorted(refs, key=refkey), 12)}")

    if a.dry_run:
        rows = [[pn, e["mfr"], len(e["refs"]), e["value"], refs_short(e["refs"])] for pn, e in sorted(lines.items())]
        print("\n" + table(rows, ["Part number", "Manufacturer", "Qty", "Value", "Refs"], right=(2,)))
        return

    load_env()
    cid = a.client_id or os.environ.get("DIGIKEY_CLIENT_ID")
    secret = a.client_secret or os.environ.get("DIGIKEY_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit("No DigiKey credentials: use --client-id/--client-secret, or set DIGIKEY_CLIENT_ID and "
                 "DIGIKEY_CLIENT_SECRET (environment or doc/scripts/.env). See --help.")
    dk = DigiKey(cid, secret, a.site, a.currency, a.language)

    try:
        cache = json.load(open(CACHE, encoding="utf8"))
    except (OSError, ValueError):
        cache = {}
    now, error = time.time(), None
    for i, pn in enumerate(sorted(lines), 1):
        key = f"{a.site}/{a.currency}/{pn}"
        hit = cache.get(key)
        if hit and not a.refresh and now - hit["t"] < 86400:
            continue
        print(f"\r  DigiKey {i}/{len(lines)} {pn:<32}", end="", file=sys.stderr, flush=True)
        try:
            cache[key] = {"t": now, "products": slim(dk.search(pn))}
        except RuntimeError as e:
            error = str(e)
            break
        time.sleep(0.6)                      # stay under 120 requests/minute
    print("\r" + " " * 60 + "\r", end="", file=sys.stderr)
    with open(CACHE, "w", encoding="utf8") as f:
        json.dump(cache, f)
    if error:
        print(f"\nDigiKey lookup stopped: {error}\nParts not fetched are listed as 'not looked up'.", file=sys.stderr)

    head = ["Part number", "Manufacturer", "Value", "Qty", "Refs", "Stock", "Status", f"Unit {a.currency}", f"Ext {a.currency}",
            "Buy", f"Order {a.currency}", "DigiKey PN", "Note"]
    rows, bom_total, order_total, problems = [], 0.0, 0.0, []
    for pn in sorted(lines):
        e = lines[pn]
        need = len(e["refs"]) * a.boards
        row = [pn, e["mfr"], e["value"], need, refs_short(e["refs"]), "", "", "", "", "", "", "", ""]
        hit = cache.get(f"{a.site}/{a.currency}/{pn}")
        if not hit:
            row[-1] = "not looked up"
        else:
            p, note = pick_product(pn, e["mfr"], hit["products"])
            if p:
                price = pick_price(p, need)
                notes = [note] if note else []
                row[5], row[6] = p["stock"], p["status"]
                if p["status"] and p["status"].lower() != "active":
                    notes.append("not active")
                if p["stock"] < need:
                    notes.append(f"short of stock, lead {p['lead_weeks'] or '?'} wk")
                if price:
                    ext = need * price["unit"]
                    bom_total += ext
                    order_total += price["order_cost"]
                    row[7:12] = [f"{price['unit']:.4f}".rstrip("0").rstrip("."), money(ext), price["order_qty"],
                                 money(price["order_cost"]), price["dkpn"]]
                    if price["order_qty"] > need:
                        notes.append(f"min order {price['order_qty']}")
                else:
                    notes.append("no price")
                row[-1] = "; ".join(notes)
            else:
                row[-1] = note
        if row[7] == "":
            problems.append(pn)
        rows.append(row)

    right = (3, 5, 7, 8, 9, 10)
    print("\n" + table(rows, head, right))
    summary = [
        f"Boards: {a.boards}   DigiKey site: {a.site}   prices in {a.currency}, excluding VAT and shipping",
        f"Total BOM price (qty x unit price): {money(bom_total)} {a.currency}"
        + (f"   = {money(bom_total / a.boards)} {a.currency} per board" if a.boards > 1 else ""),
        f"Order total (with minimum order quantities): {money(order_total)} {a.currency}",
    ]
    if problems:
        summary.append(f"NOT included in the totals, no price for {len(problems)} of {len(lines)} part numbers: "
                       + ", ".join(problems))
    print("\n" + "\n".join(summary))

    try:
        volumes = [int(v) for v in a.volumes.replace(" ", "").split(",") if v]
    except ValueError:
        sys.exit("--volumes must be a comma separated list of numbers, e.g. 1,100,1000,10000")
    vhead = ["Boards", f"Per board {a.currency}", f"Total {a.currency}", f"Order total {a.currency}",
             f"Est. real per board {a.currency}", f"Est. real total {a.currency}", "No price", "Short of stock"]
    vrows = [[v["boards"], money(v["per_board"]), money(v["total"]), money(v["order"]), money(v["real_per_board"]), money(v["real"]),
              len(v["unpriced"]), len(v["short"])]
             for v in volume_pricing(lines, cache, a.site, a.currency, volumes)]
    vnote = ("'No price' part numbers are not in the totals; 'Short of stock' = part numbers where DigiKey "
             "stock is below the quantity needed.\n"
             f"Estimated real price = DigiKey price x a factor per part category from {REAL_MIN_BOARDS} boards ("
             + ", ".join(f"{k} {v:g}" for k, v in REAL_FACTOR.items()) + "); a rule of thumb, not a quote.")
    if vrows:
        print("\nTotal BOM price by volume\n" + table(vrows, vhead, right=range(len(vhead))) + "\n" + vnote)

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(head)
            for pn, r in zip(sorted(lines), rows):
                w.writerow(r[:4] + [" ".join(lines[pn]["refs"])] + r[5:])
        print(f"wrote {a.csv}")
    if a.md:
        esc = lambda c: str(c).replace("|", "\\|")
        with open(a.md, "w", encoding="utf8") as f:
            f.write(f"# BOM price and availability ({time.strftime('%Y-%m-%d')})\n\n")
            f.write("\n".join("- " + s for s in summary) + "\n\n")
            f.write("| " + " | ".join(head) + " |\n|" + "|".join("--:" if i in right else "---" for i in range(len(head))) + "|\n")
            for r in rows:
                f.write("| " + " | ".join(esc(c) for c in r) + " |\n")
            if vrows:
                f.write("\n## Total BOM price by volume\n\n| " + " | ".join(vhead) + " |\n|" + "--:|" * len(vhead) + "\n")
                for r in vrows:
                    f.write("| " + " | ".join(str(c) for c in r) + " |\n")
                f.write("\n" + vnote + "\n")
        print(f"wrote {a.md}")


if __name__ == "__main__":
    main()
