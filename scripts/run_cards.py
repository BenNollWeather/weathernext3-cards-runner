#!/usr/bin/env python3
"""Render WeatherNext 3 storm impact cards straight from the notebook.

The notebook stays the single source of truth: this script runs only the cells
the cards need (settings/setup, shared map style, storm impact cards) with a
few settings forced for unattended runs, then writes a manifest of the cards
it produced for bin/run to upload.

    python scripts/run_cards.py --notebook path/to/weathernext3_cyclones.ipynb \
        --work-dir /tmp/weathernext3_cards --modes light --layouts 3x2
    python scripts/run_cards.py --check-only     # print the newest run id
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import urllib3

BASE_URL = "https://deepmind.google.com/science/weatherlab/download/cyclones"
MODEL = "WNV3"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--notebook", default=os.getenv("NOTEBOOK_PATH"))
    p.add_argument("--work-dir", default=os.getenv("WORK_DIR", "/tmp/weathernext3_cards"))
    p.add_argument("--modes", default=os.getenv("CARD_MODES", "light"))
    p.add_argument("--layouts", default=os.getenv("CARD_LAYOUTS", "3x2"))
    p.add_argument("--run", default=os.getenv("RUN_OVERRIDE", ""),
                   help="force a run, e.g. 2026_10_14T12_00")
    p.add_argument("--manifest", default=None)
    p.add_argument("--check-only", action="store_true",
                   help="print the newest available run id and exit")
    return p.parse_args()


def newest_run(lookback_cycles: int = 12) -> str | None:
    """Newest WNV3 run with a member-track CSV on Weather Lab."""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    verify = os.getenv("SSL_VERIFY", "false").lower() == "true"
    now = datetime.now(timezone.utc)
    newest = now.replace(hour=now.hour - now.hour % 6, minute=0, second=0,
                         microsecond=0)
    for i in range(lookback_cycles + 1):
        run = (newest - timedelta(hours=6 * i)).strftime("%Y_%m_%dT%H_%M")
        url = (f"{BASE_URL}/{MODEL}/ensemble/cyclogenesis/csv/"
               f"{MODEL}_{run}_cyclogenesis.csv")
        try:
            r = requests.head(url, timeout=20, allow_redirects=True, verify=verify)
            if r.status_code == 405:
                r = requests.get(url, timeout=20, stream=True, verify=verify)
                r.close()
            if r.status_code == 200:
                return run
        except requests.RequestException:
            continue
    return None


def find_cell(cells, marker: str) -> str:
    for cell in cells:
        src = "".join(cell["source"])
        if cell["cell_type"] == "code" and marker in src:
            return src
    raise SystemExit(f"Notebook cell not found (marker: {marker!r}). "
                     "Was the notebook restructured?")


def main():
    args = parse_args()
    if args.check_only:
        run = newest_run()
        print(run or "")
        return 0 if run else 1

    if not args.notebook or not Path(args.notebook).exists():
        raise SystemExit(f"Notebook not found: {args.notebook}")
    work_dir = Path(args.work_dir)
    # Fonts bundled with the runner, so unattended runs never read ~/Downloads
    # (macOS asks for permission and the run waits until someone answers).
    font_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    layouts = [l.strip() for l in args.layouts.split(",") if l.strip()]

    cells = json.loads(Path(args.notebook).read_text())["cells"]
    setup = find_cell(cells, "SETTINGS  --  edit this block")
    style = find_cell(cells, "GLOBAL_MAP = {")
    cards = find_cell(cells, "def run_storm_impact_cards")

    # Forced settings, inserted after the notebook's SETTINGS block so they win.
    overrides = f'''
# ---- overrides from weathernext3_cards_runner ----
RUN_OVERRIDE = {args.run or None!r}
SAVE_DIR = {str(work_dir)!r}
DELETE_EXISTING_FOLDER = True
COLOR_MODES = {modes!r}
DISPLAY_MODES = []
FONT_DIR = {str(font_dir)!r}
GENERATE_STORM_IMPACT_CARDS = True
IMPACT_LAYOUTS = {layouts!r}
'''
    split_at = setup.index("\nimport os\n")
    setup = (setup[:split_at] + "\n" + overrides + setup[split_at:])
    setup = setup.replace("%matplotlib inline", "")

    # Published cards use Libre Franklin (SIL Open Font License, bundled in
    # assets/fonts); the notebook asks for Franklin ITC by file name.
    fonts = {f"FranklinITCStd-{w}.otf": f"LibreFranklin-{w}.ttf"
             for w in ("Black", "Bold", "Light")}
    if all((font_dir / new).exists() for new in fonts.values()):
        for old, new in fonts.items():
            setup, style, cards = (c.replace(old, new) for c in (setup, style, cards))

    import matplotlib
    matplotlib.use("Agg")
    namespace = {"__name__": "__weathernext3_cards__"}
    for label, code in (("setup", setup), ("style", style), ("cards", cards)):
        print(f"\n===== notebook section: {label} =====", flush=True)
        exec(compile(code, f"<notebook:{label}>", "exec"), namespace)
        if label == "style":
            # Great Lakes outline bundled with the runner (cloud runs have no
            # ~/weather/shapefiles).
            lakes = (Path(__file__).resolve().parent.parent / "assets" / "shapefiles"
                     / "GL250515_lam" / "GL250515_lam.shp")
            if lakes.exists():
                namespace["GLOBAL_MAP"]["great_lakes_shapefile"] = str(lakes)

    run = namespace["RUN"]
    produced = []
    for mode in modes:
        folder = work_dir / "impact_cards" / mode
        for layout in layouts:
            produced += sorted(str(p) for p in folder.glob(f"*_{layout}_{mode}.*"))
    manifest = {
        "model": MODEL,
        "run": run,
        "generated_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "modes": modes,
        "layouts": layouts,
        "cards": produced,
    }
    out = Path(args.manifest or work_dir / "cards_manifest.json")
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nRun {run}: {len(produced)} card(s); manifest {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
