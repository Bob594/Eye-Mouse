from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class SettingsWindow:
    def __init__(self, settings: dict, on_save) -> None:
        self.settings = settings
        self.on_save = on_save

    def show(self) -> None:
        root = tk.Tk()
        root.title("Eye Mouse Settings")
        root.geometry("460x460")
        root.resizable(False, False)
        values = {}
        keys = [
            "dead_zone_px",
            "stable_cursor_radius_px",
            "cursor_freeze_on_blink_s",
            "scroll_step",
            "nod_pitch_threshold_deg",
            "blink_min_duration_s",
            "blink_max_duration_s",
            "blink_cooldown_s",
            "one_euro_min_cutoff",
            "one_euro_beta",
        ]
        row = 0
        for key in keys:
            ttk.Label(root, text=key).grid(row=row, column=0, sticky="w", padx=12, pady=8)
            var = tk.StringVar(value=str(self.settings.get(key, "")))
            ttk.Entry(root, textvariable=var, width=20).grid(row=row, column=1, padx=12, pady=8)
            values[key] = var
            row += 1

        def save():
            updated = dict(self.settings)
            for key, var in values.items():
                try:
                    updated[key] = float(var.get().strip())
                except ValueError:
                    pass
            self.on_save(updated)
            root.destroy()

        ttk.Button(root, text="Save", command=save).grid(row=row, column=0, columnspan=2, pady=20)
        root.mainloop()
