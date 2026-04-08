from __future__ import annotations

import threading


class AppRuntime:
    def __init__(self, controller_factory):
        self.controller_factory = controller_factory
        self.controller = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self.controller = self.controller_factory()
            self._thread = threading.Thread(target=self._run_wrapper, args=(self.controller,), daemon=True)
            self._thread.start()
            return True

    def _run_wrapper(self, controller) -> None:
        try:
            controller.run()
        finally:
            try:
                controller.mouse.full_reset()
            except Exception:
                pass
            with self._lock:
                if self.controller is controller:
                    self.controller = None
                self._thread = None

    def stop(self) -> bool:
        with self._lock:
            controller = self.controller
            thread = self._thread
        if controller is None or thread is None:
            return False
        controller.stop()
        thread.join(timeout=2.0)
        with self._lock:
            if self._thread is thread:
                self._thread = None
            if self.controller is controller:
                self.controller = None
        return True

    def toggle_pause(self) -> None:
        with self._lock:
            controller = self.controller
        if controller is not None:
            controller.toggle_pause()

    def recalibrate(self) -> None:
        with self._lock:
            controller = self.controller
        if controller is not None:
            controller.start_calibration()

    def switch_monitor_next(self) -> None:
        with self._lock:
            controller = self.controller
        if controller is not None and hasattr(controller, "_switch_monitor"):
            controller._switch_monitor(+1)

    def switch_monitor_prev(self) -> None:
        with self._lock:
            controller = self.controller
        if controller is not None and hasattr(controller, "_switch_monitor"):
            controller._switch_monitor(-1)

    def apply_settings(self, updated: dict) -> None:
        with self._lock:
            controller = self.controller
        if controller is not None and hasattr(controller, "apply_runtime_settings"):
            controller.apply_runtime_settings(updated)
