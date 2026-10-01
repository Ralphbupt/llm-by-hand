"""Hint reachability for code exercises (used by check_exercises.py).

A hint is dead when no wrong answer can trigger it: a `testFailed: 1` hint behind a test 0 that every mistake already
fails, a shape hint whose regex misses the NumPy 2 matmul message, a hint after an `any: true` hint. The page shows the
first hint (in YAML order) whose `when` matches, so a dead hint is never seen.

How a hint is proven reachable:
- `testFailed: k` and `equals` / `shape`: a wrong fill must stop at the hint and pick it. Wrong fills come from
  small mutations of the solution (a number ±1, a swapped operator or name, a dropped `.T`, slice or line, two lines
  swapped, …) and from the hint's own `wrong:` field (a string or a list: the typical wrong answer it was written
  for). Write `wrong:` when the mutations don't find one; it is stripped before the page gets the hints.
- `error: <regex>`: the regex must match an error that a wrong fill raises, or one of the everyday errors in
  COMMON_ERRORS (a misspelled name, a bad indent, …). A regex for shape errors must also match the NumPy 2 matmul
  message ("matmul: … core dimension …"), which says neither "shape" nor "aligned", unless another error hint does.

grade.ts is mirrored here: the error text is the traceback of the learner's code plus the last line, the failed test
is the first one that is not ok, and the first matching hint wins.
"""
import contextlib
import io
import json
import linecache
import re
import signal
import tokenize
import traceback

import numpy as np


def _numpy_msg(f):
    try:
        f()
    except Exception as e:  # noqa: BLE001
        return f"{type(e).__name__}: {e}"
    return ""


MATMUL_MSG = _numpy_msg(lambda: np.ones((2, 3)) @ np.ones((2, 3)))
SHAPE_MSGS = [
    _numpy_msg(lambda: np.ones((2, 3)) + np.ones((3, 2))),          # broadcast
    _numpy_msg(lambda: np.ones((2, 3)).dot(np.ones((2, 3)))),       # np.dot: not aligned
    MATMUL_MSG,
]
# errors every learner can produce in any exercise
COMMON_ERRORS = [
    "NameError: name 'x' is not defined",
    "IndentationError: unexpected indent",
    "IndentationError: expected an indented block after function definition on line 1",
    "IndentationError: unindent does not match any outer indentation level",
    "SyntaxError: invalid syntax",
    "TypeError: 'NoneType' object is not subscriptable",
    "TypeError: cannot unpack non-iterable NoneType object",
    *SHAPE_MSGS,
]


class _Timeout(Exception):
    pass


def _alarm(*_):
    raise _Timeout()


def _clean(exc: BaseException) -> str:
    """The error text the page shows: frames of the learner's code (with their source lines) and the last line."""
    tb = traceback.TracebackException.from_exception(exc)
    tb.stack = traceback.StackSummary.from_list([f for f in tb.stack if f.filename == "<exec>"])
    return "".join(tb.format()).replace("Traceback (most recent call last):\n", "").replace('File "<exec>"', "your code").strip()


def _close(a, b, tol):
    try:
        return np.allclose(np.array(a, dtype=float), np.array(b, dtype=float), atol=tol, rtol=0) and np.shape(a) == np.shape(b)
    except (TypeError, ValueError):
        return a == b


def run_fill(preamble: str, tpl: str, fill: str, ex: dict, seconds: float = 2.0):
    """Mirror of gradeCode: None when every test passes, else {error, failedIndex, value}."""
    code = tpl.replace("____", fill)
    linecache.cache["<exec>"] = (len(code), None, code.splitlines(True), "<exec>")
    g: dict = {}
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            try:
                exec(preamble, g)
                exec(compile(code, "<exec>", "exec"), g)
            except _Timeout:
                raise
            except BaseException as e:  # noqa: BLE001
                return {"error": _clean(e)}
            for k, t in enumerate(ex.get("tests", [])):
                try:
                    if t.get("setup"):
                        exec(t["setup"], g)
                    v = json.loads(g["__to_json"](eval(t["expr"], g)))
                except _Timeout:
                    raise
                except BaseException as e:  # noqa: BLE001
                    return {"error": _clean(e), "failedIndex": k}
                if "sha256" in t or t.get("sha256Pair"):
                    return None  # a paste check: mutations can't reach a valid hash, and fakes are checked elsewhere
                if not _close(v, t.get("expect"), t.get("tol", 1e-6)):
                    return {"failedIndex": k, "value": v}
    except _Timeout:
        return "timeout"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    return None


