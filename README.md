# EyeSSEF (Chromatic PLR processing)

EyeSSEF is a lightweight, reproducible pipeline for extracting a **raw pupil diameter time-series** from a recorded trial video, then applying a standard set of preprocessing steps (confidence filtering, blink/biological checks, outlier removal, interpolation, and Savitzky–Golay smoothing) to produce a clean **pupillary light reflex (PLR)** trace.

This repository focuses on **offline processing**:
- Input: recorded eye videos (e.g., `.mp4`)
- Output: `raw.csv` + `processed.csv` + plots (`.png`)

It also includes an optional **"inbox watcher" workflow** for automatically processing new trial videos uploaded from a Raspberry Pi.

---

## Quick start (manual)

### 1) Install
Follow the full installation guide:
- **docs/INSTALL.md**

### 2) Run on one video
From the repo root:
```bash
python -m venv .venv
# activate your venv (see docs/INSTALL.md)

python videoImplement/main.py --input path/to/your_video.mp4 --no_raw_plot
```
Outputs are created under:
```
videoImplement/data/<video_stem>/
  raw.csv
  rawPlot.png
  processed_interpolated.csv
  processed.csv
  processedPlot.png
```

---

## Automated workflow (Pi upload → computer inbox → session processing)

If your Raspberry Pi is uploading trial videos to a folder on your computer (e.g., via `rsync`), you can run:

```bash
python watch_inbox.py --inbox ~/plr_inbox
```

This runs in **session mode**:
- each incoming video is converted to a trial folder (raw extraction)
- when you type `process`, it processes all captured trials and generates **one** session average

Full setup steps:
- **AUTO_TRANSFER_MAC.md** (Pi → Mac example)

---

## Documentation

- **docs/INSTALL.md** — install Python + dependencies (including PyPupilEXT)
- **docs/USAGE.md** — how to run `main.py`, `process.py`, batch mode, and naming conventions
- **docs/OUTPUTS.md** — what files are produced and how to interpret them
- **docs/TROUBLESHOOTING.md** — common issues (PyPupilEXT wheels, OpenCV, matplotlib backends)

---

## Core scripts

- `videoImplement/main.py`
  - Decodes video → frames
  - Runs pupil detection per frame
  - Writes `raw.csv` and `rawPlot.png`

- `videoImplement/process.py`
  - Runs preprocessing passes
  - Writes `processed.csv` and `processedPlot.png`
  - In batch mode, also writes one averaged output folder per recording setting

---

## Video naming convention (recommended)

For best reproducibility, name trial videos like:

```
PLR_<User>_<EyeSide L/R>_<Resolution>_<FPS>_<TrialIndex>.mp4

Example:
PLR_Patrick_R_1920x1080_30_2.mp4
```

This allows `main.py` / `process.py` to infer the correct FPS and resolution reliably.

---

## Third‑party dependency note (PyPupilEXT)

This project uses **PyPupilEXT** (`pypupilext`) for pupil ellipse fitting (PuReST). PyPupilEXT is distributed as platform-specific wheels via its GitHub releases and is licensed under **GPLv3**.

Installation instructions are included in **docs/INSTALL.md**.
