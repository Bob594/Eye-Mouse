from __future__ import annotations

import cv2


class DebugRenderer:
    def __init__(self, config) -> None:
        self.cfg = config

    def render(self, frame, result, **kwargs):
        display = frame.copy()
        app_state = kwargs.get("app_state", "UNKNOWN")
        interaction_mode = kwargs.get("interaction_mode", "POINTER")
        last_intent_reason = kwargs.get("last_intent_reason", "None")
        last_reject_reason = kwargs.get("last_reject_reason", "None")
        drag_active = kwargs.get("drag_active", False)
        left_ear = kwargs.get("left_ear", 0.0)
        right_ear = kwargs.get("right_ear", 0.0)
        cursor_pos = kwargs.get("cursor_pos", None)
        frozen = kwargs.get("frozen", False)
        active_monitor = kwargs.get("active_monitor", None)
        monitor_label = kwargs.get("monitor_label", "Unknown")
        dm = kwargs.get("dm", None)
        h, w = display.shape[:2]
        cv2.rectangle(display, (0, 0), (430, 220), (0, 0, 0), -1)
        color = (0, 255, 0)
        if app_state == "PAUSED":
            color = (0, 165, 255)
        if interaction_mode == "SCROLL":
            color = (255, 255, 0)
        if drag_active:
            color = (255, 0, 255)
        y = 24
        self._txt(display, f"STATE: {app_state}", (10, y), color, 0.65)
        y += 24
        self._txt(display, f"MODE: {interaction_mode}", (10, y), color, 0.65)
        y += 22
        self._txt(display, f"FROZEN: {frozen}", (10, y), (210, 210, 210), 0.55)
        y += 20
        self._txt(display, f"LEFT EAR: {left_ear:.3f}", (10, y), (210, 210, 210), 0.55)
        y += 18
        self._txt(display, f"RIGHT EAR: {right_ear:.3f}", (10, y), (210, 210, 210), 0.55)
        y += 18
        if cursor_pos is not None:
            self._txt(display, f"CURSOR: {cursor_pos[0]}, {cursor_pos[1]}", (10, y), (210, 210, 210), 0.55)
            y += 18
        self._txt(display, f"MONITOR: {active_monitor} {monitor_label}", (10, y), (0, 255, 255), 0.50)
        y += 18
        self._txt(display, f"LAST: {last_intent_reason[:50]}", (10, y), (180, 255, 180), 0.46)
        y += 18
        self._txt(display, f"REJECT: {last_reject_reason[:48]}", (10, y), (0, 0, 255), 0.46)
        if drag_active:
            cv2.putText(display, "DRAG ACTIVE", (w // 2 - 80, h - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 0, 255), 2)
        if dm is not None:
            self._draw_topology(display, dm)
        return display

    def _draw_topology(self, canvas, dm) -> None:
        v_w = max(dm.virtual_width, 1)
        v_h = max(dm.virtual_height, 1)
        v_l = dm.virtual_left
        v_t = dm.virtual_top
        map_w = 140
        map_h = max(int(map_w * (v_h / v_w)), 40)
        start_x = canvas.shape[1] - map_w - 10
        start_y = 10
        cv2.rectangle(canvas, (start_x, start_y), (start_x + map_w, start_y + map_h), (50, 50, 50), -1)
        for mon in dm.monitors:
            m_l = int(start_x + (mon.left - v_l) * (map_w / v_w))
            m_t = int(start_y + (mon.top - v_t) * (map_h / v_h))
            m_w = max(int(mon.width * (map_w / v_w)), 2)
            m_h = max(int(mon.height * (map_h / v_h)), 2)
            color = (0, 255, 0) if mon.index == dm.active_monitor_index else (150, 150, 150)
            thickness = 2 if mon.index == dm.active_monitor_index else 1
            cv2.rectangle(canvas, (m_l, m_t), (m_l + m_w, m_t + m_h), color, thickness)
            if mon.is_primary:
                cv2.circle(canvas, (m_l + 5, m_t + 5), 2, (0, 255, 255), -1)

    def _txt(self, img, text, pos, color, scale=None):
        cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale if scale is not None else self.cfg.font_scale, color, self.cfg.font_thickness, cv2.LINE_AA)
