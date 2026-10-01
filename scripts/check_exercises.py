"""Check every content/**/exercises.yaml.

- number / shape / predict: required fields are present.
- code: the template contains ____, and `solution` (the line that replaces ____) passes every test,
  run the same way the browser runs it (same preamble: numpy as np, softmax).
- hints are reachable (scripts/hint_reach.py): some wrong answer shows each hint.
- hints don't leak: no hint ladder (one `when` branch, its rungs added up) contains 80% or more of a code
  solution's tokens. The full answer is what "Show answer" is for.
- a boss level's testOut includes its checkpoint; the files learners download from /files/<level>/ match content/
  (minus course-only blocks), and no downloaded file holds a valid PASS line or example_paste.
- a boss's answer is `reference:` (checked here, never sent to the page, so no "Show answer"); the checkpoint of a boss
  level has no `solution`, every in-browser boss part in testOut is on the way to the checkpoint (a <Gate> encloses it),
  and no template on the level shows a boss's reference lines. Every other in-browser boss part (id boss-*, a prompt
  that starts "The boss", or a `reference`) has no `solution` and is listed in the level's `mustSolve` (and testOut).
- every id used in lesson.en.mdx (<Blank id=...>, <Gate requires=...>, checkpoint) exists in the yaml.
- level references are current: a "[level K](/learn/slug/)" link names slug's real level, and no sentence sends the
  reader to main levels 16-21 for an encoder, cross-attention, a source sentence or label smoothing (that is N7).
  Put `ref-ok` on the line to accept one.

Usage:  python scripts/check_exercises.py [--only 07-attention]
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import re
import sys

import numpy as np
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
PREAMBLE = (ROOT / "site/src/lib/pyodide/worker.ts").read_text().split("const PREAMBLE = `")[1].split("`")[0]

sys.path.insert(0, str(ROOT / "scripts"))
from sync_files import DOWNLOADS, served_bytes  # noqa: E402
from hint_reach import dead_hints  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--only")
args = ap.parse_args()


def close(a, b, tol):
    try:
        return np.allclose(np.array(a, dtype=float), np.array(b, dtype=float), atol=tol, rtol=0) and np.shape(a) == np.shape(b)
    except (TypeError, ValueError):
        return a == b


def toks(s):
    s = re.sub(r"#.*", "", str(s)).replace("−", "-").replace("’", "'").replace("`", "").replace("√", "sqrt").replace("×", "*")
    return re.findall(r"[A-Za-z_][A-Za-z_0-9.]*|\d+(?:\.\d+)?|[-+*/@<>=!]+|\[|\]", s)


def hint_leaks(ex, limit=0.8):
    """(branch, rung, share) of the first hint rung whose ladder so far holds >= limit of the solution's tokens."""
    sol = [t for t in toks(ex.get("solution", ex.get("reference", ""))) if t != "print"]
    if len(sol) < 3:
        return None
    for h in ex.get("hints") or []:
        says = h.get("say")
        says = says if isinstance(says, list) else [says]
        seen = []
        for i, say in enumerate(says):
            seen += toks(say)
            share = sum(1 for t in sol if t in seen) / len(sol)
            if share >= limit:
                return next(iter(h["when"])), i + 1, round(share, 2)
    return None


_SHA256 = hashlib.sha256  # kept before any template runs: a fake paste may replace hashlib.sha256


def hash_ok(test, v):
    """Mirrors hashOk in site/src/lib/grade.ts."""
    sha = lambda t: _SHA256(t.encode()).hexdigest()
    if "sha256" in test:
        return isinstance(v, str) and len(test["sha256"]) >= 8 and sha(v).startswith(test["sha256"])
    if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, str) for x in v)):
        return False
    return bool(re.fullmatch(r"[0-9a-f]{8,}", v[1])) and sha(v[0]).startswith(v[1])


