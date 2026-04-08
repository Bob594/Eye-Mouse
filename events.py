from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class AppState(Enum):
    CALIBRATING = auto()
    TRACKING = auto()
    PAUSED = auto()


class InteractionMode(Enum):
    POINTER = auto()
    SCROLL = auto()
    DRAGGING = auto()


class GestureType(Enum):
    NONE = auto()
    EYE_CLOSURE_ONSET = auto()
    LEFT_BLINK = auto()
    RIGHT_BLINK = auto()
    BOTH_BLINK_SHORT = auto()
    BOTH_BLINK_LONG = auto()
    NOD_UP = auto()
    NOD_DOWN = auto()
    DRAG_TOGGLE = auto()


class IntentType(Enum):
    NONE = auto()
    LEFT_CLICK = auto()
    RIGHT_CLICK = auto()
    SCROLL_UP = auto()
    SCROLL_DOWN = auto()
    DRAG_START = auto()
    DRAG_END = auto()
    SCROLL_MODE_TOGGLE = auto()
    PAUSE_TOGGLE = auto()


@dataclass
class GestureCandidate:
    gesture: GestureType
    confidence: float
    timestamp: float
    reason: str = ""


@dataclass
class IntentEvent:
    intent: IntentType
    confidence: float
    timestamp: float
    reason: str = ""
