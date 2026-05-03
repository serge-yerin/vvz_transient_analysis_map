"""Main tkinter window: histograms on the left, transient map on the right.

Click on the map to highlight the closest transient and open the info panel.
The selection callback uses the same Euclidean-distance-in-(RA-hours, Dec-deg)
rule as the original IDL `Par_show` routine, so the same point is picked.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from src.data.transient_loader import TransientCatalog
from src.gui.info_panel import TransientInfoPanel
from src.maps.base import BackgroundMap
from src.plots.histograms import HistogramPanel


class TransientMapApp(tk.Tk):
    """Top-level application window."""

    def __init__(
        self,
        all_transients: TransientCatalog,
        selected: TransientCatalog,
        background_map: BackgroundMap,
        snr_threshold: float = 8.0,
    ) -> None:
        super().__init__()
        self.title("UTR-2 Transient analysis (20 MHz galactic background)")
        self.geometry("1500x900")

        self._all = all_transients
        self._selected = selected
        self._map = background_map
        self._snr_threshold = snr_threshold

        self._highlight_artist = None
        self._info_panel: TransientInfoPanel | None = None

        self._build_layout()

    # --------------------------------------------------------------- layout

    def _build_layout(self) -> None:
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        # Left: histograms
        left = ttk.Frame(container)
        left.pack(side="left", fill="y")
        self._hist_panel = HistogramPanel(self._selected, self._snr_threshold)
        hist_canvas = FigureCanvasTkAgg(self._hist_panel.figure, master=left)
        hist_canvas.get_tk_widget().configure(width=380)
        hist_canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        hist_canvas.draw()
        self._hist_canvas = hist_canvas

        # Right: transient map
        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)

        map_fig = Figure(figsize=(11, 8.5), layout="constrained")
        self._map_ax = map_fig.add_subplot(111)
        self._draw_map()

        map_canvas = FigureCanvasTkAgg(map_fig, master=right)
        map_canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(map_canvas, right)
        toolbar.update()
        map_canvas.mpl_connect("button_press_event", self._on_map_click)
        map_canvas.draw()
        self._map_canvas = map_canvas
        self._map_fig = map_fig

        self.bind("<Escape>", lambda _e: self._clear_selection())

    def _draw_map(self) -> None:
        ax = self._map_ax
        ax.clear()
        self._map.render(ax)

        ext = self._map.extent
        ax.set_xlim(ext.ra_left, ext.ra_right)  # 24 -> 0 to invert RA
        ax.set_ylim(ext.dec_bottom, ext.dec_top)
        ax.set_xlabel("RA, h")
        ax.set_ylabel("Dec, deg")
        ax.set_xticks(np.arange(0, 25, 4))
        ax.set_yticks(np.arange(-20, 81, 10))
        ax.set_title("Transient map  (click a point for parameters; Esc to clear)")

        # Plot the SNR-filtered transients on top.
        ax.plot(
            self._selected.ra,
            self._selected.dec,
            marker="D",
            mfc="none",
            mec="black",
            linestyle="none",
            markersize=6,
            markeredgewidth=1.0,
            picker=False,
        )

    # --------------------------------------------------------------- events

    def _on_map_click(self, event) -> None:
        if event.inaxes is not self._map_ax:
            return
        if event.xdata is None or event.ydata is None:
            return
        # Ignore zoom/pan toolbar clicks
        toolbar = self._map_canvas.toolbar
        if toolbar is not None and toolbar.mode != "":
            return

        ra_click = float(event.xdata)
        dec_click = float(event.ydata)

        # Same selection rule as IDL Par_show: nearest in (RA-hours, Dec-deg)
        # space, restricted to the SNR-filtered catalog.
        d2 = (
            (self._selected.ra - ra_click) ** 2
            + (self._selected.dec - dec_click) ** 2
        )
        idx = int(np.argmin(d2))
        self._highlight(idx)
        self._hist_panel.set_marker(self._selected, idx)
        self._hist_canvas.draw_idle()
        self._show_info(idx)

    def _highlight(self, idx: int) -> None:
        if self._highlight_artist is not None:
            self._highlight_artist.remove()
        (self._highlight_artist,) = self._map_ax.plot(
            [self._selected.ra[idx]],
            [self._selected.dec[idx]],
            marker="D",
            mfc="none",
            mec="red",
            markersize=12,
            markeredgewidth=2.0,
            linestyle="none",
        )
        self._map_canvas.draw_idle()

    def _show_info(self, idx: int) -> None:
        if self._info_panel is None or not self._info_panel.winfo_exists():
            self._info_panel = TransientInfoPanel(self)
        self._info_panel.show_for(self._selected, idx)

    def _clear_selection(self) -> None:
        if self._highlight_artist is not None:
            self._highlight_artist.remove()
            self._highlight_artist = None
            self._map_canvas.draw_idle()
        self._hist_panel.clear_marker()
        self._hist_canvas.draw_idle()
        if self._info_panel is not None:
            self._info_panel.hide()