def run_tests(tpl, fill, ex):
    """Run the template with ____ = fill and every test, the way the browser does. Returns the failures."""
    g, out = {}, []
    try:
        # templates and tests may print; keep the report clean
        with contextlib.redirect_stdout(io.StringIO()):
            exec(PREAMBLE, g)
            exec(tpl.replace("____", fill), g)
            for k, test in enumerate(ex.get("tests", [])):
                if test.get("setup"):
                    exec(test["setup"], g)
                got = json.loads(g["__to_json"](eval(test["expr"], g)))
                if "sha256" in test or test.get("sha256Pair"):
                    # hashed here with this script's own hashlib, like the page does in JS: the template can't patch it
                    if not hash_ok(test, got):
                        out.append(f"test {k + 1}: the hash does not match")
                elif not close(got, test["expect"], test.get("tol", 1e-6)):
                    out.append(f"test {k + 1} expected {test['expect']}, got {got}")
    except Exception as e:  # noqa: BLE001
        out.append(f"solution raised {type(e).__name__}: {e}")
    finally:
        hashlib.sha256 = _SHA256
    return out


def unwrap_casts(code):
    """Drop int(...) around np.arg* and float(...) around np.*: the natural answer without the cast.
    Returns None when there is nothing to drop. The page must grade both the same (numpy scalars in a list)."""
    out, i, hit = [], 0, False
    for m in re.finditer(r"\b(int\((?=np\.arg)|float\((?=np\.))", code):
        if m.start() < i:
            continue
        depth, j = 1, m.end()
        while j < len(code) and depth:
            depth += {"(": 1, ")": -1}.get(code[j], 0)
            j += 1
        if depth:
            continue
        out += [code[i:m.start()], code[m.end():j - 1]]
        i, hit = j, True
    return "".join(out) + code[i:] if hit else None


def json_regression():
    """numpy scalars inside lists, tuples and dicts must serialize (round 9 P0: greedy-loop with np.int64 ids)."""
    g = {}
    exec(PREAMBLE, g)
    got = json.loads(g["__to_json"]([np.int64(2), (np.float32(0.5), np.bool_(True)), {"k": np.int64(3)}, np.array([1, 2])]))
    want = [2, [0.5, True], {"k": 3}, [1, 2]]
    return [] if got == want else [f"worker.ts __to_json: nested numpy scalars give {got}, want {want}"]


def load_local(folder, filename):
    """Import a level's local script (boss.py, check.py) without running its main part."""
    sys.path.insert(0, str(folder))
    try:
        spec = importlib.util.spec_from_file_location(f"local_{folder.name}_{filename[:-3]}", folder / filename)
        mod = importlib.util.module_from_spec(spec)
        with contextlib.redirect_stdout(io.StringIO()):
            spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(folder))


def option_order(eid, n):
    """Mirror of optionOrder in site/src/lib/shuffle.ts: order[k] = yaml index of the option shown in place k."""
    M = 0xFFFFFFFF
    h = 2166136261
    for c in eid.split("/")[-1].encode("utf-16-le")[::2]:  # ids are ASCII: one code unit per character
        h = ((h ^ c) * 16777619) & M
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & M
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & M
    h ^= h >> 16
    order = list(range(n))
    for i in range(n - 1, 0, -1):
        h = (h * 1664525 + 1013904223) & M
        j = (h >> 16) % (i + 1)
        order[i], order[j] = order[j], order[i]
    return order


def _flat(s):
    """Recap or answer text without markup, spaces or unicode minus, for substring matching."""
    s = str(s).replace("−", "-").replace("’", "'").replace("·", "*").replace("×", "*")
    s = re.sub(r"\\(?:mathrm|text|operatorname)\{([^}]*)\}", r"\1", s)
    return re.sub(r"[\s`$\\{}]", "", s)


