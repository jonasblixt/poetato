#!/usr/bin/env python3
"""Trace widths for the controlled-impedance classes (doc/pcb-stackup.md).

A 2D electrostatic field solver: finite differences on a nonuniform grid,
cell-centred permittivity, the energy of the solved potential gives the
capacitance per unit length. Z0 = 1 / (c0 * sqrt(C * C_air)); differential
impedance is twice the odd-mode impedance.

Model:
  - outer layers (L1/L6): trace on the laminate, reference plane below,
    solder mask (MASK_DK; MASK_SUB over laminate, MASK_TOP over copper), air
  - inner layer (L3): trace on the lower face of the L2-L3 core, embedded in
    the prepreg below, with the next plane (L4) below the full dielectric
  - rectangular trace cross-section (real traces are trapezoidal), grounded
    box 3 mm to the sides and 5 mm above, far enough not to matter

Expect about +-5 % against the fab. JLCPCB's impedance calculator is the
reference for the order; this script is for comparing stackups and for the
starting widths.

    python doc/scripts/impedance.py                 # JLC06161H-2116A
    python doc/scripts/impedance.py --stackup all   # the four candidates
    python doc/scripts/impedance.py --check         # analytic sanity checks

Needs numpy and scipy (pip install numpy scipy).
"""
import argparse

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.optimize import brentq

C0 = 299792458.0
EPS0 = 8.8541878128e-12
MM = 1e-3

MASK_DK = 3.8
MASK_SUB = 0.030 * MM
MASK_TOP = 0.015 * MM
CU_OUTER = 0.035 * MM
CU_INNER = 0.0152 * MM

# Dk from JLCPCB's impedance page
DK = {"1080": 3.91, "3313": 4.1, "2116": 4.16, "7628": 4.4, "core": 4.6}

# Thin-core JLCPCB 6-layer stackups that suit Sig/GND/Sig/PWR/GND/Sig.
# name: (outer prepreg, L1-L2 mm, L2-L3 core mm, dielectric L3 -> L4 [(mm, Dk)])
STACKUPS = {
    "2116A": ("2116", 0.1164, 0.13,
              [(0.1164, DK["2116"]), (0.70, DK["core"]), (0.1164, DK["2116"])]),
    "1080B": ("1080", 0.0764, 0.10,
              [(0.2104, DK["7628"]), (0.70, DK["core"]), (0.2104, DK["7628"])]),
    "1080C": ("1080", 0.0764, 0.075,
              [(0.2104, DK["7628"]), (0.70, DK["core"]), (0.2104, DK["7628"])]),
    "3313E": ("3313", 0.0994, 0.10,
              [(0.2104, DK["7628"]), (0.70, DK["core"]), (0.2104, DK["7628"])]),
}

# (label, ohms, gap mm or None for single-ended)
CLASSES = [
    ("50 ohm SE", 50, None),
    ("90 ohm diff", 90, 0.15),
    ("100 ohm diff", 100, 0.20),
]


def axis(keys, lo, hi, fine, coarse, grow=1.25):
    """Grid lines through every key point, fine at the keys, growing between."""
    keys = sorted(set([lo, hi] + [k for k in keys if lo <= k <= hi]))
    pts = [lo]
    for a, b in zip(keys[:-1], keys[1:]):
        length = b - a
        left, x, d = [], 0.0, fine
        while x + d < length / 2:
            x += d
            left.append(x)
            d = min(d * grow, coarse)
        right = [length - v for v in reversed(left)]
        seg = left + ([length / 2] if length > 2 * fine else []) + right
        pts += [a + v for v in sorted(set(round(v, 12) for v in seg)) if 0 < v < length] + [b]
    return np.array(sorted(set(round(p, 12) for p in pts)))


