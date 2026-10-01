"""Write the generated stories for the level 11 labs: site/public/data/language-models/corpus.json"""
import json
import pathlib

from demo import VOCAB, make_corpus

out = pathlib.Path(__file__).resolve().parents[3] / "site/public/data/language-models/corpus.json"
out.parent.mkdir(parents=True, exist_ok=True)
s = make_corpus()
out.write_text(json.dumps({"vocab": VOCAB, "train": s[:160], "heldout": s[160:]}))
print("wrote", out, out.stat().st_size, "bytes")
