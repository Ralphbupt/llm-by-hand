"""Check the Chinese translation against the English source (content/TRANSLATING.zh.md).

For every level with lesson.zh.mdx or exercises.zh.yaml:
  - lesson.zh.mdx has the same imports, the same components with the same ids/props, in the same order,
    the same code blocks and the same display math as lesson.en.mdx, and the same number of ## sections
  - exercises.zh.yaml has only ids from exercises.yaml, only text fields, and as many options / hints / tests
    (and ladder rungs) as the English; a translated template keeps every code line (comments may change)
Also: content/levels.zh.yaml names only real levels; content/glossary.zh.yaml names only real terms.

    python scripts/check_zh.py            # all levels
    python scripts/check_zh.py matrices   # one level
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
TEXT_FIELDS = {"prompt", "promptShort", "after", "reveal", "unit", "options", "hints", "tests", "template"}
errors: list[str] = []


def err(where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


def body(src: str) -> str:
    m = re.match(r"^---\n.*?\n---\n", src, re.S)
    return src[m.end():] if m else src


def components(src: str) -> list[str]:
    """Every JSX tag outside code blocks, with its props except the human-readable ones."""
    s = re.sub(r"```.*?```", "", body(src), flags=re.S)
    out = []
    for m in re.finditer(r"<(/?)([A-Z]\w*)((?:\s+[\w:-]+(?:=(?:\"[^\"]*\"|'[^']*'|\{\{.*?\}\}|\{[^}]*\}))?)*)\s*(/?)>", s, re.S):
        close, name, props, selfclose = m.groups()
        props = re.sub(r"\s(title|q)=(\"[^\"]*\"|'[^']*')", "", props)
        out.append(f"<{close}{name}{' '.join(props.split())}{selfclose}>")
    return out


def code_blocks(src: str) -> list[str]:
    return [strip_comments(b) for b in re.findall(r"```.*?```", body(src), re.S)]


def strip_comments(code: str) -> str:
    return "\n".join(re.sub(r"\s*#.*$", "", line).rstrip() for line in code.split("\n")).strip()


def display_math(src: str) -> list[str]:
    s = re.sub(r"```.*?```", "", body(src), flags=re.S)
    return [" ".join(x.split()) for x in re.findall(r"\$\$(.*?)\$\$", s, re.S)]


def imports(src: str) -> list[str]:
    return [l.strip() for l in body(src).split("\n") if l.startswith("import ")]


def sections(src: str) -> int:
    s = re.sub(r"```.*?```", "", body(src), flags=re.S)
    return len(re.findall(r"^## ", s, re.M))


def check_lesson(d: Path) -> None:
    en, zh = (d / "lesson.en.mdx").read_text(), (d / "lesson.zh.mdx").read_text()
    w = f"{d.name}/lesson.zh.mdx"
    fm = re.match(r"^---\n(.*?)\n---\n", zh, re.S)
    if fm:
        extra = set((yaml.safe_load(fm.group(1)) or {}).keys()) - {"recap", "glossarySkip"}
        if extra:
            err(w, f"frontmatter may only hold recap and glossarySkip, not {sorted(extra)}")
    if imports(en) != imports(zh):
        err(w, "imports differ from lesson.en.mdx")
    a, b = components(en), components(zh)
    if a != b:
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                err(w, f"component #{i + 1} differs: English {x} / Chinese {y}")
                break
        else:
            err(w, f"{len(a)} components in English, {len(b)} in Chinese")
    if code_blocks(en) != code_blocks(zh):
        err(w, "code blocks differ (only comments may change)")
    if display_math(en) != display_math(zh):
        err(w, "display math ($$…$$) differs")
    if sections(en) != sections(zh):
        err(w, f"{sections(en)} ## sections in English, {sections(zh)} in Chinese")


def check_exercises(d: Path) -> None:
    en = yaml.safe_load((d / "exercises.yaml").read_text()) or {}
    zh = yaml.safe_load((d / "exercises.zh.yaml").read_text()) or {}
    for qid, t in zh.items():
        w = f"{d.name}/exercises.zh.yaml {qid}"
        if qid not in en:
            err(w, "no such id in exercises.yaml")
            continue
        e = en[qid]
        bad = set(t) - TEXT_FIELDS
        if bad:
            err(w, f"only text fields belong here, not {sorted(bad)}")
        for k in ("prompt", "promptShort", "after", "reveal", "unit"):
            if k in t and k not in e:
                err(w, f"English has no {k}")
        if "options" in t and len(t["options"]) != len(e.get("options", [])):
            err(w, f"{len(e.get('options', []))} options in English, {len(t['options'])} here")
        if "hints" in t:
            eh = e.get("hints", [])
            if len(t["hints"]) != len(eh):
                err(w, f"{len(eh)} hints in English, {len(t['hints'])} here")
            for i, (x, y) in enumerate(zip(eh, t["hints"])):
                if y is None:
                    continue
                if isinstance(x["say"], list) != isinstance(y, list) or (isinstance(y, list) and len(y) != len(x["say"])):
                    err(w, f"hint {i + 1}: the ladder must have the same shape as the English one")
        if "tests" in t and len(t["tests"]) != len(e.get("tests", [])):
            err(w, f"{len(e.get('tests', []))} tests in English, {len(t['tests'])} here")
        if "template" in t and strip_comments(t["template"]) != strip_comments(e.get("template", "")):
            err(w, "template code differs (only comments may change)")
    missing = [q for q in en if q not in zh]
    if missing:
        err(f"{d.name}/exercises.zh.yaml", f"not translated yet: {', '.join(missing)}")


def main() -> None:
    only = set(sys.argv[1:])
    levels = {p.parent.name: p.parent for p in CONTENT.glob("*/*/lesson.en.mdx")}
    for slug, d in sorted(levels.items()):
        if only and slug not in only:
            continue
        has_lesson, has_ex = (d / "lesson.zh.mdx").exists(), (d / "exercises.zh.yaml").exists()
        if has_lesson:
            check_lesson(d)
        if has_ex:
            check_exercises(d)
        if has_lesson != has_ex and (d / "exercises.yaml").exists():
            err(slug, "translate lesson.zh.mdx and exercises.zh.yaml together")
    lz = CONTENT / "levels.zh.yaml"
    if lz.exists():
        for slug, v in (yaml.safe_load(lz.read_text()) or {}).items():
            if slug not in levels:
                err("levels.zh.yaml", f"no level {slug}")
            elif "boss:" not in (levels[slug] / "lesson.en.mdx").read_text().split("---")[1] and "boss" in v:
                err("levels.zh.yaml", f"{slug} is not a boss level")
    gz = CONTENT / "glossary.zh.yaml"
    if gz.exists():
        names = {t["term"] for t in yaml.safe_load((CONTENT / "glossary.yaml").read_text())}
        for k in yaml.safe_load(gz.read_text()) or {}:
            if k not in names:
                err("glossary.zh.yaml", f"no term {k!r} in glossary.yaml")
    for e in errors:
        print(e)
    print(f"{len(errors)} problem(s)" if errors else "OK")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
