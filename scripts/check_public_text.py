"""The text the site publishes for search engines and AI assistants must never give an answer away.

Builds the site (unless --no-build), then reads every machine-readable text output in site/dist:
  llms.txt, llms-full.txt, learn/<slug>.md, and the JSON-LD blocks of every HTML page.
and looks in them for every distinctive answer from content/*/*/exercises.yaml:
  `solution` and boss `reference` code (each line), `reveal` and `after` notes, and hint texts (`say`).
A value counts as distinctive when it is at least MIN characters long once whitespace is collapsed.

Text a page prints anyway (the same line in some lesson's prose, e.g. code shown after a gate, or in a question's
prompt, template or options, e.g. a later template that starts from an earlier answer) is not a leak of the export:
it is counted as "printed on a page anyway" and does not fail the check.

  .venv/bin/python scripts/check_public_text.py            # build, then check
  .venv/bin/python scripts/check_public_text.py --no-build # check the existing site/dist (or $DIST)
Exit code 1 when an answer shows up.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIST = pathlib.Path(__import__("os").environ.get("DIST", ROOT / "site" / "dist"))
MIN = 25

QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "−": "-", "–": "-", "—": "-", " ": " "})


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).translate(QUOTES)).strip()


def secrets():
    """(slug, exercise id, field, normalized text, shown on a page anyway) for every distinctive answer-like value.
    "Shown anyway": the same text is in some lesson's prose, or in a question's prompt, template or options
    (a later question often starts from an earlier answer), so the page itself prints it."""
    files = sorted(ROOT.glob("content/*/*/exercises.yaml"))
    loaded = [(y.parent.name, yaml.safe_load(y.read_text(encoding="utf-8")) or {}) for y in files]
    public = " ".join(norm(p.read_text(encoding="utf-8")) for p in ROOT.glob("content/*/*/lesson.en.mdx"))
    for _, data in loaded:
        for ex in data.values():
            if isinstance(ex, dict):
                public += " " + norm(ex.get("prompt", "")) + " " + norm(ex.get("template", "")) + " " + " ".join(norm(o) for o in ex.get("options") or [])
    for slug, data in loaded:
        for ex_id, ex in data.items():
            if not isinstance(ex, dict):
                continue
            vals = []
            for field in ("solution", "reference"):
                if isinstance(ex.get(field), str):
                    vals += [(field, line) for line in ex[field].splitlines()]
            for field in ("reveal", "after"):
                if isinstance(ex.get(field), str):
                    vals.append((field, ex[field]))
            if isinstance(ex.get("answer"), str):
                vals.append(("answer", ex["answer"]))
            for h in ex.get("hints") or []:
                say = h.get("say") if isinstance(h, dict) else None
                for s in ([say] if isinstance(say, str) else say or []):
                    vals.append(("hint", s))
            for field, v in vals:
                n = norm(v)
                if len(n) >= MIN:
                    yield slug, ex_id, field, n, n in public


def outputs():
    """(name, normalized text) of every public machine-readable text file."""
    for p in [DIST / "llms.txt", DIST / "llms-full.txt", *sorted((DIST / "learn").glob("*.md"))]:
        if p.exists():
            yield str(p.relative_to(DIST)), norm(p.read_text(encoding="utf-8"))
    for p in sorted(DIST.rglob("*.html")):
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', p.read_text(encoding="utf-8"), re.S)
        for i, b in enumerate(blocks):
            json.loads(b)  # must parse
            yield f"{p.relative_to(DIST)} (JSON-LD {i + 1})", norm(b)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-build", action="store_true", help="check the existing site/dist")
    args = ap.parse_args()
    if not args.no_build:
        r = subprocess.run(["npx", "astro", "build"], cwd=ROOT / "site", capture_output=True, text=True)
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-2000:])
            return 1
    outs = list(outputs())
    if not any(n.endswith(".md") for n, _ in outs):
        print("no learn/*.md in site/dist: build first")
        return 1
    leaks, shown, checked = [], set(), 0
    for slug, ex_id, field, text, in_lesson in secrets():
        checked += 1
        for name, body in outs:
            if text not in body:
                continue
            if in_lesson:
                shown.add((slug, ex_id, field))
            else:
                leaks.append((name, slug, ex_id, field, text))
    for name, slug, ex_id, field, text in leaks:
        print(f"LEAK {name}: {slug}/{ex_id} {field}: {text[:90]}")
    if shown:
        print(f"{len(shown)} answer lines are printed on a page anyway (lesson prose or another question): not counted")
    print(f"public text: {len(outs)} outputs, {checked} distinctive answers checked, {len(leaks)} leaks")
    return 1 if leaks else 0


if __name__ == "__main__":
    sys.exit(main())
