"""Distribution histograms (galactic latitude, SNR, flux, DM).

Bin sizes and ranges were chosen to reproduce the IDL plots:
  * Galactic latitude b: bin width 10 deg, range -90..90
  * SNR (corrected):     bin width 1,      range Threshold..30 (log Y)
  * Flux (S_o, Jy):      bin width 5,      range 10..150        (log Y)
  * DM (corrected):      bin width 1,      range 0..30

Note: the IDL `transientanalisys_380_flux_v2.pro` histogram labeled
"Flux, Jy" is actually plotted from the `Tx1000_K` column (brightness
temperature), while the popup window for the selected transient uses the
`S_o` column (true flux density in Jansky). The two columns are different
physical quantities. We use `S_o` here so the red marker line matches the
"FLUX = ... Jy" value shown in the info panel.
"""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from src.data.transient_loader import TransientCatalog


class HistogramPanel:
    """Holds the four distribution histograms and a movable red marker line.

    The marker is updated by `set_marker(catalog, index)` and removed by
    `clear_marker()`. The figure is built once; updates only touch the marker
    artists, so they are cheap.
    """

    PARAM_KEYS = ("b", "snr", "flux", "dm")

    def __init__(
        self,
        selected: TransientCatalog,
        snr_threshold: float = 8.0,
        figure: Figure | None = None,
    ) -> None:
        self.figure = figure or Figure(figsize=(3.6, 8.4), layout="constrained")
        self.figure.clear()
        ax_list = self.figure.subplots(4, 1)
        self.axes: dict[str, "Axes"] = {  # type: ignore[name-defined]
            "b": ax_list[0],
            "snr": ax_list[1],
            "flux": ax_list[2],
            "dm": ax_list[3],
        }
        _gb_hist(self.axes["b"], selected.gb)
        _snr_hist(self.axes["snr"], selected.snr_corr, snr_threshold)
        _flux_hist(self.axes["flux"], selected.flux)
        _dm_hist(self.axes["dm"], selected.dm_corr)
        self._marker_lines: dict[str, "Line2D"] = {}  # type: ignore[name-defined]

    def set_marker(self, catalog: TransientCatalog, index: int) -> None:
        """Draw a thin red vertical line at this transient's value on each plot."""
        values = {
            "b": float(catalog.gb[index]) if catalog.gb is not None else None,
            "snr": float(catalog.snr_corr[index]),
            "flux": float(catalog.flux[index]),
            "dm": float(catalog.dm_corr[index]),
        }
        for key, val in values.items():
            if val is None:
                continue
            line = self._marker_lines.get(key)
            if line is None:
                line = self.axes[key].axvline(
                    val, color="red", linewidth=1.0, zorder=5
                )
                self._marker_lines[key] = line
            else:
                line.set_xdata([val, val])

    def clear_marker(self) -> None:
        for line in self._marker_lines.values():
            line.remove()
        self._marker_lines.clear()


def _gb_hist(ax, gb: np.ndarray) -> None:
    bins = np.arange(-90, 91, 10)
    ax.hist(gb, bins=bins, histtype="step", color="black")
    ax.set_xlim(-90, 90)
    ax.set_xticks(np.arange(-90, 91, 30))
    ax.set_xlabel("b, deg")
    ax.set_ylabel("N")
    ax.set_title("Galactic latitude", fontsize=10)


def _snr_hist(ax, snr_corr: np.ndarray, threshold: float) -> None:
    bins = np.arange(threshold, 31, 1)
    ax.hist(snr_corr, bins=bins, histtype="step", color="black")
    ax.set_yscale("log")
    ax.set_xlim(threshold, 30)
    ax.set_ylim(0.5, 300)
    ax.set_xlabel("S/N ratio")
    ax.set_ylabel("N")
    ax.set_title("SNR (corrected)", fontsize=10)


def _flux_hist(ax, flux_jy: np.ndarray) -> None:
    bins = np.arange(10, 151, 5)
    ax.hist(flux_jy, bins=bins, histtype="step", color="black")
    ax.set_yscale("log")
    ax.set_xlim(10, 150)
    ax.set_ylim(0.5, 300)
    ax.set_xlabel("Flux, Jy")
    ax.set_ylabel("N")
    ax.set_title("Flux (S_o)", fontsize=10)


def _dm_hist(ax, dm_corr: np.ndarray) -> None:
    bins = np.arange(0, 31, 1)
    ax.hist(dm_corr, bins=bins, histtype="step", color="black")
    ax.set_xlim(0, 30)
    ax.set_xlabel("DM, pc/cc")
    ax.set_ylabel("N")
    ax.set_title("DM (corrected)", fontsize=10)
