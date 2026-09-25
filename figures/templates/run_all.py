#!/usr/bin/env python3
"""Render every template (p*.py) into figures/examples/ and check the outputs.

    python3 figures/templates/run_all.py [--venue lncs|acm|ieee] [--out DIR]
"""
import argparse, importlib.util, pathlib, sys, time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", default="lncs")
    ap.add_argument("--out", default=str(HERE.parent / "examples"))
    a = ap.parse_args()
    fails = []
    for f in sorted(HERE.glob("p[0-9][0-9]_*.py")):
        spec = importlib.util.spec_from_file_location(f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        t0 = time.time()
        try:
            spec.loader.exec_module(mod)
            paths = mod.make(venue=a.venue, outdir=a.out)
            assert all(pathlib.Path(p).stat().st_size > 0 for p in paths)
            print(f"ok   {f.name:32s} {time.time() - t0:5.2f}s  -> {', '.join(pathlib.Path(p).name for p in paths)}")
        except Exception as e:  # report and continue
            fails.append(f.name)
            print(f"FAIL {f.name}: {e!r}")
        plt.close("all")
    if fails:
        sys.exit(f"{len(fails)} template(s) failed: {fails}")


if __name__ == "__main__":
    main()