# (level, exercise, words in the recap line): checked by hand, not a leak
RECAP_OK = [
    ("activations", "sig-d0", "at most 0.25"),  # the prompt hands over the formula and σ(0); the bound is the level's main fact
    ("neurons-and-loss", "z-11", "p = 0.5"),  # a probability, not the z the question asks for
    ("language-models", "p-sat-cat", "0.5 × 0.5"),  # a perplexity example, not P(sat | cat)
    ("latents-and-dit", "tokens-28", "16× the scores"),  # a ratio of scores, not a token count
]


def recap_leaks(front, exs, level=""):
    """A recap must not hold the answer of the checkpoint or of a testOut question (T P1-1).

    Code: any solution/reference line of 8+ characters. Shape: the tuple, as (a,b) or a×b. Number: the value as its own
    token, when it has 2+ characters (a lone 1 or 6 shows up everywhere). Accept a line checked by hand in RECAP_OK."""
    recap = front.get("recap") or {}
    lines = [ln for part in ("can", "keys", "mistakes") for ln in (recap.get(part) or [])]
    out = []
    for eid in dict.fromkeys([front.get("checkpoint"), *(front.get("testOut") or [])]):
        ok = [w for lv, e, w in RECAP_OK if lv == level and e == eid]
        flat = [(ln, _flat(ln)) for ln in lines if not any(w in ln for w in ok)]
        ex = exs.get(eid) or {}
        t, needles = ex.get("type"), []
        if t == "code":
            sol = ex.get("solution", ex.get("reference")) or ""
            needles = [_flat(ln) for ln in str(sol).splitlines() if len(_flat(ln)) >= 8]
        elif t == "shape" and isinstance(ex.get("answer"), list) and len(ex["answer"]) > 1:
            dims = [str(d) for d in ex["answer"]]
            needles = ["(" + ",".join(dims) + ")", "*".join(dims)]
        elif t == "number" and "answer" in ex:
            v = ex["answer"]
            v = int(v) if isinstance(v, float) and v.is_integer() else v
            if len(str(v)) >= 2:
                for ln, f in flat:
                    if re.search(rf"(?<![\w.]){re.escape(str(v))}(?![\w.]|\.\d)", ln.replace("−", "-")):
                        out.append(f"recap gives away the answer of '{eid}' ({v}): {ln[:70]}")
            continue
        for nd in needles:
            for ln, f in flat:
                if nd and nd in f:
                    out.append(f"recap gives away the answer of '{eid}': {ln[:70]}")
                    break
    return out


