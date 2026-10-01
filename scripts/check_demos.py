"""Run every content/**/demo.py and report which ones fail.

Usage:  python scripts/check_demos.py [--only 07-attention]
Use a Python that has numpy (and torch, for the levels that train locally).
"""
import argparse
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser()
ap.add_argument("--only", help="run only demos whose folder name contains this")
ap.add_argument("--timeout", type=int, default=600)
args = ap.parse_args()

demos = sorted(ROOT.glob("content/*/*/demo.py"))
if args.only:
    demos = [d for d in demos if args.only in d.parent.name]

failed = []
for d in demos:
    t = time.time()
    r = subprocess.run([sys.executable, d.name], cwd=d.parent, capture_output=True, text=True, timeout=args.timeout)
    ok = r.returncode == 0
    print(f"{'ok ' if ok else 'FAIL'} {d.parent.name:32s} {time.time() - t:6.1f}s")
    if not ok:
        failed.append(d)
        print(r.stderr[-2000:])

print(f"\n{len(demos) - len(failed)} / {len(demos)} demos ran")
sys.exit(1 if failed else 0)