def energy(conductors, x, y, eps_fn):
    """Field energy per unit length for conductors [(x0, x1, y0, y1, V)]."""
    nx, ny = len(x), len(y)
    dx, dy = np.diff(x), np.diff(y)
    xc, yc = (x[:-1] + x[1:]) / 2, (y[:-1] + y[1:]) / 2
    XC, YC = np.meshgrid(xc, yc, indexing="ij")
    E = eps_fn(XC, YC)

    idx = np.arange(nx * ny).reshape(nx, ny)
    fixed = np.zeros((nx, ny), bool)
    vfix = np.zeros((nx, ny))
    fixed[0, :] = fixed[-1, :] = fixed[:, 0] = fixed[:, -1] = True
    X, Y = np.meshgrid(x, y, indexing="ij")
    tol = 1e-12
    for x0, x1, y0, y1, v in conductors:
        m = (X >= x0 - tol) & (X <= x1 + tol) & (Y >= y0 - tol) & (Y <= y1 + tol)
        fixed |= m
        vfix[m] = v

    # edge conductances from the permittivity of the cells either side
    ex = np.zeros((nx - 1, ny))
    ex[:, 1:] += E * dy[None, :] / 2
    ex[:, :-1] += E * dy[None, :] / 2
    ey = np.zeros((nx, ny - 1))
    ey[1:, :] += E * dx[:, None] / 2
    ey[:-1, :] += E * dx[:, None] / 2
    a = np.concatenate([idx[:-1, :].ravel(), idx[:, :-1].ravel()])
    b = np.concatenate([idx[1:, :].ravel(), idx[:, 1:].ravel()])
    g = np.concatenate([(ex / dx[:, None]).ravel(), (ey / dy[None, :]).ravel()])

    n = nx * ny
    lap = sp.coo_matrix((np.concatenate([-g, -g, g, g]),
                         (np.concatenate([a, b, a, b]), np.concatenate([b, a, a, b]))),
                        shape=(n, n)).tocsr()
    f = fixed.ravel()
    v = vfix.ravel().copy()
    v[~f] = spla.spsolve(lap[~f][:, ~f].tocsc(), -lap[~f][:, f] @ v[f])
    return 0.5 * np.sum(g * (v[a] - v[b]) ** 2) * EPS0


class Layer:
    """One signal layer. 'outer': h1/e1 is the dielectric to the plane below.
    'inner': h1/e1 is the core to the plane above, below is [(thick, Dk)] to
    the plane below, starting at the trace's lower face."""

    def __init__(self, kind, t, h1, e1, below=None, fine=2e-6, coarse=60e-6,
                 lid=5 * MM, side=3 * MM):
        self.kind, self.t, self.h1, self.e1 = kind, t, h1, e1
        self.below = below or []
        self.h2 = sum(th for th, _ in self.below)
        self.fine, self.coarse, self.lid, self.side = fine, coarse, lid, side

    def _cap(self, w, s, air):
        t = self.t
        traces = [(-w / 2, w / 2)] if s is None else [(-s / 2 - w, -s / 2), (s / 2, s / 2 + w)]
        xl = (w if s is None else 2 * w + s) / 2 + self.side
        x = axis([p for tr in traces for p in tr] + [0.0], -xl, xl, self.fine, self.coarse)

        if self.kind == "outer":
            h = self.h1
            y = axis([0, h, h + t, h + MASK_SUB, h + t + MASK_TOP],
                     -10e-6, h + t + self.lid, self.fine, self.coarse)
            planes = [(-xl, xl, -10e-6, 0.0, 0.0)]
            ty = (h, h + t)

            def eps(X, Y):
                e = np.ones_like(X)
                if air:
                    return e
                e[Y < h] = self.e1
                m = (Y >= h) & (Y < h + MASK_SUB)
                for x0, x1 in traces:
                    m |= (X > x0 - MASK_TOP) & (X < x1 + MASK_TOP) & (Y >= h) & (Y < h + t + MASK_TOP)
                e[m] = MASK_DK
                return e
        else:
            h1, h2 = self.h1, self.h2
            y = axis([0, -t, h1, -h2], -h2 - 10e-6, h1 + 10e-6, self.fine, self.coarse)
            planes = [(-xl, xl, h1, h1 + 10e-6, 0.0), (-xl, xl, -h2 - 10e-6, -h2, 0.0)]
            ty = (-t, 0.0)

            def eps(X, Y):
                e = np.full_like(X, 1.0 if air else self.e1)
                if air:
                    return e
                top = 0.0
                for th, er in self.below:
                    e[(Y < top) & (Y >= top - th)] = er
                    top -= th
                e[Y < top] = self.below[-1][1]
                return e

        if s is None:
            cond = planes + [(traces[0][0], traces[0][1], ty[0], ty[1], 1.0)]
            return 2 * energy(cond, x, y, eps)          # W = C V^2 / 2
        cond = planes + [(traces[0][0], traces[0][1], ty[0], ty[1], 1.0),
                         (traces[1][0], traces[1][1], ty[0], ty[1], -1.0)]
        return energy(cond, x, y, eps)                  # +-1 V: W = C_odd

    def impedance(self, w, s=None):
        z = 1 / (C0 * np.sqrt(self._cap(w, s, False) * self._cap(w, s, True)))
        return z if s is None else 2 * z

    def width_for(self, z, s=None):
        return brentq(lambda w: self.impedance(w, s) - z, 0.04 * MM, 0.6 * MM, xtol=1e-7)


