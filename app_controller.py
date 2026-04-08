from __future__ import annotations

import threading
import time

import cv2
import keyboard

from app.config import AppConfig
from app.control.calibration import Calibration
from app.control.gaze_mapper import GazeMapper
from app.core.action_arbiter import ActionArbiter
from app.core.session_state import SessionState
from app.display.display_manager import DisplayManager
from app.input.mouse_driver import MouseDriver
from app.intent.events import AppState, GestureType, InteractionMode, IntentType
from app.intent.gesture_detector import GestureDetector
from app.intent.intent_engine import IntentEngine
from app.tracking.camera import CameraStream
from app.tracking.face_tracker import FaceTracker
from app.tracking.head_pose import HeadPoseAdapter
from app.ui.calibration_overlay import CalibrationOverlay
from app.ui.debug_renderer import DebugRenderer


class AppController:
    def __init__(self, external_settings: dict | None = None) -> None:
        self.config = AppConfig()
        self._settings_lock = threading.Lock()
        self._retry_delay_s = 5.0
        if external_settings:
            for key, value in external_settings.items():
                if hasattr(self.config, key):
                    object.__setattr__(self.config, key, value)
        self.display_manager = DisplayManager()
        active_w, active_h = self.display_manager.get_active_monitor_size()
        self.camera = CameraStream(self.config)
        self.tracker = None
        self.head_pose_adapter = None
        self.mapper = GazeMapper(self.config, active_w, active_h)
        self.mouse = MouseDriver(self.display_manager)
        self.calibrator = Calibration(self.config, active_w, active_h)
        self.gesture_detector = GestureDetector(self.config)
        self.intent_engine = IntentEngine(self.config)
        self.arbiter = ActionArbiter(self.config)
        self.session = SessionState()
        self.renderer = DebugRenderer(self.config)
        self.overlay = CalibrationOverlay(self.config, active_w, active_h)
        self.running = True
        self._latest_iris: tuple[float, float] | None = None

    def apply_runtime_settings(self, updated: dict) -> None:
        with self._settings_lock:
            for key, value in updated.items():
                if hasattr(self.config, key):
                    object.__setattr__(self.config, key, value)
            self.mapper.reset_tracker_memory()
            self.mapper._reset_filters_to_output()
            self.session.clear_cursor_history()
            self.session.last_intent_reason = "runtime settings updated"
            self.session.last_reject_reason = ""

    def _active_monitor_signature(self) -> str:
        return self.display_manager.active_monitor.layout_signature

    def _refresh_active_monitor_geometry(self) -> None:
        active_w, active_h = self.display_manager.get_active_monitor_size()
        self.mapper.resize_monitor_space(active_w, active_h)
        self.mapper.set_calibration(None)
        self.calibrator = Calibration(self.config, active_w, active_h)
        self.overlay = CalibrationOverlay(self.config, active_w, active_h)
        self.mouse.reset_motion_state()
        self.session.clear_cursor_history()

    def _switch_monitor(self, delta: int) -> None:
        self.display_manager.refresh()
        if delta > 0:
            self.display_manager.next_monitor()
        else:
            self.display_manager.previous_monitor()
        self._refresh_active_monitor_geometry()
        sig = self._active_monitor_signature()
        if self.calibrator.load(expected_monitor_signature=sig):
            data = self.calibrator.get_data()
            if data is not None:
                self.mapper.set_calibration(data.transform_matrix)
                self.mapper.reset_all()
                self.gesture_detector.reset_transient()
                self.mouse.reset_motion_state()
                self.session.app_state = AppState.TRACKING
                self.session.interaction_mode = InteractionMode.POINTER
                self.session.drag_active = False
                self.session.clear_cursor_history()
                self.session.last_reject_reason = ""
                self.session.last_intent_reason = f"loaded calibration for {sig}"
                return
        self.start_calibration()

    def _get_fused_iris(self, result) -> tuple[float, float] | None:
        if not result.face_detected:
            return None
        left = getattr(result, "left_iris_px", None)
        right = getattr(result, "right_iris_px", None)
        if left is not None and right is not None:
            return ((left[0] + right[0]) / 2.0, (left[1] + right[1]) / 2.0)
        if left is not None:
            return float(left[0]), float(left[1])
        if right is not None:
            return float(right[0]), float(right[1])
        return None

    def _extract_pitch_deg(self, result, frame_w: int, frame_h: int) -> float | None:
        head_pose = getattr(result, "head_pose", None)
        if head_pose is not None:
            for attr in ("pitch_deg", "pitch", "x_rotation_deg"):
                value = getattr(head_pose, attr, None)
                if value is not None:
                    return float(value)
        if result.face_detected and getattr(result, "landmarks", None) is not None:
            if self.head_pose_adapter is None:
                self.head_pose_adapter = HeadPoseAdapter(frame_w, frame_h)
            pose = self.head_pose_adapter.estimate(result.landmarks, frame_w, frame_h)
            if pose is not None:
                return pose.pitch_deg
        return None

    def run(self) -> None:
        while self.running:
            try:
                self._run_once()
                break
            except cv2.error:
                self.mouse.full_reset()
                if not self.running:
                    break
                time.sleep(self._retry_delay_s)
            except Exception:
                self.mouse.full_reset()
                if not self.running:
                    break
                time.sleep(self._retry_delay_s)
        self.shutdown()

    def _run_once(self) -> None:
        self.camera.open()
        frame_w, frame_h = self.camera.actual_resolution
        self.tracker = FaceTracker(frame_w, frame_h, self.config)
        self.head_pose_adapter = HeadPoseAdapter(frame_w, frame_h)
        keyboard.add_hotkey(self.config.hotkey_pause_resume, self.toggle_pause)
        keyboard.add_hotkey(self.config.hotkey_recalibrate, self.start_calibration)
        keyboard.add_hotkey(self.config.hotkey_quit, self.stop)
        keyboard.add_hotkey(self.config.hotkey_next_monitor, lambda: self._switch_monitor(+1))
        keyboard.add_hotkey(self.config.hotkey_prev_monitor, lambda: self._switch_monitor(-1))
        if self.calibrator.load(expected_monitor_signature=self._active_monitor_signature()):
            data = self.calibrator.get_data()
            if data is not None:
                self.mapper.set_calibration(data.transform_matrix)
                self.mapper.reset_all()
                self.session.app_state = AppState.TRACKING
            else:
                self.start_calibration()
        else:
            self.start_calibration()
        while self.running:
            frame = self.camera.read()
            if frame is None:
                raise RuntimeError("Camera read failed.")
            result = self.tracker.process(frame)
            iris = self._get_fused_iris(result)
            self._latest_iris = iris
            if self.session.app_state == AppState.CALIBRATING:
                self._run_calibrating(iris)
                display = self.overlay.render(self.calibrator)
            elif self.session.app_state == AppState.PAUSED:
                self.arbiter.tick(self.session, self.mouse)
                display = self.renderer.render(
                    frame, result,
                    app_state="PAUSED",
                    is_calibrated=self.mapper.is_calibrated(),
                    interaction_mode=self.session.interaction_mode.name,
                    drag_active=self.session.drag_active,
                    last_intent_reason=self.session.last_intent_reason,
                    last_reject_reason=self.session.last_reject_reason,
                    frozen=False,
                    active_monitor=self.display_manager.active_monitor.index,
                    monitor_label=self.display_manager.active_monitor.device_name,
                    dm=self.display_manager,
                )
            else:
                display = self._run_tracking(frame, frame_w, frame_h, result, iris)
            if self.config.debug_enabled:
                cv2.imshow(self.config.window_name, display)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    self.stop()
            else:
                cv2.waitKey(1)

    def stop(self) -> None:
        self.running = False

    def shutdown(self) -> None:
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        try:
            self.mouse.full_reset()
        except Exception:
            pass
        try:
            self.camera.release()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    def _run_calibrating(self, iris: tuple[float, float] | None) -> None:
        self.calibrator.update(iris)
        if self.calibrator.is_done():
            data = self.calibrator.get_data()
            self.mapper.set_calibration(data.transform_matrix if data is not None else None)
            self.calibrator.save()
            self.mapper.reset_all()
            self.gesture_detector.reset_transient()
            self.session.app_state = AppState.TRACKING
            self.session.interaction_mode = InteractionMode.POINTER
            self.session.drag_active = False
            self.session.clear_cursor_history()

    def _run_tracking(self, frame, frame_w: int, frame_h: int, result, iris):
        left_ear = 0.0
        right_ear = 0.0
        cursor = None
        frozen = False
        if result.face_detected and result.landmarks is not None:
            metrics = self.gesture_detector.extract_metrics(result.landmarks, frame_w, frame_h)
            left_ear = metrics.left_ear
            right_ear = metrics.right_ear
            pitch_deg = self._extract_pitch_deg(result, frame_w, frame_h)
            candidates = []
            candidates.extend(self.gesture_detector.detect_blink_gestures(metrics))
            candidates.extend(self.gesture_detector.detect_nod_gesture(pitch_deg))
            action_candidates = []
            for cand in candidates:
                if cand.gesture == GestureType.EYE_CLOSURE_ONSET:
                    self.mapper.freeze(cand.timestamp)
                else:
                    action_candidates.append(cand)
            if iris is not None and self.mapper.is_calibrated():
                frozen = self.mapper.is_frozen()
                local_cursor = self.mapper.update(iris)
                self.session.note_cursor(local_cursor, frozen=frozen)
                virtual_cursor = self.display_manager.local_to_virtual(*local_cursor)
                cursor = virtual_cursor
                self.mouse.move(*virtual_cursor)
            intents = self.intent_engine.candidates_to_intents(action_candidates, self.session)
            for intent in intents:
                if intent.intent == IntentType.PAUSE_TOGGLE:
                    self.toggle_pause()
                    continue
                self.arbiter.apply(intent, self.session, self.mouse)
        self.arbiter.tick(self.session, self.mouse)
        return self.renderer.render(
            frame,
            result,
            left_ear=left_ear,
            right_ear=right_ear,
            cursor_pos=cursor,
            app_state=self.session.app_state.name,
            is_calibrated=self.mapper.is_calibrated(),
            interaction_mode=self.session.interaction_mode.name,
            drag_active=self.session.drag_active,
            last_intent_reason=self.session.last_intent_reason,
            last_reject_reason=self.session.last_reject_reason,
            frozen=frozen,
            active_monitor=self.display_manager.active_monitor.index,
            monitor_label=self.display_manager.active_monitor.device_name,
            dm=self.display_manager,
        )

    def start_calibration(self) -> None:
        self.calibrator.start(monitor_signature=self._active_monitor_signature())
        self.mapper.set_calibration(None)
        self.mapper.reset_all()
        self.gesture_detector.reset_transient()
        self.mouse.emergency_release()
        self.mouse.reset_motion_state()
        self.session.app_state = AppState.CALIBRATING
        self.session.interaction_mode = InteractionMode.POINTER
        self.session.drag_active = False
        self.session.clear_cursor_history()
        self.session.last_intent_reason = ""
        self.session.last_reject_reason = ""

    def toggle_pause(self) -> None:
        if self.session.app_state == AppState.TRACKING:
            self.session.app_state = AppState.PAUSED
            self.mapper.reset_tracker_memory()
            self.gesture_detector.reset_transient()
            self.mouse.emergency_release()
            self.mouse.reset_motion_state()
            self.session.drag_active = False
            self.session.interaction_mode = InteractionMode.POINTER
            self.session.clear_cursor_history()
        elif self.session.app_state == AppState.PAUSED:
            if self._latest_iris is not None and self.mapper.is_calibrated():
                self.mapper.reanchor_to_tracker(self._latest_iris)
            else:
                self.mapper.reset_all()
            self.gesture_detector.reset_transient()
            self.mouse.reset_motion_state()
            self.session.app_state = AppState.TRACKING
            self.session.interaction_mode = InteractionMode.POINTER
            self.session.clear_cursor_history()
