from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    # Camera
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    mirror_frame: bool = True
    window_name: str = "Eye Mouse"

    # Calibration
    calibration_frames: int = 40
    calibration_settle_frames: int = 15
    calibration_path: Path = Path("calibration_data/calibration.npz")
    max_point_std_px: float = 3.5
    calibration_targets: tuple = (
        (0.10, 0.10),
        (0.90, 0.10),
        (0.10, 0.90),
        (0.90, 0.90),
        (0.50, 0.50),
    )

    # Mapping / motion
    smoothing_alpha: float = 0.15
    dead_zone_px: float = 2.0
    screen_margin_px: int = 5
    stable_cursor_radius_px: float = 18.0
    stable_cursor_required_frames: int = 5
    stable_cursor_window_s: float = 0.35
    cursor_freeze_on_blink_s: float = 0.20

    # Filtering
    one_euro_min_cutoff: float = 0.8
    one_euro_beta: float = 0.015
    one_euro_d_cutoff: float = 1.0

    # Blink / gestures
    blink_ear_threshold: float = 0.18
    blink_adaptive_ratio: float = 0.75
    blink_min_duration_s: float = 0.08
    blink_max_duration_s: float = 0.45
    blink_cooldown_s: float = 0.45
    ear_history_len: int = 100
    unilateral_open_ratio_min: float = 1.35
    bilateral_blink_min_duration_s: float = 0.15
    scroll_toggle_blink_max_duration_s: float = 0.60
    pause_blink_min_duration_s: float = 0.90
    double_blink_gap_s: float = 0.55
    drag_toggle_cooldown_s: float = 0.75

    # Scroll / nod
    scroll_step: int = 120
    scroll_mode_timeout_s: float = 3.0
    nod_pitch_threshold_deg: float = 8.0
    nod_cooldown_s: float = 0.22

    # Hotkeys
    hotkey_pause_resume: str = "f9"
    hotkey_recalibrate: str = "f10"
    hotkey_quit: str = "f12"
    hotkey_next_monitor: str = "f8"
    hotkey_prev_monitor: str = "f7"

    # UI
    font_scale: float = 0.6
    font_thickness: int = 1
    debug_enabled: bool = True
