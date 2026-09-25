"""Smoke tests for the figures toolkit (run: python3 -m pytest figures/tests -q)."""
import importlib.util
import pathlib
import subprocess
import sys

import pytest

FIG = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_palette_selfcheck():
    subprocess.run([PY, str(FIG / "style" / "palette.py")], check=True)


def test_harvester_selftest():
    pytest.importorskip("fitz")
    subprocess.run([PY, str(FIG / "harvester" / "harvest.py"), "--selftest"], check=True)


def test_gallery_selftest():
    subprocess.run([PY, str(FIG / "harvester" / "gallery.py"), "--selftest"], check=True)


@pytest.mark.parametrize("script", sorted((FIG / "templates").glob("p[0-9][0-9]_*.py")), ids=lambda p: p.stem)
def test_template_renders(script, tmp_path):
    import matplotlib
    matplotlib.use("Agg")
    mod = _load(script)
    paths = mod.make(venue="lncs", outdir=tmp_path)
    assert paths and all(pathlib.Path(p).stat().st_size > 0 for p in paths)


def test_no_private_strings():
    # assembled at runtime so that this file itself passes the repo-wide grep
    bad = ["order" + "-4", "order" + "4", "symmetry" + "-graded", "#" + "528", "#" + "699", "192" + ".168.",
           "/ho" + "me/", "ac" + "pk", "soseri" + "halsona"]
    for f in FIG.rglob("*"):
        if f.is_file() and f.suffix in {".py", ".md", ".tex", ".sty", ".mplstyle"} and f.name != "test_figures.py":
            txt = f.read_text(errors="ignore").lower()
            for b in bad:
                assert b.lower() not in txt, (f, b)