problems = json_regression()
warnings = []
for y in sorted(ROOT.glob("content/*/*/exercises.yaml")):
    name = y.parent.name
    if args.only and args.only not in name:
        continue
    exs = yaml.safe_load(y.read_text()) or {}
    for eid, ex in exs.items():
        where = f"{name}/{eid}"
        t = ex.get("type")
        if not ex.get("prompt"):
            problems.append(f"{where}: no prompt")
        if t == "number" and "answer" not in ex:
            problems.append(f"{where}: number without answer")
        elif t == "shape" and not isinstance(ex.get("answer"), list):
            problems.append(f"{where}: shape answer must be a list")
        elif t == "predict" and not (ex.get("options") and ex.get("reveal")):
            problems.append(f"{where}: predict needs options and reveal")
        elif t == "predict" and "answer" in ex and not (isinstance(ex["answer"], int) and 0 <= ex["answer"] < len(ex["options"])):
            problems.append(f"{where}: predict answer must be an option index")
        elif t == "code":
            tpl, sol = ex.get("template", ""), ex.get("solution", ex.get("reference"))
            if "solution" in ex and "reference" in ex:
                problems.append(f"{where}: use `solution` (shown on request) or `reference` (hidden), not both")
            if "____" not in tpl:
                problems.append(f"{where}: template has no ____")
            if sol is None and not ex.get("paste"):
                problems.append(f"{where}: code exercise needs a `solution` or `reference` (or `paste:` for a line pasted from a local script)")
                continue
            if sol is None:
                # a boss paste: no solution on the page (no "Show answer"). The local script makes a passing paste,
                # which must pass; every `mustFail` paste (an easy fake) must fail.
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        sol = load_local(y.parent, ex["paste"]).example_paste(eid)
                except Exception as e:  # noqa: BLE001
                    problems.append(f"{where}: {ex['paste']} example_paste('{eid}') raised {type(e).__name__}: {e}")
                    continue
                for fake in ex.get("mustFail", []):
                    if not run_tests(tpl, fake, ex):
                        problems.append(f"{where}: the fake paste {fake!r} passes every test")
            problems += [f"{where}: {m}" for m in run_tests(tpl, sol, ex)]
            if (bare := unwrap_casts(sol)) and not run_tests(tpl, sol, ex):
                problems += [f"{where}: without int()/float() the solution fails: {m}" for m in run_tests(tpl, bare, ex)]
        if t == "code" and not ex.get("paste") and sol is not None:
            for i, why in dead_hints(PREAMBLE, ex, sol):
                problems.append(f"{where}: hint {i} ({json.dumps((ex['hints'][i] or {}).get('when'))}) is dead: {why}")
        if t == "code" and (leak := hint_leaks(ex)):
            problems.append(f"{where}: hint `{leak[0]}` rung {leak[1]} gives away {leak[2]:.0%} of the solution")
        elif t not in ("number", "shape", "predict", "code"):
            problems.append(f"{where}: unknown type {t}")
        if "optional" in ex and not isinstance(ex["optional"], bool):
            problems.append(f"{where}: optional must be true or false")

    mdx = (y.parent / "lesson.en.mdx").read_text()
    used = set(re.findall(r'<(?:Blank|CodeBlank|Predict)\s+id="([^"]+)"', mdx))
    used |= set(re.findall(r'<Gate\s+requires="([^"]+)"', mdx))
    used |= set(re.findall(r"^checkpoint:\s*(\S+)", mdx, re.M))
    for u in sorted(used - set(exs)):
        problems.append(f"{name}: lesson uses id '{u}' that is not in exercises.yaml")
    for u in sorted(set(exs) - used):
        problems.append(f"{name}: exercise '{u}' is never shown on the page")
    front = yaml.safe_load(mdx.split("---", 2)[1]) if mdx.startswith("---") else {}
    if front.get("boss") and front.get("testOut") and front.get("checkpoint") not in front["testOut"]:
        problems.append(f"{name}: a boss level's testOut must include its checkpoint '{front.get('checkpoint')}'")
    for f in DOWNLOADS.get(name, []):
        served = ROOT / "site/public/files" / name / f
        if not served.exists() or served.read_bytes() != served_bytes(y.parent / f):
            problems.append(f"{name}: /files/{name}/{f} is missing or out of date: run scripts/sync_files.py")
            continue
        text = served.read_text(errors="replace")
        if "example_paste" in text:
            problems.append(f"{name}: /files/{name}/{f} contains example_paste: put it in a course-only block")
        for lv, word, val, code in re.findall(r"\b([A-Z]?\d+) ([A-Z]+) ([\d.]+) ([0-9a-f]{8})\b", text):
            if hashlib.sha256(f"llm-by-hand/{lv}/{val}".encode()).hexdigest()[:8] == code:
                problems.append(f"{name}: /files/{name}/{f} contains a valid line '{lv} {word} {val} {code}'")

    problems += [f"{name}: {m}" for m in recap_leaks(front, exs, name)]

    # `optional: true` never costs a star, so the level must not need it
    for e in [front.get("checkpoint"), *(front.get("mustSolve") or [])]:
        if exs.get(e, {}).get("optional"):
            problems.append(f"{name}/{e}: the checkpoint or a mustSolve part can't be optional")
    # graded Predicts are shown shuffled (site/src/lib/shuffle.ts); warn when one level's answers all land in one place
    spots = [option_order(e, len(x["options"])).index(x["answer"]) for e, x in exs.items()
             if x.get("type") == "predict" and isinstance(x.get("answer"), int) and x.get("options")]
    if len(spots) >= 3 and len(set(spots)) == 1:
        warnings.append(f"{name}: all {len(spots)} graded Predicts show their answer in place {spots[0] + 1}: reorder some options")

    # boss rules
    if front.get("boss"):
        cp = front.get("checkpoint")
        if exs.get(cp, {}).get("solution") is not None:
            problems.append(f"{name}: the boss checkpoint '{cp}' has a `solution` (Show answer would clear the level): use `reference`")
        # an in-browser boss part (id boss-*, a prompt that starts "The boss", or a `reference`) never shows an answer,
        # and the level only clears once it is solved (mustSolve), so "Skip for now" can't get past it
        must = front.get("mustSolve") or []
        for e, ex in exs.items():
            if ex.get("type") != "code" or "paste" in ex or e == cp:
                continue
            is_boss = e.startswith("boss-") or str(ex.get("prompt", "")).lstrip().startswith("The boss") or "reference" in ex
            if not is_boss:
                continue
            if ex.get("solution") is not None:
                problems.append(f"{name}/{e}: a boss part has a `solution` (Show answer gives the boss away): use `reference`")
            if e not in must:
                problems.append(f"{name}: boss part '{e}' is not in mustSolve, so a skipped Gate lets the level clear without it")
        for e in must:
            if e not in exs:
                problems.append(f"{name}: mustSolve id '{e}' is not in exercises.yaml")
            elif exs[e].get("solution") is not None:
                problems.append(f"{name}/{e}: a mustSolve boss part has a `solution`: use `reference`")
            if front.get("testOut") and e not in front["testOut"]:
                problems.append(f"{name}: mustSolve id '{e}' must be in testOut too")
        enclosing, stack, order = {}, [], []
        for m in re.finditer(r'<Gate\s+requires="([^"]+)"|</Gate>|<(?:Blank|CodeBlank|Predict)\s+id="([^"]+)"', mdx):
            if m.group(0) == "</Gate>":
                stack and stack.pop()
            elif m.group(1):
                stack.append(m.group(1))
            else:
                enclosing[m.group(2)] = list(stack)
                order.append(m.group(2))
        on_path, todo = set(), [cp]
        while todo:
            for r in enclosing.get(todo.pop(), []):
                if r not in on_path:
                    on_path.add(r)
                    todo.append(r)
        for e in front.get("testOut") or []:
            if e == cp or exs.get(e, {}).get("type") != "code" or e not in order or cp not in order:
                continue
            if order.index(e) < order.index(cp) and e not in on_path:
                problems.append(f"{name}: boss part '{e}' is in testOut but the checkpoint '{cp}' can be reached without it: wrap the rest in <Gate requires=\"{e}\">")
    for eid, ex in exs.items():
        ref = ex.get("reference")
        if not ref:
            continue
        lines = {re.sub(r"\s+", " ", ln).strip() for ln in ref.splitlines()}
        lines = {ln for ln in lines if len(ln) > 12}
        for other, ox in exs.items():
            tpl = re.sub(r"[ \t]+", " ", ox.get("template", ""))
            shown = [ln for ln in lines if ln in tpl]
            if other != eid and shown:
                problems.append(f"{name}/{other}: the template shows lines of the boss answer '{eid}': {shown[:2]}")


