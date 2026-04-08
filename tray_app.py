from __future__ import annotations

from PIL import Image, ImageDraw
import pystray


class TrayApp:
    def __init__(self, runtime, on_open_settings=None) -> None:
        self.runtime = runtime
        self.on_open_settings = on_open_settings
        self.icon = pystray.Icon("EyeMouse")
        self.icon.icon = self._make_icon()
        self.icon.title = "Eye Mouse"

    def _make_icon(self):
        img = Image.new("RGB", (64, 64), color=(26, 26, 26))
        draw = ImageDraw.Draw(img)
        draw.ellipse((8, 18, 56, 46), outline=(0, 220, 255), width=4)
        draw.ellipse((26, 24, 38, 36), fill=(0, 220, 255))
        return img

    def run(self) -> None:
        self.icon.menu = pystray.Menu(
            pystray.MenuItem("Start", self._start),
            pystray.MenuItem("Stop", self._stop),
            pystray.MenuItem("Pause / Resume", self._pause),
            pystray.MenuItem("Recalibrate", self._recalibrate),
            pystray.MenuItem("Previous Monitor", self._prev_monitor),
            pystray.MenuItem("Next Monitor", self._next_monitor),
            pystray.MenuItem("Settings", self._settings),
            pystray.MenuItem("Quit", self._quit),
        )
        self.icon.run()

    def _start(self, icon, item) -> None:
        self.runtime.start()

    def _stop(self, icon, item) -> None:
        self.runtime.stop()

    def _pause(self, icon, item) -> None:
        self.runtime.toggle_pause()

    def _recalibrate(self, icon, item) -> None:
        self.runtime.recalibrate()

    def _prev_monitor(self, icon, item) -> None:
        self.runtime.switch_monitor_prev()

    def _next_monitor(self, icon, item) -> None:
        self.runtime.switch_monitor_next()

    def _settings(self, icon, item) -> None:
        if self.on_open_settings is not None:
            self.on_open_settings()

    def _quit(self, icon, item) -> None:
        self.runtime.stop()
        self.icon.stop()
