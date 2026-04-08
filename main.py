from __future__ import annotations

from app.app_host.app_runtime import AppRuntime
from app.app_host.settings_store import SettingsStore
from app.app_host.tray_app import TrayApp
from app.core.app_controller import AppController
from app.ui.settings_window import SettingsWindow

DEFAULT_SETTINGS = {
    "dead_zone_px": 2.0,
    "stable_cursor_radius_px": 18.0,
    "cursor_freeze_on_blink_s": 0.20,
    "scroll_step": 120,
    "nod_pitch_threshold_deg": 8.0,
    "blink_min_duration_s": 0.08,
    "blink_max_duration_s": 0.45,
    "blink_cooldown_s": 0.45,
    "one_euro_min_cutoff": 0.8,
    "one_euro_beta": 0.015,
}


def main() -> None:
    store = SettingsStore()
    settings = store.load(DEFAULT_SETTINGS)

    def controller_factory():
        return AppController(external_settings=settings)

    runtime = AppRuntime(controller_factory=controller_factory)

    def open_settings():
        def save_settings(updated):
            nonlocal settings
            settings = updated
            store.save(settings)
            runtime.apply_settings(updated)
        SettingsWindow(settings, save_settings).show()

    tray = TrayApp(runtime=runtime, on_open_settings=open_settings)
    tray.run()


if __name__ == "__main__":
    main()
