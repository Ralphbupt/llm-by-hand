"""Check that the color tokens in site/src/styles/global.css stay apart (see AUTHORING.md "Color tokens").

Any two of the tokens below can appear in the same lab, so each pair must be easy to tell apart:
CIE76 color difference (Delta E) of at least MIN_DE, in the light and in the dark theme.
Each of them must also stand out from the background (contrast at least 3:1, for lines and marks), and must not
look like the neutral ink a lab draws with anyway (--fg text, --dim axes and grid labels, --line hairlines): a
series in a color that matches the grid reads as part of the grid.
A plain tensor block in the 3D nets (--card mixed toward --fg in linear light, see colorOf in Net3D.svelte) must
stand out from the page: contrast at least MIN_BLOCK against --bg in both themes.

Usage:  python scripts/check_tokens.py [--table]
Exit code 1 when a pair is too close or a token is too faint.
"""
import itertools
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = ROOT / "site/src/styles/global.css"
TOKENS = ["accent", "ok", "warn", "pos", "neg", "grad", "cat-1", "cat-2", "cat-3", "cat-4", "cat-5"]
NEUTRALS = ["fg", "dim", "line"]
MIN_DE = 15.0
MIN_CONTRAST = 3.0
MIN_BLOCK = 1.5
# how much --fg goes into --card for a plain block face (Net3D.svelte colorOf: 0.14, times 2.4 in the light theme)
BLOCK_MIX = {"light": 0.14 * 2.4, "dark": 0.14}


def parse(block: str) -> dict[str, str]:
    return {m[1]: m[2].lower() for m in re.finditer(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", block)}


def themes(css: str) -> dict[str, dict[str, str]]:
    light = parse(css[css.index(":root {"): css.index("}", css.index(":root {"))])
    i = css.index(':root[data-theme="dark"]')
    dark = {**light, **parse(css[i: css.index("}", i)])}
    return {"light": light, "dark": dark}


def lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb(h: str) -> tuple[float, float, float]:
    return tuple(int(h[i: i + 2], 16) / 255 for i in (1, 3, 5))  # type: ignore[return-value]


def lab(h: str) -> tuple[float, float, float]:
    r, g, b = (lin(c) for c in rgb(h))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116  # noqa: E731
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a: str, b: str) -> float:
    return sum((p - q) ** 2 for p, q in zip(lab(a), lab(b))) ** 0.5


def contrast(a: str, b: str) -> float:
    la, lb = (0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(bl) for r, g, bl in (rgb(a), rgb(b)))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def main() -> int:
    bad = 0
    for name, t in themes(CSS.read_text()).items():
        missing = [k for k in TOKENS + NEUTRALS + ["bg"] if k not in t]
        if missing:
            print(f"{name}: missing tokens {missing}")
            return 1
        worst = []
        for a, b in itertools.combinations(TOKENS, 2):
            d = delta_e(t[a], t[b])
            worst.append((d, a, b))
            if d < MIN_DE:
                print(f"{name}: --{a} {t[a]} and --{b} {t[b]} are too close (Delta E {d:.1f} < {MIN_DE})")
                bad += 1
        for a, b in itertools.product(TOKENS, NEUTRALS):
            d = delta_e(t[a], t[b])
            worst.append((d, a, b))
            if d < MIN_DE:
                print(f"{name}: --{a} {t[a]} and the neutral --{b} {t[b]} are too close (Delta E {d:.1f} < {MIN_DE})")
                bad += 1
        for k in TOKENS:
            c = contrast(t[k], t["bg"])
            if c < MIN_CONTRAST:
                print(f"{name}: --{k} {t[k]} is too faint on --bg (contrast {c:.2f} < {MIN_CONTRAST})")
                bad += 1
        mix = BLOCK_MIX["dark" if "dark" in name else "light"]
        face_lin = [lin(c) + mix * (lin(f) - lin(c)) for c, f in zip(rgb(t["card"]), rgb(t["fg"]))]
        face_l = 0.2126 * face_lin[0] + 0.7152 * face_lin[1] + 0.0722 * face_lin[2]
        bg_l = sum(w * lin(c) for w, c in zip((0.2126, 0.7152, 0.0722), rgb(t["bg"])))
        cb = (max(face_l, bg_l) + 0.05) / (min(face_l, bg_l) + 0.05)
        if cb < MIN_BLOCK:
            print(f"{name}: a plain 3D block face is too faint on --bg (contrast {cb:.2f} < {MIN_BLOCK})")
            bad += 1
        worst.sort()
        if "--table" in sys.argv:
            for d, a, b in worst[:8]:
                print(f"  {name}: {a:7s} {b:7s} {d:5.1f}")
        print(f"{name}: closest pair --{worst[0][1]} / --{worst[0][2]} (Delta E {worst[0][0]:.1f})")
    print("ok" if not bad else f"{bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
