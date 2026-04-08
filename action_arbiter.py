from __future__ import annotations

import math

from app.core.session_state import SessionState
from app.input.mouse_driver import MouseDriver
from app.intent.events import AppState, IntentEvent, IntentType, InteractionMode


class ActionArbiter:
    def __init__(self, config) -> None:
        self.config = config

    def _recent_samples(self, session: SessionState):
        now = session.now()
        cutoff = now - self.config.stable_cursor_window_s
        return [s for s in session.cursor_history if s.timestamp >= cutoff]

    def _cursor_is_stable(self, session: SessionState) -> bool:
        samples = self._recent_samples(session)
        if len(samples) < self.config.stable_cursor_required_frames:
            return False
        samples = samples[-self.config.stable_cursor_required_frames :]
        xs = [s.x for s in samples]
        ys = [s.y for s in samples]
        cx = sum(xs) / len(xs)
        cy = sum(ys) / len(ys)
        max_r = 0.0
        for s in samples:
            max_r = max(max_r, math.hypot(s.x - cx, s.y - cy))
        return max_r <= self.config.stable_cursor_radius_px

    def apply(self, intent: IntentEvent, session: SessionState, mouse: MouseDriver) -> bool:
        now = intent.timestamp
        if intent.intent == IntentType.LEFT_CLICK:
            if session.app_state != AppState.TRACKING:
                session.last_reject_reason = "left click rejected: not tracking"
                return False
            if session.interaction_mode != InteractionMode.POINTER:
                session.last_reject_reason = "left click rejected: not in pointer mode"
                return False
            if not self._cursor_is_stable(session):
                session.last_reject_reason = "left click rejected: cursor unstable"
                return False
            if (now - session.last_click_ts) < self.config.blink_cooldown_s:
                session.last_reject_reason = "left click rejected: cooldown"
                return False
            mouse.left_click()
            session.last_click_ts = now
            session.last_intent_reason = intent.reason
            session.last_reject_reason = ""
            return True

        if intent.intent == IntentType.RIGHT_CLICK:
            if session.app_state != AppState.TRACKING:
                session.last_reject_reason = "right click rejected: not tracking"
                return False
            if session.interaction_mode != InteractionMode.POINTER:
                session.last_reject_reason = "right click rejected: not in pointer mode"
                return False
            if not self._cursor_is_stable(session):
                session.last_reject_reason = "right click rejected: cursor unstable"
                return False
            if (now - session.last_click_ts) < self.config.blink_cooldown_s:
                session.last_reject_reason = "right click rejected: cooldown"
                return False
            mouse.right_click()
            session.last_click_ts = now
            session.last_intent_reason = intent.reason
            session.last_reject_reason = ""
            return True

        if intent.intent == IntentType.DRAG_START:
            if session.app_state != AppState.TRACKING:
                session.last_reject_reason = "drag start rejected: not tracking"
                return False
            if session.drag_active:
                session.last_reject_reason = "drag start rejected: already dragging"
                return False
            if not self._cursor_is_stable(session):
                session.last_reject_reason = "drag start rejected: cursor unstable"
                return False
            if (now - session.last_drag_toggle_ts) < self.config.drag_toggle_cooldown_s:
                session.last_reject_reason = "drag start rejected: cooldown"
                return False
            mouse.left_down()
            session.drag_active = True
            session.interaction_mode = InteractionMode.DRAGGING
            session.last_drag_toggle_ts = now
            session.last_intent_reason = intent.reason
            session.last_reject_reason = ""
            return True

        if intent.intent == IntentType.DRAG_END:
            if not session.drag_active:
                session.last_reject_reason = "drag end rejected: drag inactive"
                return False
            if (now - session.last_drag_toggle_ts) < self.config.drag_toggle_cooldown_s:
                session.last_reject_reason = "drag end rejected: cooldown"
                return False
            mouse.left_up()
            session.drag_active = False
            session.interaction_mode = InteractionMode.POINTER
            session.last_drag_toggle_ts = now
            session.last_intent_reason = intent.reason
            session.last_reject_reason = ""
            return True

        if intent.intent == IntentType.SCROLL_MODE_TOGGLE:
            if session.app_state == AppState.PAUSED:
                session.last_reject_reason = "scroll toggle rejected: paused"
                return False
            if session.drag_active:
                session.last_reject_reason = "scroll toggle rejected: dragging"
                return False
            session.interaction_mode = InteractionMode.POINTER if session.interaction_mode == InteractionMode.SCROLL else InteractionMode.SCROLL
            session.last_scroll_mode_activity_ts = now
            session.last_intent_reason = intent.reason
            session.last_reject_reason = ""
            return True

        if intent.intent == IntentType.SCROLL_UP:
            if session.interaction_mode != InteractionMode.SCROLL:
                session.last_reject_reason = "scroll up rejected: not in scroll mode"
                return False
            if (now - session.last_scroll_ts) < self.config.nod_cooldown_s:
                session.last_reject_reason = "scroll up rejected: cooldown"
                return False
            mouse.scroll(+self.config.scroll_step)
            session.last_scroll_ts = now
            session.last_scroll_mode_activity_ts = now
            session.last_intent_reason = intent.reason
            session.last_reject_reason = ""
            return True

        if intent.intent == IntentType.SCROLL_DOWN:
            if session.interaction_mode != InteractionMode.SCROLL:
                session.last_reject_reason = "scroll down rejected: not in scroll mode"
                return False
            if (now - session.last_scroll_ts) < self.config.nod_cooldown_s:
                session.last_reject_reason = "scroll down rejected: cooldown"
                return False
            mouse.scroll(-self.config.scroll_step)
            session.last_scroll_ts = now
            session.last_scroll_mode_activity_ts = now
            session.last_intent_reason = intent.reason
            session.last_reject_reason = ""
            return True

        return False

    def tick(self, session: SessionState, mouse: MouseDriver) -> None:
        now = session.now()
        if session.interaction_mode == InteractionMode.SCROLL and (now - session.last_scroll_mode_activity_ts) > self.config.scroll_mode_timeout_s:
            session.interaction_mode = InteractionMode.POINTER
        if session.app_state == AppState.PAUSED and session.drag_active:
            mouse.emergency_release()
            session.drag_active = False
            session.interaction_mode = InteractionMode.POINTER