# MDX treats a bare `{` in prose as a JavaScript expression: `h_{t-1}` outside math or code can blank a whole page
# without an error. Flag `{` in prose lines (outside code fences, $$ blocks, inline `code`, $math$ and JSX tags).
for mdx in sorted(ROOT.glob("content/*/*/lesson.en.mdx")):
    if args.only and args.only not in mdx.parent.name:
        continue
    text = mdx.read_text()
    body = text.split("---", 2)[2] if text.startswith("---") else text
    fence = math = False
    tag_depth = 0
    for n, line in enumerate(body.splitlines(), start=text[: text.find(body)].count("\n") + 1):
        st = line.strip()
        if st.startswith("```"):
            fence = not fence
            continue
        if st == "$$":
            math = not math
            continue
        if fence or math or st.startswith("import ") or st.startswith("export "):
            continue
        if st.startswith("<") or tag_depth:
            # JSX lines: props may use {…}; track multi-line tags roughly
            tag_depth = 0 if st.endswith(">") else 1
            continue
        prose = re.sub(r"`[^`]*`", "", line)
        prose = re.sub(r"\$\$.*?\$\$", "", prose)
        prose = re.sub(r"\$[^$]*\$", "", prose)
        prose = re.sub(r"\{/\*.*?\*/\}", "", prose)  # MDX comments
        if "{" in prose or "}" in prose:
            problems.append(f"{mdx.parent.name}/lesson.en.mdx:{n}: bare brace in prose (wrap it in `code` or $math$): {st[:80]}")

