"""Toplevel popup that lists the parameters of the currently selected transient."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from src.coordinates.transforms import hours_to_hms
from src.data.transient_loader import TransientCatalog


class TransientInfoPanel(tk.Toplevel):
    """A small always-on-top window that displays one transient's parameters."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title("Transient parameters")
        self.geometry("260x260")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.hide)

        self._labels: dict[str, ttk.Label] = {}
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        for row, key in enumerate(
            ["TRS #", "RA", "DEC", "l", "b", "SNR_CORR", "FLUX", "DM_CORR"]
        ):
            ttk.Label(frame, text=f"{key}:", font=("TkDefaultFont", 10, "bold")).grid(
                row=row, column=0, sticky="w", padx=(0, 8), pady=2
            )
            value = ttk.Label(frame, text="-", font=("TkDefaultFont", 10))
            value.grid(row=row, column=1, sticky="w", pady=2)
            self._labels[key] = value

        ttk.Button(frame, text="Close (Esc)", command=self.hide).grid(
            row=99, column=0, columnspan=2, pady=(12, 0)
        )
        self.bind("<Escape>", lambda _e: self.hide())
        self.withdraw()

    def show_for(self, catalog: TransientCatalog, index: int) -> None:
        ra = catalog.ra[index]
        h, m, s = hours_to_hms(ra)
        self._labels["TRS #"].configure(text=str(index + 1))
        self._labels["RA"].configure(text=f"{h:02d}h {m:02d}m {s:04.1f}s  ({ra:.3f} h)")
        self._labels["DEC"].configure(text=f"{catalog.dec[index]:+.3f} deg")
        if catalog.gl is not None:
            self._labels["l"].configure(text=f"{catalog.gl[index]:7.3f} deg")
        if catalog.gb is not None:
            self._labels["b"].configure(text=f"{catalog.gb[index]:+7.3f} deg")
        self._labels["SNR_CORR"].configure(text=f"{catalog.snr_corr[index]:.3f}")
        self._labels["FLUX"].configure(text=f"{catalog.flux[index]:.2f} Jy")
        self._labels["DM_CORR"].configure(text=f"{catalog.dm_corr[index]:.3f} pc/cc")
        self.deiconify()
        self.lift()

    def hide(self) -> None:
        self.withdraw()
