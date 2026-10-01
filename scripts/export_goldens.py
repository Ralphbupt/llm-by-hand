"""
Export numpy results as golden data for the site's unit tests (site/src/lib/num.test.ts).

The labs compute in JavaScript (site/src/lib/num.ts) while code exercises run real numpy in the browser.
Both must agree exactly, or a lab and the exercise below it would disagree.

Run:  .venv/bin/python scripts/export_goldens.py
"""

import json
import pathlib

import numpy as np

OUT = pathlib.Path(__file__).resolve().parent.parent / "site/public/data/goldens/core.json"


def softmax(x, axis=-1):
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)


def layernorm(x, eps=1e-5):
    mu = x.mean(axis=-1, keepdims=True)
    sd = np.sqrt(x.var(axis=-1, keepdims=True) + eps)
    return (x - mu) / sd


def main():
    rng = np.random.default_rng(0)
    cases = {}

    # attention example: 3 words, 2 dimensions
    X = np.array([[1, 0], [0, 1], [1, 1.0]])
    scores = X @ X.T / np.sqrt(2)
    w = softmax(scores)
    cases["attention_3x2"] = {
        "X": X.tolist(), "d_k": 2,
        "scores": scores.tolist(), "weights": w.tolist(), "out": (w @ X).tolist(),
    }

    # causal mask + masked softmax
    L = 4
    m = np.triu(np.ones((L, L), dtype=bool), 1)
    s = rng.standard_normal((L, L))
    masked = np.where(m, -np.inf, s)
    cases["masked_softmax_4"] = {
        "scores": s.tolist(), "mask": m.tolist(), "weights": softmax(masked).tolist(),
    }

    # plain matmul, transpose, LayerNorm, ReLU
    a, b = rng.standard_normal((3, 4)), rng.standard_normal((4, 2))
    cases["matmul_3x4_4x2"] = {"a": a.tolist(), "b": b.tolist(), "out": (a @ b).tolist()}
    v = rng.standard_normal((2, 5)) * 3 + 1
    cases["layernorm_2x5"] = {"x": v.tolist(), "out": layernorm(v).tolist()}
    cases["relu_2x3"] = {"x": (u := rng.standard_normal((2, 3))).tolist(), "out": np.maximum(u, 0).tolist()}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(cases, indent=1))
    print(f"wrote {OUT} ({len(cases)} cases, {OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
