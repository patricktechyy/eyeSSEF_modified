# Troubleshooting

## 1) `ModuleNotFoundError: No module named 'pypupilext'`

PyPupilEXT is **not** installed by `requirements.txt`.

Fix:
1. Download the correct PyPupilEXT wheel (`.whl`) for your OS + Python version from PyPupilEXT GitHub **Releases**.
2. Install it:
   ```bash
   pip install /path/to/PyPupilEXT-*.whl
   ```

If there is no wheel for your platform, you must build from source (see PyPupilEXT README).

---

## 2) PyPupilEXT wheel installs but import fails

Common causes:
- You installed a wheel for the wrong Python version (e.g., cp311 but you are running Python 3.10).
- You have multiple pythons installed and `pip` installed into a different one.

Checks:
```bash
python --version
python -c "import sys; print(sys.executable)"
python -c "import pypupilext; print('import OK')"
```

If needed, force using the matching pip:
```bash
python -m pip install /path/to/PyPupilEXT-*.whl
```

---

## 3) Matplotlib errors / plot windows not showing

### Headless mode (recommended for automated runs)
Use:
- `main.py`: add `--no_raw_plot`
- `process.py`: add `--no_show_plot`

You can also force a non-interactive backend:
```bash
export MPLBACKEND=Agg
```

### macOS interactive backend issues
Some macOS environments need an explicit backend. Try:
```bash
export MPLBACKEND=MacOSX
```

---

## 4) OpenCV install issues

### Windows
If `opencv-python` fails to install, update pip and try again:
```bash
python -m pip install --upgrade pip
pip install opencv-python
```

### Raspberry Pi
Prefer system packages (faster and more reliable):
```bash
sudo apt-get install -y python3-opencv
```

---

## 5) Processing is extremely slow

What is normal:
- `main.py` decodes **every frame** and runs pupil detection on each frame. This is the slowest part.

Ways to speed it up:
- record at **720p60** instead of **1080p30** only if your detection remains stable (more frames, but smaller images)
- shorten trial durations when doing debug runs
- use a machine with a stronger CPU

---

## 6) `watch_inbox.py` doesn't react to new files

Checklist:
- Confirm videos are placed directly in the inbox root (not inside a subfolder):
  `~/plr_inbox/<video>.mp4`
- If you upload via rsync, upload as `.part` then rename (recommended). The watcher ignores `.part`.
- The watcher waits until file size is stable before processing.

Run the watcher with an explicit inbox path:
```bash
python watch_inbox.py --inbox /full/path/to/plr_inbox
```

---

## 7) Output folder is empty

Most often:
- `main.py` crashed before writing `raw.csv`.
- The video is unreadable by OpenCV.

Try processing the same file manually (not through the watcher) to see the full error:
```bash
python videoImplement/main.py --input path/to/video.mp4
```