def match_one(w: dict, ctx: dict) -> bool:
    """Mirror of matchOne in grade.ts."""
    if w.get("any"):
        return True
    if "equals" in w:
        v = ctx.get("value")
        return isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v - w["equals"]) < 1e-9
    if "shape" in w:
        return isinstance(ctx.get("value"), list) and _close(ctx["value"], w["shape"], 0)
    if "error" in w:
        return bool(ctx.get("error")) and re.search(w["error"], ctx["error"]) is not None
    if "testFailed" in w:
        return ctx.get("failedIndex") == w["testFailed"]
    return False


def pick(hints: list, ctx: dict):
    for i, h in enumerate(hints):
        if match_one(h.get("when") or {}, ctx):
            return i
    return None


# ---- mutations of the solution ---------------------------------------------------------------------------------
OP_SWAP = {"+": ["-"], "-": ["+"], "*": ["/", "+"], "/": ["*"], "//": ["/"], "@": ["*"], "<": ["<="], "<=": ["<"],
           ">": [">="], ">=": [">"], "**": ["*", "^"], "==": ["!="], "!=": ["=="], "+=": ["="], "-=": ["+="], "*=": ["="]}
NAME_SWAP = {"True": ["False"], "False": ["True"], "max": ["min"], "min": ["max"], "argmax": ["argmin"],
             "argmin": ["argmax"], "sum": ["mean"], "mean": ["sum"], "and": ["or"], "or": ["and"], "sqrt": ["abs"],
             "exp": ["log"], "log": ["exp"], "append": ["extend"], "break": ["continue"], "T": [], "zeros": ["ones"],
             "ones": ["zeros"], "inf": ["0"], "maximum": ["max"], "minimum": ["min"],
             "float64": ["int64"], "float32": ["int64"], "float": ["int"]}
KEYWORDS = {"for", "in", "if", "else", "elif", "return", "def", "while", "not", "is", "lambda", "None", "import",
            "from", "as", "with", "yield", "pass", "range", "len", "np", "print"}


def _tokens(src: str):
    try:
        return [t for t in tokenize.generate_tokens(io.StringIO(src).readline)
                if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.ENDMARKER, tokenize.COMMENT)]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return []


def _offsets(src: str):
    starts, n = [0], 0
    for line in src.splitlines(True):
        n += len(line)
        starts.append(n)
    return lambda pos: starts[pos[0] - 1] + pos[1]


def mutants(sol: str, tpl: str):
    """Small wrong versions of `sol`, simplest first, without duplicates."""
    seen, out = {sol}, []

    def add(s):
        if s not in seen:
            seen.add(s)
            out.append(s)

    toks = [t for t in _tokens(sol) if t.type not in (tokenize.INDENT, tokenize.DEDENT)]
    off = _offsets(sol)
    names = [t.string for t in _tokens(sol + "\n" + tpl) if t.type == tokenize.NAME and t.string not in KEYWORDS]
    names = list(dict.fromkeys(names))
    for i, t in enumerate(toks):
        a, b = off(t.start), off(t.end)
        rep = lambda new: add(sol[:a] + new + sol[b:])  # noqa: E731
        if t.type == tokenize.NUMBER:
            try:
                n = float(t.string)
            except ValueError:
                continue
            for v in (0, 1, 2, n + 1, n - 1, -n, n * 2, n / 2):
                v = int(v) if float(v).is_integer() and "." not in t.string else v
                rep(str(v))
        elif t.type == tokenize.OP:
            for new in OP_SWAP.get(t.string, []):
                rep(new)
            if t.string == "-" and (i == 0 or toks[i - 1].string in "([,=:"):
                rep("")  # drop a unary minus
            if t.string == "." and i + 1 < len(toks) and toks[i + 1].string == "T":
                add(sol[:a] + sol[off(toks[i + 1].end):])  # drop .T
            if t.string in "[(":
                # drop a whole bracket group: a slice, an index, or a call's parentheses
                depth = 0
                for j in range(i, len(toks)):
                    depth += toks[j].string in "([{"
                    depth -= toks[j].string in ")]}"
                    if depth == 0:
                        inner = sol[b:off(toks[j].start)]
                        if t.string == "[" and i > 0 and toks[i - 1].type in (tokenize.NAME, tokenize.OP):
                            add(sol[:a] + sol[off(toks[j].end):])
                        if t.string == "(" and i > 0 and toks[i - 1].type == tokenize.NAME:
                            # f(x) -> x : drop the call, keep its argument
                            add(sol[:off(toks[i - 1].start)] + inner + sol[off(toks[j].end):])
                        break
        elif t.type == tokenize.NAME:
            for new in NAME_SWAP.get(t.string, []):
                rep(new)
            if t.string not in KEYWORDS and t.string not in NAME_SWAP:
                for new in names:
                    if new != t.string:
                        rep(new)
    # two different names swap places (operands in the wrong order)
    nm = [t for t in toks if t.type == tokenize.NAME and t.string not in KEYWORDS]
    for i in range(len(nm)):
        for j in range(i + 1, len(nm)):
            if nm[i].string != nm[j].string:
                a1, b1, a2, b2 = off(nm[i].start), off(nm[i].end), off(nm[j].start), off(nm[j].end)
                add(sol[:a1] + nm[j].string + sol[b1:a2] + nm[i].string + sol[b2:])
    # whole lines: drop one, or swap two neighbours (order bugs)
    lines = sol.split("\n")
    for i in range(len(lines)):
        if lines[i].strip():
            add("\n".join(lines[:i] + lines[i + 1:]))
            add("\n".join(lines[:i] + [re.match(r"\s*", lines[i]).group(0) + "pass"] + lines[i + 1:]))
        if i + 1 < len(lines):
            sw = lines[:i] + [lines[i + 1], lines[i]] + lines[i + 2:]
            add("\n".join(sw))
            # the same swap keeping each line's indent (a statement moved past an if)
            ind = lambda s: re.match(r"\s*", s).group(0)  # noqa: E731
            add("\n".join(lines[:i] + [ind(lines[i]) + lines[i + 1].strip(), ind(lines[i + 1]) + lines[i].strip()] + lines[i + 2:]))
    return out