def layers(name):
    pp, outer, core, below = STACKUPS[name]
    return [
        ("L1/L6", Layer("outer", CU_OUTER, outer * MM, DK[pp])),
        ("L3", Layer("inner", CU_INNER, core * MM, DK["core"],
                     below=[(th * MM, er) for th, er in below])),
    ]


def check():
    from scipy.special import ellipk
    # centred stripline, thin strip: Cohn's exact zero-thickness result
    b, er, w, t = 0.4 * MM, 4.0, 0.2 * MM, 1e-6
    st = Layer("inner", t, (b - t) / 2, er, below=[((b - t) / 2, er)], fine=t)
    k = 1 / np.cosh(np.pi * w / (2 * b))
    exact = 30 * np.pi / np.sqrt(er) * ellipk(k ** 2) / ellipk(1 - k ** 2)
    print(f"stripline   FD {st.impedance(w):6.2f}  exact (t=0) {exact:6.2f}")
    # microstrip without mask: Hammerstad-Jensen with thickness correction
    h, w, t, er = 0.2 * MM, 0.36 * MM, 35e-6, 4.4
    global MASK_SUB, MASK_TOP
    MASK_SUB = MASK_TOP = 0.0
    ms = Layer("outer", t, h, er)
    dw = t / np.pi * np.log(1 + 4 * np.e / (t / h * (1 / np.tanh(np.sqrt(6.517 * w / h))) ** 2))
    u = (w + dw * (1 + 1 / np.cosh(np.sqrt(er - 1))) / 2) / h
    f = 6 + (2 * np.pi - 6) * np.exp(-(30.666 / u) ** 0.7528)
    a = 1 + np.log((u ** 4 + (u / 52) ** 2) / (u ** 4 + 0.432)) / 49 + np.log(1 + (u / 18.1) ** 3) / 18.7
    bb = 0.564 * ((er - 0.9) / (er + 3)) ** 0.053
    ee = (er + 1) / 2 + (er - 1) / 2 * (1 + 10 / u) ** (-a * bb)
    hj = 60 * np.log(f / u + np.sqrt(1 + 4 / u ** 2)) / np.sqrt(ee)
    print(f"microstrip  FD {ms.impedance(w):6.2f}  Hammerstad-Jensen {hj:6.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stackup", default="2116A", choices=list(STACKUPS) + ["all"])
    ap.add_argument("--check", action="store_true", help="run the analytic sanity checks")
    args = ap.parse_args()
    if args.check:
        check()
        return
    names = list(STACKUPS) if args.stackup == "all" else [args.stackup]
    print(f"{'stackup':15} {'layer':6} {'class':13} {'W mm':>6} {'S mm':>6}")
    for name in names:
        for lname, layer in layers(name):
            for label, z, s in CLASSES:
                w = layer.width_for(z, None if s is None else s * MM)
                gap = "-" if s is None else f"{s:.2f}"
                print(f"JLC06161H-{name:5} {lname:6} {label:13} {w / MM:6.3f} {gap:>6}", flush=True)


if __name__ == "__main__":
    main()
