"""Copy the files learners download for local work into site/public/files/<level>/ (served at /files/<level>/).

The originals live next to each level's lesson in content/. Run this after editing any of them;
scripts/check_exercises.py fails while a served copy is out of date.

A block between the lines `# >>> course-only` and `# <<< course-only` (the example paste that the course's own
checks use) is left out of the served copy, so a downloaded script never contains a passing line.
Anything else under site/public/files/ (a __pycache__, a file no longer listed) is removed.

Usage:  python scripts/sync_files.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent

# level folder name -> files in that folder that a learner downloads.
# No demo.py that solves a boss (lstm, seq2seq-attention, latents-and-dit, write-a-gpt) is served.
DOWNLOADS = {
    "numpy-to-pytorch": ["first_run.py"],
    "convolutions": ["demo.py"],
    "residuals-and-norms": ["demo.py"],
    "rnn": ["demo.py"],
    "debugging": ["broken_train.py", "check.py"],
    "lstm": ["boss.py"],
    "seq2seq-attention": ["boss.py"],
    "autoencoders": ["demo.py"],
    "encoder-decoder": ["demo.py"],
    "attention-backward": ["demo.py"],
    "latents-and-dit": ["boss.py"],
    "write-a-gpt": ["skeleton.py", "skeleton_hints.py", "check.py", "check_weights.json"],
}

COURSE_ONLY = re.compile(rb"\n# >>> course-only[^\n]*\n.*?# <<< course-only\n", re.S)


def served_bytes(path):
    """The bytes a learner downloads: the file without its course-only blocks."""
    return COURSE_ONLY.sub(b"\n", path.read_bytes())


if __name__ == "__main__":
    for name, files in DOWNLOADS.items():
        src = next(ROOT.glob(f"content/*/{name}"))
        out = ROOT / "site/public/files" / name
        out.mkdir(parents=True, exist_ok=True)
        for f in files:
            (out / f).write_bytes(served_bytes(src / f))
            print(f"/files/{name}/{f}")
    # nothing else is published: no __pycache__ (left by running a script there), no file that left DOWNLOADS
    import shutil
    for d in (ROOT / "site/public/files").iterdir():
        for p in d.iterdir():
            if p.name not in DOWNLOADS.get(d.name, []):
                shutil.rmtree(p) if p.is_dir() else p.unlink()
                print("removed", p.relative_to(ROOT))