def dead_hints(preamble: str, ex: dict, sol: str, max_mutants: int = 600):
    """[(hint index, why)] for every hint of a code exercise that no wrong answer reaches."""
    hints = ex.get("hints") or []
    tpl = ex.get("template", "")
    out = []
    todo = set()
    for i, h in enumerate(hints):
        w = h.get("when") or {}
        if w.get("any"):
            if i + 1 < len(hints):
                out += [(k, "comes after an `any: true` hint, so it never shows") for k in range(i + 1, len(hints))]
            break
        if any((h2.get("when") or {}) == w for h2 in hints[:i]):
            out.append((i, "the same `when` as an earlier hint"))
            continue
        if "testFailed" in w and not (0 <= w["testFailed"] < len(ex.get("tests", []))):
            out.append((i, f"testFailed: {w['testFailed']} but there are only {len(ex.get('tests', []))} tests"))
            continue
        if "error" in w:
            rx = re.compile(w["error"])
            mm = pick(hints, {"error": MATMUL_MSG})
            if any(rx.search(m) for m in SHAPE_MSGS[:2]) and not rx.search(MATMUL_MSG) and (mm is None or "error" not in hints[mm]["when"]):
                out.append((i, "a shape-error regex that misses the NumPy 2 matmul message: add |matmul|core dimension"))
                continue
            if any(rx.search(m) and pick(hints, {"error": m}) == i for m in COMMON_ERRORS):
                continue
        todo.add(i)
    if not todo:
        return out
    wrong = []
    for i in sorted(todo):
        ws = hints[i].get("wrong")
        wrong += [(i, s) for s in (ws if isinstance(ws, list) else [ws] if ws else [])]
    for i, fill in wrong:
        ctx = run_fill(preamble, tpl, fill, ex)
        if ctx in (None, "timeout"):
            out.append((i, f"its `wrong:` fill {'passes every test' if ctx is None else 'runs too long'}: {fill!r}"))
            todo.discard(i)
            continue
        got = pick(hints, ctx)
        if got == i:
            todo.discard(i)
        else:
            out.append((i, f"its `wrong:` fill picks hint {got} instead: {fill!r}"))
            todo.discard(i)
    for n, fill in enumerate(mutants(sol, tpl)):
        if not todo or n >= max_mutants:
            break
        ctx = run_fill(preamble, tpl, fill, ex, seconds=1.0)
        if ctx in (None, "timeout"):
            continue
        todo.discard(pick(hints, ctx))
    out += [(i, "no wrong answer found that shows it (fix the trigger, or give it a `wrong:` that does)") for i in sorted(todo)]
    return sorted(out)


