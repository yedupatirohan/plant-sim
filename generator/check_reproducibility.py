"""Build twice with the same seed and compare row counts and checksums."""
import sys
import tempfile
from pathlib import Path

from generator.build_dataset import build


def main() -> int:
    seed = 20261022
    with tempfile.TemporaryDirectory() as d:
        a = build(seed, Path(d) / "run1")
        b = build(seed, Path(d) / "run2")
    ok = True
    for name in a["files"]:
        same = a["files"][name] == b["files"][name]
        ok &= same
        print(f"{name:28s} rows={a['files'][name]['rows']:>7}  "
              f"{'MATCH' if same else 'DIFFERENT'}  {a['files'][name]['sha256'][:16]}")
    print("REPRODUCIBLE" if ok else "NOT REPRODUCIBLE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())