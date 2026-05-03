"""Entry point for the UTR-2 transient analysis viewer.

Run from the project root:

    python main.py

Optional arguments allow pointing the program at a different CSV or background
image (useful when a higher resolution map becomes available).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("TkAgg")  # required: must be set before pyplot/Figure imports happen

from src.coordinates.transforms import equatorial_to_galactic
from src.data.transient_loader import load_transients
from src.gui.main_window import TransientMapApp
from src.maps.jpeg_map import JpegBackgroundMap

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CSV = PROJECT_ROOT / "Data" / "Tr_380_Flux.csv"
DEFAULT_MAP = PROJECT_ROOT / "assets" / "GalBackgr20MHz-1.jpg"
SNR_THRESHOLD = 8.0
MAX_DEC_DEG = 75.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Transient CSV")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="Background JPEG")
    parser.add_argument(
        "--snr-threshold",
        type=float,
        default=SNR_THRESHOLD,
        help="Hide transients with SNR_corr below this value",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    catalog = load_transients(args.csv)
    gl, gb = equatorial_to_galactic(catalog.ra, catalog.dec)
    catalog = catalog.with_galactic(gl, gb)

    mask = (catalog.snr_corr > args.snr_threshold) & (catalog.dec < MAX_DEC_DEG)
    selected = catalog.selection(mask)
    print(
        f"Loaded {len(catalog)} transients; "
        f"{len(selected)} pass SNR>{args.snr_threshold} & Dec<{MAX_DEC_DEG} deg."
    )

    background = JpegBackgroundMap(args.map)
    app = TransientMapApp(
        all_transients=catalog,
        selected=selected,
        background_map=background,
        snr_threshold=args.snr_threshold,
    )
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
