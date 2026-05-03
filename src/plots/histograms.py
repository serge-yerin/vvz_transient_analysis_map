"""Distribution histograms (galactic latitude, SNR, flux, DM).

Bin sizes and ranges were chosen to reproduce the IDL plots:
  * Galactic latitude b: bin width 10 deg, range -90..90
  * SNR (corrected):     bin width 1,      range Threshold..30 (log Y)
  * Flux (Tx1000_K):     bin width 5,      range 21..120        (log Y)
  * DM (corrected):      bin width 1,      range 0..30
"""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure

from src.data.transient_loader import TransientCatalog


def build_histograms_figure(
    selected: TransientCatalog,
    snr_threshold: float = 8.0,
    figure: Figure | None = None,
) -> Figure:
    """Render the four distribution histograms onto a Figure with 4 stacked subplots.

    `selected` should be the SNR/Dec-filtered catalog (i.e. what the IDL code
    plots after applying `inds = where(SNR_corr gt Threshold and dec lt 75)`).
    """
    fig = figure or Figure(figsize=(3.6, 8.4), layout="constrained")
    fig.clear()
    axes = fig.subplots(4, 1)

    _gb_hist(axes[0], selected.gb)
    _snr_hist(axes[1], selected.snr_corr, snr_threshold)
    _flux_hist(axes[2], selected.tx1000_k)
    _dm_hist(axes[3], selected.dm_corr)

    return fig


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


def _flux_hist(ax, tx1000_k: np.ndarray) -> None:
    bins = np.arange(21, 121, 5)
    ax.hist(tx1000_k, bins=bins, histtype="step", color="black")
    ax.set_yscale("log")
    ax.set_xlim(21, 120)
    ax.set_ylim(0.5, 300)
    ax.set_xlabel("Flux, Jy")
    ax.set_ylabel("N")
    ax.set_title("Flux", fontsize=10)


def _dm_hist(ax, dm_corr: np.ndarray) -> None:
    bins = np.arange(0, 31, 1)
    ax.hist(dm_corr, bins=bins, histtype="step", color="black")
    ax.set_xlim(0, 30)
    ax.set_xlabel("DM, pc/cc")
    ax.set_ylabel("N")
    ax.set_title("DM (corrected)", fontsize=10)