# ---------------------------------------------------------------------------------------------------------------
# Number questions: an `equals` hint only shows when a learner types exactly that value, so the value must be the
# one the mistake it describes really produces (round 9: kv-context said 32768 for a mistake that gives 16384).
# Give the hint a `wrong:` (an arithmetic expression, or a list of them: the mistake written out) and it is
# recomputed here. Without `wrong:`, the value must at least appear in the hint, or be what one of the hint's
# own sums gives; otherwise it is listed as unverified.

_SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")


def _arith(s: str) -> str:
    s = str(s).replace("×", "*").replace("·", "*").replace("÷", "/").replace("−", "-").replace("–", "-")
    s = s.replace("√", "sqrt").replace("^", "**").replace("ln", "log").replace("`", "")
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)                                 # 16,384 → 16384
    s = re.sub(r"([\d)])([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)", lambda m: f"{m[1]}**({m[2].translate(_SUP)})", s)  # 10⁹ → 10**(9)
    return s


def _eval(expr: str):
    import math
    env = {k: getattr(math, k) for k in ("sqrt", "log", "log2", "log10", "exp", "e", "pi", "tanh", "cos", "sin")}
    env.update(np=np)
    try:
        v = eval(_arith(expr), {"__builtins__": {}, "min": min, "max": max, "abs": abs, "round": round}, env)
        return float(v) if isinstance(v, (int, float, np.number)) and not isinstance(v, bool) else None
    except Exception:  # noqa: BLE001
        return None


def _same(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= max(tol, 1e-9, 1e-3 * abs(b))


def _numbers_in(text: str):
    t = _arith(text)
    vals = [float(x) for x in re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?(?:e-?\d+)?", t)]
    # sums written in the hint: "8 * 1024 / 512", "(2 - 0.5) * 3", "10**(9) / 512"
    for m in re.finditer(r"[-(]*\d[\d.]*(?:\*\*\(-?\d+\))?\)*(?:\s*(?:\*\*|[-+*/])\s*[(]*-?\d[\d.]*(?:\*\*\(-?\d+\))?\)*)+", t):
        v = _eval(m[0])
        if v is not None:
            vals.append(v)
    return vals


def number_hint_problems(ex: dict):
    """(errors, unverified): [(hint index, why)] for the `equals` hints of one number question."""
    errors, unverified = [], []
    ans, tol = ex.get("answer"), float(ex.get("tol", 0) or 0)
    for i, h in enumerate(ex.get("hints") or []):
        w = h.get("when") or {}
        if "equals" not in w:
            continue
        val = float(w["equals"])
        if isinstance(ans, (int, float)) and abs(val - ans) <= tol:
            errors.append((i, f"equals {w['equals']} is accepted as right (answer {ans} ± {tol}), so the hint never shows"))
            continue
        ws = h.get("wrong")
        ws = ws if isinstance(ws, list) else [ws] if ws is not None else []
        if ws:
            for s in ws:
                got = _eval(s)
                if got is None:
                    errors.append((i, f"its `wrong:` {s!r} does not evaluate"))
                elif abs(got - val) > 1e-9 + 1e-6 * abs(val):
                    errors.append((i, f"its `wrong:` {s!r} gives {got:g}, but the hint is on equals {w['equals']}"))
            continue
        says = h.get("say")
        text = " ".join(str(s) for s in (says if isinstance(says, list) else [says]))
        if not any(_same(v, val, 0) for v in _numbers_in(text)):
            unverified.append((i, f"equals {w['equals']}: {text[:110]}"))
    return errors, unverified


if __name__ == "__main__":
    import argparse
    import pathlib

    import yaml

    ap = argparse.ArgumentParser(description="Check that every number question's `equals` hint is on the value its mistake gives.")
    ap.add_argument("--unverified", action="store_true", help="also list hints whose value is neither recomputed nor in the hint")
    a = ap.parse_args()
    root = pathlib.Path(__file__).resolve().parent.parent
    n_err = n_unv = 0
    for y in sorted(root.glob("content/*/*/exercises.yaml")):
        for eid, ex in (yaml.safe_load(y.read_text()) or {}).items():
            if not isinstance(ex, dict) or ex.get("type") != "number":
                continue
            errs, unv = number_hint_problems(ex)
            for i, why in errs:
                print(f"{y.parent.name}/{eid}: hint {i}: {why}")
            n_err += len(errs)
            n_unv += len(unv)
            if a.unverified:
                for i, why in unv:
                    print(f"  unverified {y.parent.name}/{eid}: hint {i}: {why}")
    print(f"number hints: {n_err} wrong, {n_unv} unverified (give them a `wrong:` sum; --unverified lists them)")
    raise SystemExit(1 if n_err else 0)
