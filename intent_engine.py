from __future__ import annotations

from app.core.session_state import SessionState
from app.intent.events import GestureCandidate, GestureType, IntentEvent, IntentType, InteractionMode


class IntentEngine:
    def __init__(self, config) -> None:
        self.config = config

    def candidates_to_intents(self, candidates: list[GestureCandidate], session: SessionState) -> list[IntentEvent]:
        intents: list[IntentEvent] = []
        for cand in candidates:
            if cand.gesture == GestureType.LEFT_BLINK:
                intents.append(IntentEvent(IntentType.LEFT_CLICK, cand.confidence, cand.timestamp, cand.reason))
            elif cand.gesture == GestureType.RIGHT_BLINK:
                intents.append(IntentEvent(IntentType.RIGHT_CLICK, cand.confidence, cand.timestamp, cand.reason))
            elif cand.gesture == GestureType.DRAG_TOGGLE:
                intents.append(IntentEvent(IntentType.DRAG_END if session.drag_active else IntentType.DRAG_START, cand.confidence, cand.timestamp, cand.reason))
            elif cand.gesture == GestureType.BOTH_BLINK_SHORT:
                intents.append(IntentEvent(IntentType.SCROLL_MODE_TOGGLE, cand.confidence, cand.timestamp, cand.reason))
            elif cand.gesture == GestureType.BOTH_BLINK_LONG:
                intents.append(IntentEvent(IntentType.PAUSE_TOGGLE, cand.confidence, cand.timestamp, cand.reason))
            elif cand.gesture == GestureType.NOD_UP and session.interaction_mode == InteractionMode.SCROLL:
                intents.append(IntentEvent(IntentType.SCROLL_UP, cand.confidence, cand.timestamp, cand.reason))
            elif cand.gesture == GestureType.NOD_DOWN and session.interaction_mode == InteractionMode.SCROLL:
                intents.append(IntentEvent(IntentType.SCROLL_DOWN, cand.confidence, cand.timestamp, cand.reason))
        return intents
