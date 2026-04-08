# Eye Mouse Repo

This is a single-folder GitHub-ready project for the Windows eye-mouse app.

## What is included
- Multi-monitor display manager
- Calibration and monitor signature validation
- Gesture -> Intent -> Arbiter pipeline
- Windows SendInput mouse driver
- One Euro smoothing
- Tray app + settings window + runtime manager

## Run in Python
```bash
pip install -r requirements.txt
python -m app.main
```

## Build an EXE (on Windows or GitHub Actions)
```bash
pyinstaller --noconsole --onedir -n EyeMouse app/main.py
```

## Notes
This is a best-effort complete repo assembled from the design/code we built in chat. You may still want to tune thresholds and package imports after first real hardware testing.