# Level references must match the course as it is now (levels get renumbered and moved):
# - a link "[level K](/learn/<slug>/)" must name the level that <slug> really is;
# - the 2017 encoder-decoder topics live in side trip N7, so a sentence that sends the reader to a main level 16-21 for
#   an encoder, cross-attention, a source sentence or label smoothing is stale.
LEVEL_OF = {}
for mdx in ROOT.glob("content/*/*/lesson.en.mdx"):
    m = re.search(r'^level:\s*"?([^"\n]+)"?', mdx.read_text(), re.M)
    if m:
        LEVEL_OF[mdx.parent.name] = m.group(1).strip()
N7_TOPIC = re.compile(r"\bencoder\b|cross-attention|source sentence|two sequences|label[_ ]smoothing", re.I)
MAIN_LATE = re.compile(r"\blevels? (?:1[6-9]|2[01])\b(?:\s*(?:–|-|to|and)\s*\d+)?", re.I)
ref_files = sorted(ROOT.glob("content/*/*/lesson.en.mdx")) + sorted(ROOT.glob("content/*/*/exercises.yaml")) + [ROOT / "content/glossary.yaml"]
for f in ref_files:
    if args.only and args.only not in f.parent.name:
        continue
    rel = f.relative_to(ROOT / "content")
    for n, line in enumerate(f.read_text().splitlines(), 1):
        if "ref-ok" in line:
            continue
        for text, slug in re.findall(r"\[((?:[Ll]evels?|[Bb]ranch level|[Ss]ide trip)[^\]]*)\]\(/learn/([\w-]+)/", line):
            want = LEVEL_OF.get(slug)
            got = re.search(r"\b([A-Z]?\d+)\b", text)
            if want and got and got.group(1) != want:
                problems.append(f"{rel}:{n}: link text '{text}' points to /learn/{slug}/, which is level {want}")
        for sent in re.split(r"(?<=[.!?])\s+", line):
            if (MAIN_LATE.search(sent) and N7_TOPIC.search(sent) and "N7" not in sent and "encoder-decoder" not in str(rel)
                    and not re.search(r"\bno (?:separate )?encoder|without (?:an )?encoder", sent, re.I)):
                problems.append(f"{rel}:{n}: a main level and an encoder-decoder topic in one sentence (that is side trip N7 now): {sent.strip()[:90]}")

for p in sorted((ROOT / "site/public/files").glob("*/*")):
    if p.name not in DOWNLOADS.get(p.parent.name, []):
        problems.append(f"/files/{p.parent.name}/{p.name} is published but not in DOWNLOADS: run scripts/sync_files.py")

for w in warnings:
    print(f"warning: {w}")
print("\n".join(problems) if problems else "all exercises ok")
sys.exit(1 if problems else 0)
